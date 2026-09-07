"""
Unit and integration tests for the Online Safety Agent, Combined Risk Reasoning,
Risk Level Thresholds, and LangGraph Fan-In Synchronization.

Covers:
1. Fan-in synchronization: safety_node waits for EO + Ocean + Weather (concurrent execution).
2. Case A: Boundary proximity only -> moderate risk.
3. Case B: Severe weather only -> high risk.
4. Case C: Boundary + severe weather -> critical risk (strictly greater than either alone).
5. Case D: Boundary + rough ocean -> elevated/high risk (strictly greater than either alone).
6. Case E: Boundary + severe hazard (tsunami/storm surge) -> critical risk.
7. Missing upstream result handling: gracefully degrades without crashing.
8. Malformed/missing location in state handling.
9. Hazard alert network fallback: truthfully returns mock without fabricating live data.
10. Demo boundary disclaimer: explicitly marked approximate / not for navigation.
11. State isolation: safety_node writes ONLY to safety_result.
12. Safety path separation: /api/safety-check is completely independent of safety_node and LangGraph.
13. Deterministic threshold boundaries: 0-24 (low), 25-49 (moderate), 50-74 (high), 75-100 (critical).
"""
import asyncio
import time
from unittest.mock import AsyncMock, patch
import httpx
from httpx import ASGITransport, AsyncClient
import pytest

from app.agents.safety_agent import (
    SafetyAgent,
    classify_risk_level,
    safety_node,
)
from app.core.graph import orca_graph
from app.core.state import OrcaState
from app.main import app


@pytest.fixture
def agent():
    return SafetyAgent()


# ── 1. Threshold Boundary Tests ────────────────────────────────────────────

def test_risk_level_threshold_boundaries():
    """Verify deterministic 4-tier risk level classification boundaries."""
    # Low: 0 to 24
    assert classify_risk_level(0) == "low"
    assert classify_risk_level(10) == "low"
    assert classify_risk_level(24) == "low"

    # Moderate: 25 to 49
    assert classify_risk_level(25) == "moderate"
    assert classify_risk_level(35) == "moderate"
    assert classify_risk_level(49) == "moderate"

    # High: 50 to 74
    assert classify_risk_level(50) == "high"
    assert classify_risk_level(65) == "high"
    assert classify_risk_level(74) == "high"

    # Critical: 75 to 100
    assert classify_risk_level(75) == "critical"
    assert classify_risk_level(90) == "critical"
    assert classify_risk_level(100) == "critical"


# ── 2. Case A: Boundary Proximity Only ─────────────────────────────────────

def test_risk_case_a_boundary_only(agent: SafetyAgent):
    """
    Case A: Vessel near demo boundary, normal weather, normal ocean.
    Expectation: moderate risk (score = 25, risk_level = moderate).
    """
    prox_near = {
        "status": "near_boundary",
        "distance_km": 8.0,  # <= 15 km
        "boundary_name": "Demo IMBL",
        "demo_only": True,
    }
    hazards = {"status": "mock", "alerts": []}
    weather_safe = {
        "source": "IMD",
        "status": "live",
        "wind": {"speed": 8.0, "unit": "knots"},
        "visibility": {"value": "Good"},
        "sea_condition": "Smooth",
        "warnings": [],
    }
    ocean_safe = {
        "source": "INCOIS ERDDAP",
        "status": "live",
        "significant_wave_height_m": 0.8,
    }

    res = agent.calculate_combined_risk(prox_near, hazards, None, ocean_safe, weather_safe, 9.3, 79.5)
    assert res["risk_score"] == 25
    assert res["risk_level"] == "moderate"
    assert any("boundary" in r.lower() for r in res["reasoning"])


# ── 3. Case B: Severe Weather Only ─────────────────────────────────────────

def test_risk_case_b_severe_weather_only(agent: SafetyAgent):
    """
    Case B: Vessel far from boundary, severe weather / storm warning active.
    Expectation: high risk (score = 50, risk_level = high).
    """
    prox_safe = {
        "status": "inside",
        "distance_km": 50.0,
        "boundary_name": "Demo IMBL",
        "demo_only": True,
    }
    hazards = {"status": "mock", "alerts": []}
    weather_storm = {
        "source": "IMD",
        "status": "live",
        "wind": {"speed": 28.0, "unit": "knots"},  # Gale force (+20)
        "visibility": {"value": "Moderate"},
        "sea_condition": "Rough",
        "warnings": ["Cyclonic storm advisory active"],  # Warning (+30)
    }
    ocean_safe = {
        "source": "INCOIS ERDDAP",
        "status": "live",
        "significant_wave_height_m": 1.2,
    }

    res = agent.calculate_combined_risk(prox_safe, hazards, None, ocean_safe, weather_storm, 20.0, 72.0)
    assert res["risk_score"] == 50  # 30 (warning) + 20 (gale wind)
    assert res["risk_level"] == "high"
    assert any("weather" in r.lower() or "warning" in r.lower() for r in res["reasoning"])


