"""
Direct integration tests for EO Agent with MOSDAC Service (Phase 10 — Step 11).
Tests query routing, coordinate extraction, nearest NetCDF grid lookup, and structured EO response.
"""
import pytest
from app.agents.eo_agent import eo_node, _cache


@pytest.fixture(autouse=True)
def clear_cache():
    _cache.clear()
    yield
    _cache.clear()


@pytest.mark.asyncio
async def test_eo_agent_chlorophyll_chennai():
    """
    Step 11 Test:
    Query: 'What is the chlorophyll concentration near Chennai?'
    Latitude: 13.0827
    Longitude: 80.2707
    """
    state = {
        "query": "What is the chlorophyll concentration near Chennai?",
        "location": {
            "latitude": 13.0827,
            "longitude": 80.2707,
        },
    }

    output = await eo_node(state)
    assert "eo_result" in output
    res = output["eo_result"]

    assert res["source"] == "MOSDAC"
    assert res["parameter"] == "chlorophyll_a"
    assert res["status"] == "success"
    assert res["data_source_type"] == "live"
    assert res["requested_latitude"] == 13.0827
    assert res["requested_longitude"] == 80.2707
    assert res["grid_latitude"] == 13.012
    assert res["grid_longitude"] == 80.25
    assert res["value"] in (0.0885, 0.0882)
    assert res["unit"] is None
    assert "Unit metadata not explicitly provided" in res["unit_notes"]
    assert res["observation_date"] in ("2026-09-03", "2026-09-04")
    assert res["grid_distance_km"] == 8.18
    assert len(res["observations"]) == 1
    assert res["observations"][0]["platform"] == "Oceansat-3 (EOS-06)"
    assert res["observations"][0]["instrument"] == "OCM-3"
    assert res["observations"][0]["parameter"] == "Chlorophyll-A"
    assert res["observations"][0]["value"] in (0.0885, 0.0882)


@pytest.mark.asyncio
async def test_eo_agent_chlorophyll_missing_coordinates():
    """Missing coordinates for chlorophyll query must return status unavailable."""
    state = {
        "query": "What is the chlorophyll concentration?",
        "location": {},
    }

    output = await eo_node(state)
    assert "eo_result" in output
    res = output["eo_result"]

    assert res["source"] == "MOSDAC"
    assert res["status"] == "unavailable"
    assert res["value"] is None
    assert "no geographic coordinates were provided" in res["notes"]


@pytest.mark.asyncio
async def test_eo_agent_chlorophyll_invalid_coordinates():
    """Invalid coordinates for chlorophyll query must return status invalid_coordinates."""
    state = {
        "query": "What is the chlorophyll level here?",
        "location": {
            "latitude": "bad_lat",
            "longitude": "bad_lon",
        },
    }

    output = await eo_node(state)
    assert "eo_result" in output
    res = output["eo_result"]

    assert res["source"] == "MOSDAC"
    assert res["status"] == "invalid_coordinates"
    assert res["value"] is None


@pytest.mark.asyncio
async def test_eo_agent_non_chlorophyll_regression():
    """Non-chlorophyll satellite query continues to use Bhoonidhi STAC without regression."""
    state = {
        "query": "Show satellite optical scenes and cloud cover",
        "location": {
            "latitude": 13.0827,
            "longitude": 80.2707,
        },
    }

    output = await eo_node(state)
    assert "eo_result" in output
    res = output["eo_result"]

    # Source should be Bhoonidhi (either live STAC or mock fallback)
    assert "Bhoonidhi" in res["source"]
    assert "parameter" not in res or res.get("parameter") != "chlorophyll_a"
