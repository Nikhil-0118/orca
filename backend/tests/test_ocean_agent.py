"""
Unit and integration tests for the INCOIS ERDDAP Ocean Agent and Mock Transparency.

Covers:
1. Live ocean result includes data_time, retrieved_at, data_age_hours, freshness.
2. data_age_hours calculation and freshness tiers (fresh, stale, historical).
3. Mock results are explicitly identified with status: "mock".
4. Cache functionality and state isolation.
5. API synthesis mock transparency (never presenting mock data as verified live).
"""
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from httpx import ASGITransport, AsyncClient

from app.agents import ocean_agent
from app.agents.ocean_agent import (
    ocean_node,
    _cache,
    _cache_ts,
    _calculate_data_age_hours,
    _classify_freshness,
)
from app.core.state import OrcaState
from app.main import app


MOCK_SST_ERDDAP_JSON = {
    "table": {
        "columnNames": ["time", "zlev", "latitude", "longitude", "sst", "anom"],
        "columnTypes": ["String", "float", "float", "float", "float", "float"],
        "columnUnits": ["UTC", "meters", "degrees_north", "degrees_east", "degrees C", "degrees C"],
        "rows": [
            ["2011-10-04T00:00:00Z", 0.0, 20.125, 72.125, 28.76, 0.23]
        ]
    }
}

MOCK_WIND_ERDDAP_JSON = {
    "table": {
        "columnNames": ["time", "depth", "latitude", "longitude", "wind_speed", "eastward_wind", "northward_wind"],
        "columnTypes": ["String", "float", "float", "float", "double", "double", "double"],
        "columnUnits": ["UTC", "m", "degrees_north", "degrees_east", "m/s", "m/s", "m/s"],
        "rows": [
            ["2023-05-21T12:00:00Z", 10.0, 20.125, 72.125, 4.83, 4.22, -1.09]
        ]
    }
}


@pytest.fixture(autouse=True)
def clear_ocean_cache():
    """Clear ocean cache before and after each test."""
    _cache.clear()
    _cache_ts.clear()
    yield
    _cache.clear()
    _cache_ts.clear()


# ── Test 1 & 2: Live ocean result includes data_time, retrieved_at, data_age_hours, freshness ──

@pytest.mark.asyncio
async def test_ocean_node_freshness_fields():
    """Verify live ocean result includes data_time, retrieved_at, data_age_hours, and freshness."""
    def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 200
        if "NOAA_AVHRR_AMSR" in url:
            mock_resp.json.return_value = MOCK_SST_ERDDAP_JSON
        elif "ascat_daily" in url:
            mock_resp.json.return_value = MOCK_WIND_ERDDAP_JSON
        else:
            mock_resp.status_code = 404
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        state: OrcaState = {
            "query": "Current sea conditions",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-s1",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await ocean_node(state)
        assert "ocean_result" in output
        res = output["ocean_result"]

        # Check required freshness fields
        assert res["status"] == "live"
        assert res["data_time"] == "2023-05-21T12:00:00Z"
        assert "retrieved_at" in res
        assert isinstance(res["retrieved_at"], str)
        assert "data_age_hours" in res
        assert isinstance(res["data_age_hours"], float)
        assert res["data_age_hours"] > 0
        assert res["freshness"] == "historical"  # 2023 observation is > 168h old


# ── Test 3 & 4: Data age calculation and freshness classification ─────────

def test_data_age_and_freshness_classification():
    """Verify calculation of data age hours and classification thresholds."""
    # 1. Fresh (e.g. 5 hours ago)
    t_obs = "2026-09-01T12:00:00Z"
    t_ret = "2026-09-01T17:00:00Z"
    age = _calculate_data_age_hours(t_obs, t_ret)
    assert age == 5.0
    assert _classify_freshness(age) == "fresh"

    # 2. Exactly 24 hours (boundary of fresh)
    assert _classify_freshness(24.0) == "fresh"

    # 3. Stale (e.g. 48 hours / 2 days ago)
    t_obs_stale = "2026-08-30T17:00:00Z"
    age_stale = _calculate_data_age_hours(t_obs_stale, t_ret)
    assert age_stale == 48.0
    assert _classify_freshness(age_stale) == "stale"

    # 4. Exactly 168 hours (7 days, boundary of stale)
    assert _classify_freshness(168.0) == "stale"

    # 5. Historical (> 7 days)
    t_obs_hist = "2026-08-01T17:00:00Z"
    age_hist = _calculate_data_age_hours(t_obs_hist, t_ret)
    assert age_hist > 168.0
    assert _classify_freshness(age_hist) == "historical"

    # 6. None / Unknown
    assert _classify_freshness(None) == "unknown"


# ── Test 5: Mock results are explicitly identified ─────────────────────────

@pytest.mark.asyncio
async def test_mock_ocean_node_identification():
    """Verify that fallback mock results are clearly labeled with status: 'mock'."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network down")):
        state: OrcaState = {
            "query": "Sea temp",
            "location": {"lat": 15.0, "lon": 74.0},
            "session_id": "test-s3",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await ocean_node(state)
        res = output["ocean_result"]
        assert res["status"] == "mock"
        assert res["source"] == "INCOIS-mock"
        assert "retrieved_at" in res
        assert "data_age_hours" in res
        assert "freshness" in res


# ── Test 6: API synthesis mock transparency ────────────────────────────────

@pytest.mark.asyncio
async def test_api_synthesis_mock_transparency():
    """Verify /api/query never presents mock EO or weather observations as live real observations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/query",
            json={
                "query": "What are the marine conditions?",
                "location": {"lat": 20.0, "lon": 72.0},
                "session_id": "test-mock-transparency",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check evidence explicitly flags mocks or live provenance
        evidence_str = " ".join(data["evidence"])
        assert "mock" in evidence_str.lower() or "live" in evidence_str.lower()
        if any("EO" in e or "Weather" in e for e in data["evidence"]):
            assert any("mock" in e.lower() for e in data["evidence"] if "EO" in e or "Weather" in e)

        # Check answer explicitly demarcates simulated vs live or notes limitations
        answer = data["answer"]
        limitations = " ".join(data.get("data_limitations", [])).lower()
        assert (
            "[SIMULATED EO DATA]" in answer
            or "[SIMULATED WEATHER DATA]" in answer
            or "simulated" in answer.lower()
            or "mock" in answer.lower()
            or "simulated" in limitations
            or "historical" in answer.lower()
        )


# ── Test 7: State isolation ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ocean_node_state_isolation():
    """Verify ocean_node writes ONLY to ocean_result without mutating shared keys."""
    state: OrcaState = {
        "query": "Test query",
        "location": {"lat": 13.0, "lon": 80.0},
        "session_id": "test-isolation",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    output = await ocean_node(state)
    assert set(output.keys()) == {"ocean_result"}