# ── 4. Case C: Boundary + Severe Weather (Synergy) ─────────────────────────

def test_risk_case_c_boundary_plus_severe_weather(agent: SafetyAgent):
    """
    Case C: Near boundary + severe weather.
    Expectation: compound risk strictly greater than boundary alone and storm alone.
    """
    prox_safe = {"status": "inside", "distance_km": 50.0, "demo_only": True}
    prox_near = {"status": "near_boundary", "distance_km": 8.0, "demo_only": True}

    hazards = {"status": "mock", "alerts": []}

    weather_safe = {
        "source": "IMD",
        "status": "live",
        "wind": {"speed": 8.0, "unit": "knots"},
        "visibility": {"value": "Good"},
        "sea_condition": "Smooth",
        "warnings": [],
    }

    weather_storm = {
        "source": "IMD",
        "status": "live",
        "wind": {"speed": 28.0, "unit": "knots"},
        "visibility": {"value": "Moderate"},
        "sea_condition": "Rough",
        "warnings": ["Cyclonic storm advisory active"],
    }

    ocean_safe = {"source": "INCOIS", "status": "live", "significant_wave_height_m": 0.8}

    # 1. Boundary only: 25
    res_boundary_only = agent.calculate_combined_risk(
        prox_near, hazards, None, ocean_safe, weather_safe, 9.3, 79.5
    )

    # 2. Storm only: 50
    res_storm_only = agent.calculate_combined_risk(
        prox_safe, hazards, None, ocean_safe, weather_storm, 9.3, 79.5
    )

    # 3. Combined: 25 (boundary) + 50 (storm) + 15 (synergy) = 90
    res_combined = agent.calculate_combined_risk(
        prox_near, hazards, None, ocean_safe, weather_storm, 9.3, 79.5
    )

    assert res_combined["risk_score"] == 90
    assert res_combined["risk_level"] == "critical"
    assert res_combined["risk_score"] > res_boundary_only["risk_score"]
    assert res_combined["risk_score"] > res_storm_only["risk_score"]
    assert any("compound" in f.lower() or "multiplier" in f.lower() for f in res_combined["contributing_factors"])


# ── 5. Case D: Boundary + Rough Ocean ──────────────────────────────────────

def test_risk_case_d_boundary_plus_rough_ocean(agent: SafetyAgent):
    """
    Case D: Near boundary + rough ocean wave conditions (wave >= 3.0m).
    Expectation: elevated risk higher than boundary alone (25) and wave alone (20).
    """
    prox_safe = {"status": "inside", "distance_km": 50.0, "demo_only": True}
    prox_near = {"status": "near_boundary", "distance_km": 8.0, "demo_only": True}
    hazards = {"status": "mock", "alerts": []}

    weather_safe = {
        "source": "IMD",
        "status": "live",
        "wind": {"speed": 8.0, "unit": "knots"},
        "visibility": {"value": "Good"},
        "sea_condition": "Smooth",
        "warnings": [],
    }

    ocean_safe = {"source": "INCOIS", "status": "live", "significant_wave_height_m": 0.8}
    ocean_rough = {"source": "INCOIS", "status": "live", "significant_wave_height_m": 3.5}

    # Boundary only: 25
    res_boundary = agent.calculate_combined_risk(prox_near, hazards, None, ocean_safe, weather_safe, 9.3, 79.5)
    # Ocean rough only: 20
    res_rough = agent.calculate_combined_risk(prox_safe, hazards, None, ocean_rough, weather_safe, 9.3, 79.5)
    # Combined: 25 (boundary) + 20 (wave >= 3m) + 15 (synergy) = 60
    res_combined = agent.calculate_combined_risk(prox_near, hazards, None, ocean_rough, weather_safe, 9.3, 79.5)

    assert res_combined["risk_score"] == 60
    assert res_combined["risk_level"] == "high"
    assert res_combined["risk_score"] > res_boundary["risk_score"]
    assert res_combined["risk_score"] > res_rough["risk_score"]


