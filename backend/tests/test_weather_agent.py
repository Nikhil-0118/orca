"""
Unit and integration tests for the official IMD Weather Agent and Mock Transparency.

Covers:
1. Successful IMD response parsing & normalization (status: "live").
2. HTTP 401 fallback (invalid or missing key).
3. HTTP 403 fallback (forbidden).
4. Timeout fallback.
5. Network exception fallback.
6. Malformed JSON handling.
7. Empty response handling.
8. Missing API key handling.
9. Missing response fields handling.
10. 15-minute cache hit behavior.
11. Cache expiry behavior.
12. Freshness calculation & boundaries.
13. Mock transparency in API query output.
14. State isolation (returns ONLY {"weather_result": ...}).
"""
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from httpx import ASGITransport, AsyncClient

from app.agents import weather_agent
from app.agents.weather_agent import (
    weather_node,
    _cache,
    _cache_ts,
    _calculate_data_age_hours,
    _classify_freshness,
    _parse_wind_field,
)
from app.core.state import OrcaState
from app.main import app


MOCK_IMD_COASTAL_BULLETIN_RESPONSE = [
    {
        "Id": "108",
        "Date of Observation": "2023-03-28",
        "Layer": "North Maharashtra - South Gujarat coast",
        "Issued by": "ACWC MUMBAI",
        "Valid From": "2023-03-28 22:00:00",
        "Validity": "12",
        "TTT Warning": "Squally weather with wind speed reaching 45-55 kmph",
        "Wind": "South Westerly/ South Easterly, 10 - 15 Knots",
        "Synoptic Situation": "Low pressure area over Eastcentral Arabian Sea",
        "Weather": "Isolated Rain/ Thunderstorm",
        "Visibility": "Good Becoming Poor",
        "Sea Condition": "Smooth to Slight",
        "Port Signal": "NIL at all Ports",
        "Update Time": "2023-03-28 22:27:17",
    }
]


@pytest.fixture(autouse=True)
def clear_weather_cache():
    """Clear Weather cache before and after each test."""
    _cache.clear()
    _cache_ts.clear()
    yield
    _cache.clear()
    _cache_ts.clear()


