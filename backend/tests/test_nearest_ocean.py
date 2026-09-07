"""
Test suite for ORCA Phase A.1.2: Nearest Ocean / Coastal Proximity Intelligence.
Verifies:
1. Geodesic distance calculation to coastline reference dataset
2. Forward bearing calculation and 8-point compass mapping
3. Distinction between inland (Kanpur), coastal (Chennai, Mumbai), and marine (14.0, 84.0) coordinates
4. Distinction between nearest ocean and nearest freshwater water body (Ganges)
5. Intent classification and routing isolation across planner
6. Absence of unprompted wave/sea-state reports for proximity questions
"""
import pytest
import asyncio
from app.services.location_resolver import (
    location_resolver,
    calculate_bearing,
    bearing_to_compass,
    _haversine_distance_km,
)
from app.services.planner import orca_planner
from app.services.conversational_llm import generate_conversational_response, _deterministic_fallback


def test_01_bearing_and_compass_calculations():
    """Verify forward initial bearing and 8-point compass conversion."""
    # North: (0, 0) -> (10, 0)
    b_north = calculate_bearing(0.0, 0.0, 10.0, 0.0)
    assert round(b_north) == 0 or round(b_north) == 360
    assert bearing_to_compass(b_north) == "North"

    # East: (0, 0) -> (0, 10)
    b_east = calculate_bearing(0.0, 0.0, 0.0, 10.0)
    assert round(b_east) == 90
    assert bearing_to_compass(b_east) == "East"

    # South: (10, 0) -> (0, 0)
    b_south = calculate_bearing(10.0, 0.0, 0.0, 0.0)
    assert round(b_south) == 180
    assert bearing_to_compass(b_south) == "South"

    # West: (0, 10) -> (0, 0)
    b_west = calculate_bearing(0.0, 10.0, 0.0, 0.0)
    assert round(b_west) == 270
    assert bearing_to_compass(b_west) == "West"

    # Kanpur -> Balasore/Odisha Coast should be Southeast (~128 deg)
    b_kanpur = calculate_bearing(26.52, 80.26, 21.50, 87.00)
    assert 120.0 <= b_kanpur <= 135.0
    assert bearing_to_compass(b_kanpur) == "Southeast"


def test_02_kanpur_nearest_ocean_inland_proximity():
    """Verify nearest ocean calculation for Kanpur (26.52, 80.26)."""
    res = location_resolver.find_nearest_ocean(
        lat=26.52,
        lon=80.26,
        user_place="Kanpur, Uttar Pradesh",
        geo_type="inland",
    )
    assert res.is_user_inland is True
    assert res.ocean == "Bay of Bengal"
    # Geodesic distance to Balasore / Digha Coast is approx 883 km
    assert 850.0 <= res.distance_km <= 920.0
    assert res.compass_direction == "Southeast"
    assert "inland" in res.summary_text.lower()
    assert "Bay of Bengal" in res.summary_text
    assert "km" in res.summary_text
    # Must NOT report Ganges as an ocean
    assert "ganges" not in res.ocean.lower()
    assert "river" not in res.ocean.lower()


def test_03_chennai_coastal_nearest_ocean():
    """Verify nearest ocean calculation for coastal Chennai (13.0827, 80.2707)."""
    res = location_resolver.find_nearest_ocean(
        lat=13.0827,
        lon=80.2707,
        user_place="Chennai, Tamil Nadu",
        geo_type="coastal",
    )
    assert res.is_user_inland is False
    assert res.ocean == "Bay of Bengal"
    # Distance to coastline should be very small (< 25 km)
    assert res.distance_km < 25.0
    assert "coastal" in res.summary_text.lower() or "coast" in res.summary_text.lower()


def test_04_marine_coordinate_nearest_ocean():
    """Verify nearest ocean calculation for open marine waters (14.0, 84.0)."""
    res = location_resolver.find_nearest_ocean(
        lat=14.0,
        lon=84.0,
        geo_type="marine",
    )
    assert res.is_user_inland is False
    assert res.ocean == "Bay of Bengal"
    assert res.distance_km == 0.0
    assert "open waters" in res.summary_text.lower() or "marine" in res.summary_text.lower()


