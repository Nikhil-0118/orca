"""
Comprehensive Geospatial Integrity, Data Provenance, and Anti-Repair Test Suite (Phase 8.4).
Validates:
1. Canonical location parsing and out-of-range coordinate rejection (-90..90, -180..180).
2. Honest handling of unavailable location (no silent fallback to Chennai).
3. Explicit demonstration mode labelling (is_demo=True, source='demo').
4. Location switching without cross-query bleeding.
5. Geospatial consistency validator detecting mismatched coordinates.
6. Final reasoning engine anti-repair rule (discarding mismatched agent data).
7. Transparent data timestamps and observation freshness tiers (fresh, stale, simulated).
8. Marine ecosystem agent location awareness (chlorophyll density & trophic status).
9. Named geographic region resolution (e.g. Sri Lanka side, Mumbai, Kochi) independent of device GPS.
"""
import pytest
from httpx import AsyncClient

from app.schemas.query import LocationContext, QueryRequest
from app.services.geo_validator import (
    haversine_distance_km,
    validate_agent_geo_consistency,
    validate_all_agent_locations,
    resolve_query_spatial_target,
    NAMED_MARITIME_REGIONS,
)
from app.agents.weather_agent import weather_node
from app.agents.ocean_agent import ocean_node
from app.agents.eo_agent import eo_node
from app.agents.safety_agent import safety_node
from app.agents.marine_ecosystem_agent import ecosystem_node
from app.agents.final_reasoning_agent import final_reasoning_agent


# ── 1. Coordinate Validation & Rejection ────────────────────────────────────

def test_location_context_valid_coordinates():
    loc = LocationContext(
        latitude=18.922,
        longitude=72.834,
        source="browser_gps",
        accuracy_m=15.0,
        is_demo=False,
    )
    assert loc.latitude == 18.922
    assert loc.longitude == 72.834
    assert loc.source == "browser_gps"
    assert loc.is_demo is False


def test_location_context_invalid_latitude_raises():
    with pytest.raises(ValueError):
        LocationContext(latitude=95.0, longitude=80.0)


def test_location_context_invalid_longitude_raises():
    with pytest.raises(ValueError):
        LocationContext(latitude=13.0, longitude=185.0)


@pytest.mark.asyncio
async def test_endpoint_rejects_out_of_bounds_coordinates(client: AsyncClient):
    resp = await client.post(
        "/api/query",
        json={
            "query": "What is the weather here?",
            "location": {"latitude": 120.0, "longitude": 80.0},
            "session_id": "test-invalid-coords",
        },
    )
    assert resp.status_code == 400
    assert "latitude" in resp.json()["detail"].lower()


# ── 2. Unavailable Location (No Silent Fallback to Chennai) ──────────────────