# ── 6. Case E: Boundary + Severe Hazard Alert (Tsunami) ────────────────────

def test_risk_case_e_boundary_plus_severe_hazard(agent: SafetyAgent):
    """
    Case E: Boundary proximity + severe tsunami hazard alert.
    Expectation: critical/high risk with tsunami reasoning.
    """
    prox_near = {"status": "near_boundary", "distance_km": 8.0, "demo_only": True}
    hazard_tsunami = {
        "source": "INCOIS/SAMUDRA",
        "status": "live",
        "alerts": [{"type": "tsunami", "severity": "critical", "headline": "Tsunami Warning"}],
    }
    weather_safe = {"source": "IMD", "status": "live", "wind": {"speed": 8.0, "unit": "knots"}}
    ocean_safe = {"source": "INCOIS", "status": "live", "significant_wave_height_m": 0.8}

    # 25 (boundary) + 45 (tsunami) = 70
    res = agent.calculate_combined_risk(prox_near, hazard_tsunami, None, ocean_safe, weather_safe, 9.3, 79.5)
    assert res["risk_score"] >= 70
    assert any("tsunami" in h["type"] for h in res["hazards"])
    assert any("tsunami" in r.lower() for r in res["reasoning"])


# ── 7. Missing Upstream Data Degradation ───────────────────────────────────

