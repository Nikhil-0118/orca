"""
Tests for the three core /api endpoints: health, query, safety-check.
Includes LangGraph integration tests verifying ocean_node flows through the compiled graph.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── GET /api/health ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ── POST /api/query ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_returns_expected_shape(client: AsyncClient):
    response = await client.post(
        "/api/query",
        json={
            "query": "Is it safe to fish near Chennai today?",
            "location": {"lat": 13.0827, "lon": 80.2707},
            "session_id": "test-session-001",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["answer"], str)
    assert isinstance(data["evidence"], list)
    assert isinstance(data["risk_level"], str)
    assert isinstance(data["recommendations"], list)


@pytest.mark.asyncio
async def test_query_without_location(client: AsyncClient):
    response = await client.post(
        "/api/query",
        json={
            "query": "What is the current sea temperature?",
            "session_id": "test-session-002",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "risk_level" in data


@pytest.mark.asyncio
async def test_query_rejects_missing_session_id(client: AsyncClient):
    response = await client.post(
        "/api/query",
        json={"query": "Hello"},
    )
    assert response.status_code == 422  # validation error


# ── POST /api/query — LangGraph ocean_node integration ────────────────────

@pytest.mark.asyncio
async def test_query_ocean_node_populates_evidence(client: AsyncClient):
    """Verify that a sea-state query flows through the LangGraph and ocean_result is populated."""
    response = await client.post(
        "/api/query",
        json={
            "query": "What are the current wave conditions off the coast?",
            "location": {"lat": 13.0827, "lon": 80.2707},
            "session_id": "test-graph-001",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Evidence should contain an entry from the ocean node
    assert len(data["evidence"]) > 0
    assert any("Ocean state data" in e for e in data["evidence"])

    # Answer should reference ocean data (wave height / SST / sea state)
    answer = data["answer"].lower()
    assert any(term in answer for term in ["wave", "sea state", "sst"])


@pytest.mark.asyncio
async def test_query_ocean_node_risk_level(client: AsyncClient):
    """Verify risk_level is derived from ocean data (mock has 1.8m waves → low)."""
    response = await client.post(
        "/api/query",
        json={
            "query": "Is the sea calm enough to go fishing?",
            "location": {"lat": 12.95, "lon": 80.14},
            "session_id": "test-graph-002",
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Mock returns 1.8m wave height → risk_level should be "low"
    assert data["risk_level"] == "low"


# ── POST /api/safety-check ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safety_check_returns_expected_shape(client: AsyncClient):
    response = await client.post(
        "/api/safety-check",
        json={"lat": 13.0827, "lon": 80.2707},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["inside_boundary"], bool)
    assert isinstance(data["distance_to_boundary_km"], (int, float))
    assert isinstance(data["alert_level"], str)


@pytest.mark.asyncio
async def test_safety_check_rejects_invalid_coords(client: AsyncClient):
    response = await client.post(
        "/api/safety-check",
        json={"lat": 999, "lon": 80.0},
    )
    assert response.status_code == 422  # out of range