@pytest.mark.asyncio
async def test_unavailable_location_no_silent_chennai(client: AsyncClient):
    resp = await client.post(
        "/api/query",
        json={
            "query": "What is my current location?",
            "location": None,
            "is_demo_mode": False,
            "session_id": "test-unavail",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    ans = data["answer"].lower()
    # Must inform user location is unavailable, NOT pretend to be Chennai
    assert "unavailable" in ans or "permission" in ans or "gps" in ans or "access" in ans
    assert "13.08" not in ans and "chennai" not in ans


# ── 3. Explicit Demo Mode ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_explicit_demo_mode_labelling(client: AsyncClient):
    resp = await client.post(
        "/api/query",
        json={
            "query": "What is my current location?",
            "location": None,
            "is_demo_mode": True,
            "session_id": "test-demo-mode",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["is_demo"] is True
    assert data["location"]["source"] == "demo"
    ans = data["answer"].lower()
    assert "demo" in ans or "demonstration" in ans


# ── 4. Location Switching (No State Bleed) ───────────────────────────────────

@pytest.mark.asyncio
async def test_location_switching_in_same_session(client: AsyncClient):
    sess_id = "test-session-switching"

    # Step 1: Query for Kochi (Kerala coast)
    loc_kochi = {"latitude": 9.931, "longitude": 76.267, "source": "browser_gps", "is_demo": False}
    resp1 = await client.post(
        "/api/query",
        json={"query": "What is my current location?", "location": loc_kochi, "session_id": sess_id},
    )
    assert resp1.status_code == 200
    ans1 = resp1.json()["answer"].lower()
    assert "kochi" in ans1 or "9.93" in ans1 or "malabar" in ans1
    assert "chennai" not in ans1

    # Step 2: Query for Mumbai in same session
    loc_mumbai = {"latitude": 18.922, "longitude": 72.834, "source": "browser_gps", "is_demo": False}
    resp2 = await client.post(
        "/api/query",
        json={"query": "What is my current location?", "location": loc_mumbai, "session_id": sess_id},
    )
    assert resp2.status_code == 200
    ans2 = resp2.json()["answer"].lower()
    assert "mumbai" in ans2 or "18.92" in ans2 or "maharashtra" in ans2
    assert "kochi" not in ans2 and "chennai" not in ans2


# ── 5. Geospatial Consistency Validator & Anti-Repair Rule ──────────────────

def test_haversine_distance_accuracy():
    # Chennai (13.0827, 80.2707) to Mumbai (18.922, 72.834) ~ 1030 km
    dist = haversine_distance_km(13.0827, 80.2707, 18.922, 72.834)
    assert 1020 <= dist <= 1045


def test_geo_consistency_mismatch_detection():
    # Requested Mumbai, but agent returned Chennai
    requested_lat, requested_lon = 18.922, 72.834
    mismatched_weather = {
        "source": "IMD",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "status": "live",
    }
    is_consistent, dist, note = validate_agent_geo_consistency(
        requested_lat, requested_lon, mismatched_weather, "weather"
    )
    assert is_consistent is False
    assert dist > 1000.0
    assert "exceeding the local threshold" in note


def test_validate_all_agent_locations_detects_mismatch():
    loc_ctx = {"latitude": 18.922, "longitude": 72.834}
    results = {
        "weather": {"location": {"lat": 13.0827, "lon": 80.2707}},  # Chennai (mismatch!)
        "ocean": {"location": {"lat": 18.90, "lon": 72.85}},        # Mumbai grid (consistent)
    }
    audit = validate_all_agent_locations(loc_ctx, results)
    assert audit["all_consistent"] is False
    assert len(audit["mismatches"]) == 1
    assert audit["mismatches"][0]["agent"] == "weather"


@pytest.mark.asyncio
async def test_final_reasoner_anti_repair_discards_mismatched_agent():
    # Simulate a state where user requested Mumbai, but weather agent returned Chennai data
    state = {
        "query": "What is the weather and sea condition here?",
        "location": {"latitude": 18.922, "longitude": 72.834, "is_demo": False},
        "session_id": "test-anti-repair",
        "selected_agents": ["weather", "ocean"],
        "safety_required": False,
        "eo_result": None,
        "ocean_result": {
            "source": "INCOIS ERDDAP",
            "status": "live",
            "location": {"lat": 18.90, "lon": 72.85},
            "sea_surface_temperature": {"value": 29.2},
            "significant_wave_height_m": 1.5,
        },
        "weather_result": {
            "source": "IMD",
            "status": "live",
            "location": {"lat": 13.0827, "lon": 80.2707},  # Chennai!
            "zone": "Chennai Coastal Zone",
            "wind": {"speed": 15.0, "direction": "SW"},
        },
        "safety_result": None,
        "ecosystem_result": None,
        "evidence": [],
    }

    result = await final_reasoning_agent.reason(state)
    # The weather data from Chennai must be discarded due to mismatch
    assert any("mismatch" in lim.lower() for lim in result["data_limitations"])
    # Discarded agent must not be presented as valid local evidence
    ans = result["final_answer"].lower()
    assert "chennai" not in ans


# ── 6. Domain Agents Receive & Obey Coordinates ─────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_uses_supplied_coordinates():
    state = {
        "location": {"latitude": 21.64, "longitude": 69.60, "is_demo": False},
        "selected_agents": ["weather"],
    }
    res = await weather_node(state)
    w_res = res["weather_result"]
    assert w_res["location"]["lat"] == 21.64
    assert w_res["location"]["lon"] == 69.60
    assert "gujarat" in w_res["zone"].lower() or "coastal" in w_res["zone"].lower()
    assert "observation_time" in w_res
    assert "data_source_type" in w_res


@pytest.mark.asyncio
async def test_ocean_node_uses_supplied_coordinates():
    state = {
        "location": {"latitude": 15.49, "longitude": 73.82, "is_demo": False},
        "selected_agents": ["ocean"],
    }
    res = await ocean_node(state)
    o_res = res["ocean_result"]
    assert o_res["requested_location"]["lat"] == 15.49
    assert o_res["requested_location"]["lon"] == 73.82
    assert o_res["distance_km"] <= 30.0
    assert "observation_time" in o_res
    assert "data_source_type" in o_res


@pytest.mark.asyncio
async def test_marine_ecosystem_node_chlorophyll_density():
    state = {
        "location": {"latitude": 19.5, "longitude": 85.8, "is_demo": False},  # Odisha shelf
        "selected_agents": ["ecosystem"],
    }
    res = await ecosystem_node(state)
    e_res = res["ecosystem_result"]
    assert e_res["location"]["lat"] == 19.5
    assert e_res["location"]["lon"] == 85.8
    assert "chlorophyll_a" in e_res
    assert e_res["chlorophyll_a"]["value"] > 0.5
    assert e_res["trophic_status"] in ["Mesotrophic", "Eutrophic", "Oligotrophic"]
    assert "scientific_interpretation" in e_res


# ── 7. Named Region Routing vs Deictic Routing ──────────────────────────────

def test_resolve_query_spatial_target_named_region():
    client_loc = LocationContext(latitude=13.08, longitude=80.27, source="browser_gps")
    target = resolve_query_spatial_target("What is the weather near Mumbai?", client_loc)
    assert target.source == "named_region"
    assert target.latitude == NAMED_MARITIME_REGIONS["mumbai"]["latitude"]
    assert target.longitude == NAMED_MARITIME_REGIONS["mumbai"]["longitude"]


def test_resolve_query_spatial_target_deictic_here():
    client_loc = LocationContext(latitude=9.93, longitude=76.26, source="browser_gps")
    target = resolve_query_spatial_target("What is the weather here right now?", client_loc)
    # Strictly bound to client device location
    assert target.latitude == 9.93
    assert target.longitude == 76.26
    assert target.source == "browser_gps"