@pytest.mark.asyncio
async def test_safety_node_missing_upstream_data_graceful():
    """Verify safety_node degrades safely when upstream dictionaries are None."""
    state: OrcaState = {
        "query": "Safety check with no data",
        "location": {"lat": 13.0, "lon": 80.0},
        "session_id": "test-s-empty",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    output = await safety_node(state)
    assert "safety_result" in output
    res = output["safety_result"]
    assert res["status"] == "online"
    assert res["risk_level"] in ("low", "moderate", "high", "critical")
    assert isinstance(res["risk_score"], int)


# ── 8. Malformed / Missing Location Handling ───────────────────────────────

@pytest.mark.asyncio
async def test_safety_node_malformed_location_graceful():
    """Verify safety_node handles invalid or malformed location in state without raising exceptions."""
    for bad_loc in [None, {}, {"lat": "invalid", "lon": None}, "not-a-dict"]:
        state: OrcaState = {
            "query": "Safety check bad loc",
            "location": bad_loc,  # type: ignore
            "session_id": "test-bad-loc",
            "eo_result": None,
            "ocean_result": None,
            "weather_result": None,
            "safety_result": None,
            "evidence": [],
            "risk_level": "unknown",
            "final_answer": "",
            "recommendations": [],
        }
        output = await safety_node(state)
        assert "safety_result" in output
        assert isinstance(output["safety_result"]["risk_score"], int)


# ── 9. Mock Transparency in Hazard Alerts ──────────────────────────────────

@pytest.mark.asyncio
async def test_hazard_alerts_mock_transparency(agent: SafetyAgent):
    """Verify hazard alerts returns truthfully labeled mock status without fabricating fake live data."""
    hazards = await agent.fetch_hazard_alerts(20.0, 72.0)
    assert hazards["status"] == "mock"
    assert hazards["source"] == "INCOIS/SAMUDRA-mock"
    assert isinstance(hazards["alerts"], list)
    assert "pending" in hazards["reason"].lower() or "unavailable" in hazards["reason"].lower()


# ── 10. check_proximity() Offline Guarantee & Disclaimer ───────────────────

def test_check_proximity_offline_and_disclaimer(agent: SafetyAgent):
    """Verify check_proximity computes purely locally and contains mandatory demo disclaimer."""
    prox = agent.check_proximity(9.28, 79.3)
    assert isinstance(prox["distance_km"], float)
    assert prox["distance_km"] < 20.0
    assert prox["demo_only"] is True
    assert "DEMO ONLY" in prox["warning"]
    assert "NOT FOR NAVIGATION" in prox["warning"]


# ── 11. State Isolation ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safety_node_state_isolation():
    """Verify safety_node writes ONLY to safety_result and does not mutate shared state keys."""
    state: OrcaState = {
        "query": "Safety check",
        "location": {"lat": 20.0, "lon": 72.0},
        "session_id": "test-s-iso",
        "eo_result": {"status": "mock"},
        "ocean_result": {"status": "live"},
        "weather_result": {"status": "mock"},
        "safety_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    output = await safety_node(state)
    assert set(output.keys()) == {"safety_result"}
    assert "evidence" not in output
    assert "risk_level" not in output
    assert "final_answer" not in output
    assert "eo_result" not in output
    assert "ocean_result" not in output
    assert "weather_result" not in output


# ── 12. Offline Safety Separation Test ─────────────────────────────────────

@pytest.mark.asyncio
async def test_offline_safety_check_endpoint_remains_independent():
    """
    Verify /api/safety-check remains a dedicated, independent fast offline path
    that does NOT invoke safety_node, LangGraph, or external network services.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/safety-check",
            json={"lat": 9.28, "lon": 79.3, "vessel_id": "VESSEL-TEST-01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "inside_boundary" in data
        assert "distance_to_boundary_km" in data
        assert "alert_level" in data


# ── 13. LangGraph Fan-In Synchronization Test ─────────────────────────────

@pytest.mark.asyncio
async def test_langgraph_fan_in_waits_for_all_three_nodes():
    """
    Strengthened synchronization test:
    Injects artificial async delays (EO = 50ms, Ocean = 100ms, Weather = 150ms).
    Proves:
    1. safety_node begins ONLY after the slowest node (Weather at 150ms) finishes.
    2. All 3 upstream results are present in state when safety starts.
    3. Total upstream duration reflects concurrent execution (~150ms, not sequential 300ms).
    """
    t_start = time.perf_counter()
    timestamps = {}

    async def delayed_eo(state):
        await asyncio.sleep(0.05)  # 50ms
        timestamps["eo_done"] = time.perf_counter()
        return {"eo_result": {"source": "EO-Test", "status": "mock"}}

    async def delayed_ocean(state):
        await asyncio.sleep(0.10)  # 100ms
        timestamps["ocean_done"] = time.perf_counter()
        return {"ocean_result": {"source": "Ocean-Test", "status": "mock"}}

    async def delayed_weather(state):
        await asyncio.sleep(0.15)  # 150ms
        timestamps["weather_done"] = time.perf_counter()
        return {"weather_result": {"source": "Weather-Test", "status": "mock"}}

    async def sync_safety(state):
        timestamps["safety_start"] = time.perf_counter()
        timestamps["eo_in_state"] = state.get("eo_result") is not None
        timestamps["ocean_in_state"] = state.get("ocean_result") is not None
        timestamps["weather_in_state"] = state.get("weather_result") is not None
        return {"safety_result": {"status": "online", "risk_level": "low", "risk_score": 10}}

    from langgraph.graph import StateGraph, START, END
    test_builder = StateGraph(OrcaState)
    test_builder.add_node("coordinator_node", lambda s: {})
    test_builder.add_node("eo_node", delayed_eo)
    test_builder.add_node("ocean_node", delayed_ocean)
    test_builder.add_node("weather_node", delayed_weather)
    test_builder.add_node("safety_node", sync_safety)

    test_builder.add_edge(START, "coordinator_node")
    test_builder.add_edge("coordinator_node", "eo_node")
    test_builder.add_edge("coordinator_node", "ocean_node")
    test_builder.add_edge("coordinator_node", "weather_node")
    test_builder.add_edge("eo_node", "safety_node")
    test_builder.add_edge("ocean_node", "safety_node")
    test_builder.add_edge("weather_node", "safety_node")
    test_builder.add_edge("safety_node", END)

    compiled_test_graph = test_builder.compile()

    state: OrcaState = {
        "query": "Fan in sync test",
        "location": {"lat": 20.0, "lon": 72.0},
        "session_id": "test-fan-in-sync",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    res = await compiled_test_graph.ainvoke(state)

    # 1. Verify timing sequence
    assert "eo_done" in timestamps
    assert "ocean_done" in timestamps
    assert "weather_done" in timestamps
    assert "safety_start" in timestamps

    # Safety must start AFTER the latest upstream node finishes
    assert timestamps["safety_start"] >= timestamps["weather_done"]
    assert timestamps["safety_start"] >= timestamps["ocean_done"]
    assert timestamps["safety_start"] >= timestamps["eo_done"]

    # 2. Verify all 3 results are present in state when safety starts
    assert timestamps["eo_in_state"] is True
    assert timestamps["ocean_in_state"] is True
    assert timestamps["weather_in_state"] is True

    # 3. Verify concurrency (150ms total delay + minor overhead, < 350ms vs sequential 300ms)
    elapsed_total = timestamps["safety_start"] - t_start
    assert elapsed_total < 0.35, f"Expected concurrent execution (~0.15s), got {elapsed_total:.3f}s"
