"""
Unit and integration tests for the ISRO Bhoonidhi STAC EO Agent and Mock Transparency.

Covers:
1. Successful Bhoonidhi STAC response parsing & normalization (status: "live").
2. HTTP 401 fallback (invalid or expired token).
3. HTTP 403 fallback (forbidden access).
4. Timeout / network failure fallback.
5. Malformed response JSON handling.
6. Empty feature/scene response handling.
7. 15-minute in-memory cache functionality.
8. Freshness tier calculation (fresh, stale, historical).
9. State isolation (returns ONLY {"eo_result": ...}).
"""
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from app.agents import eo_agent
from app.agents.eo_agent import (
    eo_node,
    _cache,
    _cache_ts,
    _calculate_data_age_hours,
    _classify_freshness,
)
from app.core.state import OrcaState


MOCK_BHOONIDHI_STAC_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": "E06_OCM_LAC_02NOV2023_001",
            "collection": "EOS-06_OCM-LAC_L1C",
            "bbox": [71.5, 19.5, 72.5, 20.5],
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[71.5, 19.5], [72.5, 19.5], [72.5, 20.5], [71.5, 20.5], [71.5, 19.5]]
                ]
            },
            "properties": {
                "datetime": "2023-11-02T06:30:15Z",
                "platform": "EOS-06 (Oceansat-3)",
                "instruments": ["OCM-3"],
                "eo:cloud_cover": 12.5,
                "proj:epsg": 4326,
            }
        }
    ]
}


@pytest.fixture(autouse=True)
def clear_eo_cache():
    """Clear EO cache before and after each test."""
    _cache.clear()
    _cache_ts.clear()
    yield
    _cache.clear()
    _cache_ts.clear()


# ── Test 1: Successful Bhoonidhi response parsing ──────────────────────────