# ── Test 1: Successful IMD response parsing ────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_successful_parsing():
    """Verify successful parsing of valid IMD coastal bulletin JSON into normalized live structure."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_IMD_COASTAL_BULLETIN_RESPONSE

    with patch("app.config.settings.IMD_API_KEY", "mock-valid-key"), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):

        state: OrcaState = {
            "query": "Weather near Mumbai coast",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-w-s1",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        assert "weather_result" in output
        res = output["weather_result"]

        assert res["source"] == "IMD"
        assert res["status"] == "live"
        assert res["data_time"] == "2023-03-28T22:27:17Z"
        assert "retrieved_at" in res
        assert isinstance(res["data_age_hours"], float)
        assert res["freshness"] == "historical"
        assert res["zone"] == "North Maharashtra - South Gujarat coast"
        assert res["sea_condition"] == "Smooth to Slight"
        assert res["visibility"]["value"] == "Good Becoming Poor"

        # Check parsed wind speed & direction
        assert res["wind"]["speed"] == 12.5  # Mean of 10 and 15
        assert res["wind"]["unit"] == "knots"
        assert "South Westerly" in res["wind"]["direction"]

        # Check warnings
        assert len(res["warnings"]) == 1
        assert "Squally" in res["warnings"][0]


# ── Test 2: HTTP 401 fallback ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_http_401():
    """Verify HTTP 401 Unauthorized falls back to mock with clear auth reason."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 401

    with patch("app.config.settings.IMD_API_KEY", "invalid-key"), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):

        state: OrcaState = {
            "query": "Weather query",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-w-401",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        res = output["weather_result"]
        assert res["status"] == "mock"
        assert res["source"] == "IMD-mock"
        assert "401" in res["reason"]


# ── Test 3: HTTP 403 fallback ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_http_403():
    """Verify HTTP 403 Forbidden falls back to mock with clear permission reason."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 403

    with patch("app.config.settings.IMD_API_KEY", "forbidden-key"), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):

        state: OrcaState = {
            "query": "Weather query",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-w-403",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        res = output["weather_result"]
        assert res["status"] == "mock"
        assert "403" in res["reason"]


# ── Test 4: Timeout fallback ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_timeout():
    """Verify timeout falls back to mock safely without raising exceptions."""
    with patch("app.config.settings.IMD_API_KEY", "mock-key"), \
         patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Read timeout")):

        state: OrcaState = {
            "query": "Weather query",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-w-timeout",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        res = output["weather_result"]
        assert res["status"] == "mock"
        assert "timeout" in res["reason"].lower()


# ── Test 5: Network exception fallback ─────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_network_exception():
    """Verify network connection errors fall back to mock safely."""
    with patch("app.config.settings.IMD_API_KEY", "mock-key"), \
         patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):

        state: OrcaState = {
            "query": "Weather query",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-w-net-err",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        res = output["weather_result"]
        assert res["status"] == "mock"


# ── Test 6: Malformed JSON handling ────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_malformed_json():
    """Verify unexpected response structure falls back to mock without crashing."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": "unexpected format, not a list"}

    with patch("app.config.settings.IMD_API_KEY", "mock-key"), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):

        state: OrcaState = {
            "query": "Weather query",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-w-malformed",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        res = output["weather_result"]
        assert res["status"] == "mock"


# ── Test 7: Empty response handling ────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_empty_response():
    """Verify empty list from IMD API falls back to mock."""
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    with patch("app.config.settings.IMD_API_KEY", "mock-key"), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):

        state: OrcaState = {
            "query": "Weather query",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-w-empty",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        res = output["weather_result"]
        assert res["status"] == "mock"
        assert "no coastal bulletins" in res["reason"].lower()


# ── Test 8: Missing API key handling ───────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_missing_api_key():
    """Verify that unconfigured IMD_API_KEY immediately falls back with clear reason."""
    with patch("app.config.settings.IMD_API_KEY", None):
        state: OrcaState = {
            "query": "Weather query",
            "location": {"lat": 20.0, "lon": 72.0},
            "session_id": "test-w-no-key",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        res = output["weather_result"]
        assert res["status"] == "mock"
        assert res["reason"] == "IMD_API_KEY not configured"


# ── Test 9: Missing response fields handling ───────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_missing_fields():
    """Verify partial bulletin with missing optional fields parses safely."""
    partial_bulletin = [
        {
            "Id": "100",
            "Date of Observation": "2026-09-01",
            "Layer": "Kerala coast",
            "Wind": None,
            "Visibility": None,
            "Sea Condition": None,
        }
    ]
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = partial_bulletin

    with patch("app.config.settings.IMD_API_KEY", "mock-key"), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):

        state: OrcaState = {
            "query": "Weather near Kochi",
            "location": {"lat": 9.93, "lon": 76.26},
            "session_id": "test-w-partial",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        output = await weather_node(state)
        res = output["weather_result"]
        assert res["status"] == "live"
        assert res["zone"] == "Kerala coast"
        assert res["wind"]["speed"] is None
        assert res["visibility"]["value"] == "Good"


# ── Test 10 & 11: 15-minute cache & expiry ─────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_cache_and_expiry():
    """Verify 15-minute cache prevents repeated calls and respects TTL."""
    mock_post = AsyncMock()
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_IMD_COASTAL_BULLETIN_RESPONSE
    mock_post.return_value = mock_resp

    with patch("app.config.settings.IMD_API_KEY", "mock-key"), \
         patch("httpx.AsyncClient.get", mock_post):

        state: OrcaState = {
            "query": "Weather check",
            "location": {"lat": 18.0, "lon": 73.0},
            "session_id": "test-w-cache",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }

        # 1. First call -> network request
        out1 = await weather_node(state)
        assert mock_post.call_count == 1

        # 2. Second call -> cache hit
        out2 = await weather_node(state)
        assert mock_post.call_count == 1
        assert out1["weather_result"] == out2["weather_result"]

        # 3. Simulate cache expiry (> 15 minutes)
        key = (18.0, 73.0)
        weather_agent._cache_ts[key] = weather_agent._cache_ts[key] - (16 * 60)
        out3 = await weather_node(state)
        assert mock_post.call_count == 2


# ── Test 12: Freshness boundaries ──────────────────────────────────────────

def test_weather_freshness_boundaries():
    """Verify data age calculation and freshness classification tiers for IMD weather bulletins."""
    t_ret = "2026-09-01T12:00:00Z"

    # Fresh: 4 hours ago
    t_fresh = "2026-09-01T08:00:00Z"
    age_fresh = _calculate_data_age_hours(t_fresh, t_ret)
    assert age_fresh == 4.0
    assert _classify_freshness(age_fresh) == "fresh"

    # Stale: 48 hours ago
    t_stale = "2026-08-30T12:00:00Z"
    age_stale = _calculate_data_age_hours(t_stale, t_ret)
    assert age_stale == 48.0
    assert _classify_freshness(age_stale) == "stale"

    # Historical: 300 hours ago
    t_hist = "2026-08-19T00:00:00Z"
    age_hist = _calculate_data_age_hours(t_hist, t_ret)
    assert age_hist > 168.0
    assert _classify_freshness(age_hist) == "historical"


# ── Test 13: Mock transparency in /api/query ───────────────────────────────

@pytest.mark.asyncio
async def test_weather_mock_transparency():
    """Verify /api/query clearly labels unconfigured IMD as simulated/pending in answer & evidence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/query",
            json={
                "query": "What are the marine conditions off Chennai?",
                "location": {"lat": 13.08, "lon": 80.27},
                "session_id": "test-w-transparency",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check evidence explicitly flags weather mock
        assert any("Weather data" in e and "mock" in e.lower() for e in data["evidence"])

        # Check answer or data_limitations explicitly demarcates simulated weather data
        answer = data["answer"]
        limitations = data.get("data_limitations", [])
        assert (
            "[SIMULATED WEATHER DATA]" in answer
            or "mock" in answer.lower()
            or any("simulated" in lim.lower() or "mock" in lim.lower() for lim in limitations)
        )


# ── Test 14: State isolation ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_node_state_isolation():
    """Verify weather_node writes ONLY to weather_result without mutating shared keys."""
    state: OrcaState = {
        "query": "Weather test",
        "location": {"lat": 13.0, "lon": 80.0},
        "session_id": "test-w-isolation",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    output = await weather_node(state)
    assert set(output.keys()) == {"weather_result"}
    assert "evidence" not in output
    assert "risk_level" not in output
    assert "final_answer" not in output
    assert "eo_result" not in output
    assert "ocean_result" not in output
