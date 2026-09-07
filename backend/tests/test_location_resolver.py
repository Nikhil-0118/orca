"""
Tests for Dedicated LocationResolver (ORCA Phase A.1).

Validates:
1. Inland coordinate (26.52, 80.26) -> strictly inland, never Bay of Bengal / marine.
2. Coastal coordinate (Chennai: 13.0827, 80.2707) -> coastal classification.
3. Marine coordinate (open sea: 14.0, 84.0) -> marine classification.
4. Out-of-bounds coordinates -> rejected.
5. Missing coordinates -> unavailable.
6. Reverse geocoder network failure -> safe offline fallback (never calls inland coastal).
7. Named location query -> target location separate from vessel location.
8. Vessel GPS coordinates remain authoritative and untouched.
9. Spatial cache isolation -> Location A does not bleed into Location B.
10. Explicit demo mode identification.
"""
import pytest
from unittest.mock import patch, AsyncMock
import httpx

from app.services.location_resolver import LocationResolver, location_resolver
from app.schemas.query import LocationContext, QueryRequest
from app.services.geo_validator import resolve_query_spatial_target
from app.services.utility_tools import get_location_context, get_location_context_async


@pytest.mark.asyncio
async def test_01_inland_coordinate_kanpur():
    """Kanpur (26.52, 80.26) must resolve as INLAND and NEVER as Bay of Bengal."""
    resolver = LocationResolver()
    res = await resolver.resolve(26.52, 80.26, source="browser_gps")

    assert res.geographic_type == "inland", f"Expected inland, got {res.geographic_type}"
    assert "bay of bengal" not in (res.place_name or "").lower(), "Must NOT be Bay of Bengal"
    assert "coastal" not in res.geographic_type.lower()
    assert "marine" not in res.geographic_type.lower()
    # Place should contain Kanpur or Uttar Pradesh
    assert "kanpur" in (res.place_name or "").lower() or "uttar pradesh" in (res.state or "").lower()


@pytest.mark.asyncio
async def test_02_coastal_coordinate_chennai():
    """Chennai (13.0827, 80.2707) must resolve as COASTAL."""
    resolver = LocationResolver()
    res = await resolver.resolve(13.0827, 80.2707, source="browser_gps")

    assert res.geographic_type == "coastal", f"Expected coastal, got {res.geographic_type}"
    assert "chennai" in (res.place_name or "").lower() or "tamil nadu" in (res.state or "").lower()


@pytest.mark.asyncio
async def test_03_marine_coordinate_bay_of_bengal():
    """Coordinates far in the Bay of Bengal (14.0, 84.0) must resolve as MARINE."""
    resolver = LocationResolver()
    res = await resolver.resolve(14.0, 84.0, source="browser_gps")

    assert res.geographic_type == "marine", f"Expected marine, got {res.geographic_type}"
    assert "bay of bengal" in (res.place_name or "").lower() or "marine" in (res.place_name or "").lower()


@pytest.mark.asyncio
async def test_04_marine_coordinate_arabian_sea():
    """Coordinates far in the Arabian Sea (18.0, 68.0) must resolve as MARINE."""
    resolver = LocationResolver()
    res = await resolver.resolve(18.0, 68.0, source="browser_gps")

    assert res.geographic_type == "marine", f"Expected marine, got {res.geographic_type}"
    assert "arabian sea" in (res.place_name or "").lower() or "marine" in (res.place_name or "").lower()


@pytest.mark.asyncio
async def test_05_invalid_and_out_of_bounds():
    """Out-of-bounds coordinates must return source='invalid'."""
    resolver = LocationResolver()
    res = await resolver.resolve(95.0, 80.26)
    assert res.source == "invalid"
    assert res.place_name == "Invalid Coordinates"


@pytest.mark.asyncio
async def test_06_missing_coordinates():
    """None coordinates must return source='unavailable'."""
    resolver = LocationResolver()
    res = await resolver.resolve(None, None)
    assert res.source == "unavailable"
    assert res.place_name is None


@pytest.mark.asyncio
async def test_07_offline_fallback_safety():
    """When geocoder network call raises an exception, inland coordinates must remain inland."""
    resolver = LocationResolver()
    # Mock httpx to simulate total network outage
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network is completely down")):
        res = await resolver.resolve(26.52, 80.26, source="browser_gps")

        assert res.source == "offline_dataset"
        assert res.geographic_type == "inland"
        assert "bay of bengal" not in (res.place_name or "").lower()
        assert "uttar pradesh" in (res.state or "").lower() or "gangetic" in (res.place_name or "").lower()


def test_08_spatial_cache_isolation():
    """Location A must not bleed into Location B via caching."""
    resolver = LocationResolver()
    # Resolve Kanpur
    res_a = resolver.resolve_sync(26.52, 80.26)
    # Resolve Chennai
    res_b = resolver.resolve_sync(13.0827, 80.2707)

    assert res_a.geographic_type == "inland"
    assert res_b.geographic_type == "coastal"
    assert res_a.latitude != res_b.latitude
    assert res_a.place_name != res_b.place_name


def test_09_user_vs_target_location_separation():
    """Vessel GPS must remain separate from query target location."""
    vessel_gps = LocationContext(
        latitude=9.93,
        longitude=76.27,
        source="browser_gps",
        accuracy_m=12.0,
        is_demo=False,
    )

    query = "What is the sea condition near Sri Lanka?"
    target_loc = resolve_query_spatial_target(query, vessel_gps)

    # Target is Sri Lanka
    assert target_loc.source == "named_region"
    assert target_loc.latitude == 9.45
    assert target_loc.longitude == 79.20

    # User vessel GPS remains untouched in Kochi
    assert vessel_gps.source == "browser_gps"
    assert vessel_gps.latitude == 9.93
    assert vessel_gps.longitude == 76.27


def test_10_explicit_demo_mode_identification():
    """Demo mode must be clearly flagged and not confused with real GPS."""
    resolver = LocationResolver()
    res = resolver.resolve_sync(13.0827, 80.2707, source="demo", is_demo=True)

    assert res.source == "demo"
    assert res.is_approximate is True
    assert "demo" in (res.place_name or "").lower()


@pytest.mark.asyncio
async def test_11_utility_tools_integration_kanpur():
    """utility_tools.get_location_context_async must return inland for 26.52, 80.26."""
    loc_input = {"latitude": 26.52, "longitude": 80.26, "source": "browser_gps"}
    ctx = await get_location_context_async(loc_input)

    assert ctx["available"] is True
    assert ctx["geographic_type"] == "inland"
    assert "bay of bengal" not in ctx["region_name"].lower()
    assert "bay of bengal" not in ctx["short_name"].lower()
    assert "inland" in ctx["short_name"].lower()
