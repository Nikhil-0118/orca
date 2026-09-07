"""
Phase 11: Integration Tests for LangGraph MOSDAC EO Agent Orchestration.

Verifies:
- Test A: Full graph chlorophyll query execution with truthful MOSDAC provenance
- Test B: Parallel state preservation across EO, Ocean, and Weather branches
- Test C: Missing coordinates handling without coordinate fabrication
- Test D: End-to-end API integration via POST /api/query
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.core.state import OrcaState
from app.core.graph import orca_graph
from app.agents.eo_agent import _cache
from app.main import app


@pytest.fixture(autouse=True)
def clear_eo_cache():
    """Ensure in-memory cache is clean before and after each test."""
    _cache.clear()
    yield
    _cache.clear()


# ── TEST A: Full Graph Chlorophyll Query ──────────────────────────────────────

@pytest.mark.asyncio
async def test_full_graph_chlorophyll_query_chennai():
    """
    Test A: Run the actual LangGraph flow for:
    Query: 'What is the chlorophyll concentration near Chennai?'
    Location: latitude=13.0827, longitude=80.2707

    Verifies all 12 criteria:
    1. graph executes successfully
    2. EO Agent executes
    3. MOSDAC is selected
    4. EO result is present in final graph state
    5. result source is MOSDAC
    6. parameter is chlorophyll_a
    7. value is numeric/non-null for this known test file
    8. observation date is present
    9. requested coordinates are preserved
    10. grid coordinates are present
    11. no fake unit is introduced
    12. no graph exception occurs
    """
    state: OrcaState = {
        "query": "What is the chlorophyll concentration near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "test-phase11-chennai",
        "selected_agents": None,
        "safety_required": False,
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "ecosystem_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    # 1. Graph executes without exception
    result = await orca_graph.ainvoke(state)
    assert result is not None

    # 2 & 4. EO Agent executes and eo_result is present in final graph state
    assert "eo_result" in result
    eo_res = result["eo_result"]
    assert eo_res is not None

    # 3 & 5. MOSDAC is selected as result source
    assert eo_res.get("source") == "MOSDAC"
    assert eo_res.get("status") == "success"

    # 6. Parameter is chlorophyll_a
    assert eo_res.get("parameter") == "chlorophyll_a"

    # 7. Value is numeric/non-null for this known test file
    val = eo_res.get("value")
    assert isinstance(val, (int, float))
    assert round(val, 4) in (0.0885, 0.0882)

    # 8. Observation date is present
    obs_date = eo_res.get("observation_date")
    assert obs_date in ("2026-09-03", "2026-09-04")

    # 9. Requested coordinates are preserved
    assert eo_res.get("requested_latitude") == 13.0827
    assert eo_res.get("requested_longitude") == 80.2707

    # 10. Grid coordinates are present
    assert eo_res.get("grid_latitude") == 13.012
    assert eo_res.get("grid_longitude") == 80.25
    assert eo_res.get("grid_distance_km") == 8.18

    # 11. No fake unit is introduced
    assert eo_res.get("unit") is None
    assert "Unit metadata not explicitly provided" in eo_res.get("unit_notes", "")

    # Final answer & synthesis assertions
    final_answer = result.get("final_answer", "")
    assert str(val) in final_answer
    assert "MOSDAC" in final_answer
    assert "mg/m³" not in final_answer
    assert "mg/m3" not in final_answer

    # Structured evidence includes MOSDAC
    struct_ev = result.get("structured_evidence") or []
    mosdac_ev = [e for e in struct_ev if "MOSDAC" in e.get("source", "")]
    assert len(mosdac_ev) >= 1
    assert any(num in mosdac_ev[0].get("summary", "") for num in ("0.0885", "0.0882"))

    # Limitations mention local NetCDF archive and unit metadata absence
    limits = result.get("data_limitations") or []
    assert any("MOSDAC NetCDF dataset" in lim for lim in limits)


# ── TEST B: Parallel Result Preservation ─────────────────────────────────────

@pytest.mark.asyncio
async def test_parallel_result_preservation():
    """
    Test B: Run a graph query that causes EO, Ocean, and Weather branches to execute.
    Verify that after graph completion:
    - EO result exists
    - Ocean result exists
    - Weather result exists
    - EO integration does not remove or overwrite Ocean/Weather results
    """
    state: OrcaState = {
        "query": "What is the chlorophyll concentration, wave height, and weather near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "test-phase11-parallel",
        "selected_agents": ["eo", "ocean", "weather"],
        "safety_required": False,
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "ecosystem_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    result = await orca_graph.ainvoke(state)

    # 1. EO result exists and has MOSDAC chlorophyll data
    assert result.get("eo_result") is not None
    assert result["eo_result"].get("source") == "MOSDAC"
    assert result["eo_result"].get("parameter") == "chlorophyll_a"
    assert result["eo_result"].get("value") in (0.0885, 0.0882)

    # 2. Ocean result exists and was not overwritten by EO
    assert result.get("ocean_result") is not None
    ocean_res = result["ocean_result"]
    assert "source" in ocean_res
    assert "status" in ocean_res

    # 3. Weather result exists and was not overwritten by EO
    assert result.get("weather_result") is not None
    weather_res = result["weather_result"]
    assert "source" in weather_res
    assert "status" in weather_res

    # 4. Evidence preserves findings from all active agents
    ev_list = result.get("evidence") or []
    assert any("MOSDAC" in e for e in ev_list)
    assert any("Ocean" in e or "INCOIS" in e for e in ev_list)
    assert any("Weather" in e or "IMD" in e for e in ev_list)


# ── TEST C: Missing Location Handling ────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_location_handling():
    """
    Test C: Run 'What is the chlorophyll concentration?' without a location.
    Verify:
    - The system does NOT silently invent coordinates
    - It marks EO result status as 'unavailable'
    - Value is None
    - Does not call MOSDAC with fabricated coordinates
    """
    state: OrcaState = {
        "query": "What is the chlorophyll concentration?",
        "location": {},
        "session_id": "test-phase11-missing-loc",
        "selected_agents": None,
        "safety_required": False,
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "ecosystem_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    result = await orca_graph.ainvoke(state)

    eo_res = result.get("eo_result")
    assert eo_res is not None
    assert eo_res.get("source") == "MOSDAC"
    assert eo_res.get("status") == "unavailable"
    assert eo_res.get("value") is None
    assert eo_res.get("requested_latitude") is None
    assert eo_res.get("requested_longitude") is None
    assert "no geographic coordinates were provided" in eo_res.get("notes", "")

    # Final answer explains unavailability rather than reporting fake values
    final_answer = result.get("final_answer", "")
    assert "unavailable" in final_answer.lower() or "no geographic coordinates" in final_answer.lower()


# ── TEST D: API Integration Endpoint ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_query_chlorophyll_endpoint():
    """
    Test D: Check API-level integration via POST /api/query.
    Query: 'What is the chlorophyll concentration near Chennai?'
    Location: {'lat': 13.0827, 'lon': 80.2707}
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/query",
            json={
                "query": "What is the chlorophyll concentration near Chennai?",
                "location": {"lat": 13.0827, "lon": 80.2707},
                "session_id": "test-phase11-api",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["mode"] == "marine"
        assert ("0.0885" in data["answer"] or "0.0882" in data["answer"])
        assert "MOSDAC" in data["answer"]
        assert "mg/m³" not in data["answer"]
        assert "mg/m3" not in data["answer"]

        # Structured evidence contains MOSDAC
        struct_ev = data.get("structured_evidence") or []
        assert any("MOSDAC" in e.get("source", "") for e in struct_ev)