def test_05_mumbai_and_western_coast():
    """Verify Arabian Sea detection for Mumbai and Western coast."""
    res_mumbai = location_resolver.find_nearest_ocean(
        lat=19.0760,
        lon=72.8777,
        user_place="Mumbai, Maharashtra",
        geo_type="coastal",
    )
    assert res_mumbai.ocean == "Arabian Sea"
    assert res_mumbai.distance_km < 25.0

    # Jaipur (inland NW) closest ocean should be Arabian Sea (Gulf of Khambhat)
    res_jaipur = location_resolver.find_nearest_ocean(
        lat=26.9124,
        lon=75.7873,
        user_place="Jaipur, Rajasthan",
        geo_type="inland",
    )
    assert res_jaipur.is_user_inland is True
    assert res_jaipur.ocean == "Arabian Sea"
    assert 650.0 <= res_jaipur.distance_km <= 750.0


def test_06_nearest_water_body_vs_nearest_ocean():
    """Verify distinction between terrestrial river systems and oceans."""
    wb = location_resolver.find_nearest_water_body(
        lat=26.52,
        lon=80.26,
        user_place="Kanpur, Uttar Pradesh",
        geo_type="inland",
    )
    assert wb["is_freshwater"] is True
    assert "ganges" in wb["nearest_water_body"].lower()
    assert wb["nearest_ocean"] == "Bay of Bengal"
    # Summary explicitly clarifies that Ganges is a freshwater river, not an ocean
    assert "freshwater river" in wb["summary_text"].lower()
    assert "Bay of Bengal" in wb["summary_text"]


@pytest.mark.asyncio
async def test_07_planner_intent_classification():
    """Verify planner classifies proximity, water body, location, and marine queries distinctly."""
    # 1. Nearest ocean
    plan1 = await orca_planner.plan("where is the nearest ocean nearby me")
    assert plan1.intent == "nearest_ocean"
    assert plan1.response_mode == "utility"
    assert "location" in plan1.tools
    assert plan1.requires_agents is False

    plan2 = await orca_planner.plan("how far is the nearest ocean")
    assert plan2.intent == "nearest_ocean"
    assert plan2.response_mode == "utility"

    plan3 = await orca_planner.plan("which ocean is closest to me")
    assert plan3.intent == "nearest_ocean"
    assert plan3.response_mode == "utility"

    plan4 = await orca_planner.plan("what is the nearest coast")
    assert plan4.intent == "nearest_ocean"
    assert plan4.response_mode == "utility"

    # 2. Ocean proximity presence
    plan5 = await orca_planner.plan("is there an ocean nearby me")
    assert plan5.intent == "ocean_proximity"
    assert plan5.response_mode == "utility"

    # 3. Water body
    plan6 = await orca_planner.plan("what is the nearest water body")
    assert plan6.intent == "nearest_water_body"
    assert plan6.response_mode == "utility"

    # 4. Location inquiry (Phase A.1 - unchanged)
    plan7 = await orca_planner.plan("what is my location")
    assert plan7.intent in ("location", "LOCATION_CURRENT")
    assert plan7.response_mode == "utility"

    # 5. Ocean SST (unchanged - routes to ocean agent)
    plan8 = await orca_planner.plan("what is the sea temperature here")
    assert plan8.response_mode == "marine"
    assert "ocean" in plan8.agents

    # 6. Weather (unchanged - routes to weather agent)
    plan9 = await orca_planner.plan("what is the weather here")
    assert plan9.response_mode == "marine"
    assert "weather" in plan9.agents


@pytest.mark.asyncio
async def test_08_conversational_response_generation():
    """Verify dynamic response generation produces concise output without unrequested wave telemetry."""
    location_payload = {
        "lat": 26.52,
        "lon": 80.26,
        "resolved_place": "Kanpur, Uttar Pradesh",
        "geographic_type": "inland",
    }
    resp = await generate_conversational_response(
        intent="nearest_ocean",
        user_query="where is the nearest ocean nearby me",
        tools=["location"],
        location=location_payload,
    )
    # Check key contents
    assert "Bay of Bengal" in resp
    assert "inland" in resp.lower()
    assert ("km" in resp.lower()) or ("kilometer" in resp.lower())
    assert ("southeast" in resp.lower()) or ("bearing" in resp.lower())
    # Verify absence of unprompted wave/sea-state reports
    assert "wave height" not in resp.lower()
    assert "significant wave" not in resp.lower()
    assert "fishing suitability" not in resp.lower()
    assert "svg" not in resp.lower() or "svg" not in resp