@pytest.mark.asyncio
async def test_eo_node_successful_parsing():
    """Verify successful parsing of valid Bhoonidhi STAC response into normalized live structure."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_BHOONIDHI_STAC_RESPONSE

    with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "mock-valid-token"), \
         patch("httpx.AsyncClient.post", return_value=mock_resp):

        state: OrcaState = {
            "query": "Satellite coverage near Mumbai",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-eo-s1",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await eo_node(state)
        assert "eo_result" in output
        res = output["eo_result"]

        assert res["source"] == "Bhoonidhi STAC"
        assert res["status"] == "live"
        assert res["data_time"] == "2023-11-02T06:30:15Z"
        assert "retrieved_at" in res
        assert isinstance(res["data_age_hours"], float)
        assert res["freshness"] == "historical"
        assert res["observation_count"] == 1

        obs = res["observations"][0]
        assert obs["platform"] == "EOS-06 (Oceansat-3)"
        assert obs["instrument"] == "OCM-3"
        assert obs["collection"] == "EOS-06_OCM-LAC_L1C"
        assert obs["cloud_cover"] == 12.5
        assert obs["id"] == "E06_OCM_LAC_02NOV2023_001"


# ── Test 2: HTTP 401 fallback ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eo_node_http_401_fallback():
    """Verify that HTTP 401 Unauthorized triggers mock fallback cleanly."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 401

    with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "invalid-token"), \
         patch("httpx.AsyncClient.post", return_value=mock_resp):

        state: OrcaState = {
            "query": "Satellite coverage",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-eo-401",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await eo_node(state)
        res = output["eo_result"]
        assert res["status"] == "mock"
        assert res["source"] == "Bhoonidhi-mock"
        assert "401" in res["reason"]


# ── Test 3: HTTP 403 fallback ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eo_node_http_403_fallback():
    """Verify that HTTP 403 Forbidden triggers mock fallback cleanly."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 403

    with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "forbidden-token"), \
         patch("httpx.AsyncClient.post", return_value=mock_resp):

        state: OrcaState = {
            "query": "Satellite coverage",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-eo-403",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await eo_node(state)
        res = output["eo_result"]
        assert res["status"] == "mock"
        assert res["source"] == "Bhoonidhi-mock"
        assert "403" in res["reason"]


# ── Test 4: Timeout/network failure fallback ───────────────────────────────

@pytest.mark.asyncio
async def test_eo_node_timeout_fallback():
    """Verify that timeout/network errors trigger mock fallback without raising exceptions."""
    with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "mock-token"), \
         patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timeout")):

        state: OrcaState = {
            "query": "Satellite coverage",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-eo-timeout",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await eo_node(state)
        res = output["eo_result"]
        assert res["status"] == "mock"
        assert "timeout" in res["reason"].lower()


# ── Test 5: Malformed response fallback ────────────────────────────────────

@pytest.mark.asyncio
async def test_eo_node_malformed_response_fallback():
    """Verify that malformed or unexpected STAC JSON safely falls back to mock."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"unexpected": "structure"}

    with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "mock-token"), \
         patch("httpx.AsyncClient.post", return_value=mock_resp):

        state: OrcaState = {
            "query": "Satellite coverage",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-eo-malformed",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await eo_node(state)
        res = output["eo_result"]
        assert res["status"] == "mock"


# ── Test 6: Empty/no-observation response fallback ─────────────────────────

@pytest.mark.asyncio
async def test_eo_node_empty_features_fallback():
    """Verify that a STAC response with zero matching features falls back cleanly."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"type": "FeatureCollection", "features": []}

    with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "mock-token"), \
         patch("httpx.AsyncClient.post", return_value=mock_resp):

        state: OrcaState = {
            "query": "Satellite coverage",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-eo-empty",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await eo_node(state)
        res = output["eo_result"]
        assert res["status"] == "mock"
        assert "no satellite" in res["reason"].lower()


# ── Test 7: 15-minute cache behavior ───────────────────────────────────────

@pytest.mark.asyncio
async def test_eo_node_cache():
    """Verify that calling eo_node twice for the same coordinates uses cache."""
    mock_post = AsyncMock()
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_BHOONIDHI_STAC_RESPONSE
    mock_post.return_value = mock_resp

    with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "mock-token"), \
         patch("httpx.AsyncClient.post", mock_post):

        state: OrcaState = {
            "query": "Satellite coverage",
            "location": {"lat": 18.0, "lon": 73.0},
            "session_id": "test-eo-cache",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        # First call -> network request
        out1 = await eo_node(state)
        assert mock_post.call_count == 1

        # Second call with same location -> cache hit
        out2 = await eo_node(state)
        assert mock_post.call_count == 1
        assert out1["eo_result"] == out2["eo_result"]


# ── Test 8: Freshness calculation ──────────────────────────────────────────

def test_eo_freshness_calculation():
    """Verify data age calculation and freshness classification tiers for EO passes."""
    t_ret = "2026-09-01T12:00:00Z"

    # Fresh: pass 6 hours ago
    t_fresh = "2026-09-01T06:00:00Z"
    age_fresh = _calculate_data_age_hours(t_fresh, t_ret)
    assert age_fresh == 6.0
    assert _classify_freshness(age_fresh) == "fresh"

    # Stale: pass 3 days ago (72 hours)
    t_stale = "2026-08-29T12:00:00Z"
    age_stale = _calculate_data_age_hours(t_stale, t_ret)
    assert age_stale == 72.0
    assert _classify_freshness(age_stale) == "stale"

    # Historical: pass 10 days ago (240 hours)
    t_hist = "2026-08-22T12:00:00Z"
    age_hist = _calculate_data_age_hours(t_hist, t_ret)
    assert age_hist == 240.0
    assert _classify_freshness(age_hist) == "historical"


# ── Test 9: State isolation ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eo_node_state_isolation():
    """Verify eo_node returns ONLY eo_result and does not mutate shared fields."""
    state: OrcaState = {
        "query": "EO test",
        "location": {"lat": 13.0, "lon": 80.0},
        "session_id": "test-eo-isolation",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    output = await eo_node(state)
    assert set(output.keys()) == {"eo_result"}
    assert "evidence" not in output
    assert "risk_level" not in output
    assert "final_answer" not in output
    assert "ocean_result" not in output
    assert "weather_result" not in output
