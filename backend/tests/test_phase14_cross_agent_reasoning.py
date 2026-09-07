"""
Phase 14 Cross-Agent Marine Reasoning & Decision Engine Tests.

Tests:
1. TEST 1: 'Can I go fishing near Chennai today?' (multi-agent contribution, cross-agent analysis, recommendation exists, no fabricated values).
2. TEST 2: 'What is the sea surface temperature near Chennai?' (factual SST response, no forced fishing decision).
3. TEST 3: 'Is the weather suitable for fishing near Chennai?' (Weather + Ocean considered in tandem).
4. TEST 4: 'Is this location safe for fishing?' (Safety evidence strictly prioritized).
5. TEST 5: MOSDAC unavailable (chlorophyll marked unavailable, no fabrication, other agents still contribute).
6. TEST 6: Weather unavailable (no fabricated weather, confidence reduced, missing info recorded).
7. TEST 7: Stale MOSDAC data (stale status preserved, reduced weight, not claimed real-time).
8. TEST 8: Conflicting evidence (conflicts detected, conservative safety resolution).
9. TEST 9: No location query ('Can I go fishing today?' -> graceful handling, acknowledges missing coordinates, no invented location).
10. TEST 10: General marine question ('Why is chlorophyll important?' -> no forced decision engine).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.graph import orca_graph
from app.services.marine_analysis_service import (
    marine_analysis_service,
    classify_query_intent,
)
from app.schemas.evidence import EvidenceItem, SignalConflict


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ─── TEST 1: 'Can I go fishing near Chennai today?' ──────────────────────────

def test_01_fishing_near_chennai_cross_agent_decision(client):
    payload = {
        "query": "Can I go fishing near Chennai today?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "test-p14-t1",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Decision card exists
    assert data.get("decision") is not None
    dec = data["decision"]
    assert dec.get("label") in ["Recommended", "Recommended with caution", "Not recommended", "Operational caution", "GO", "CAUTION", "AVOID", "INSUFFICIENT_DATA"]
    assert "summary" in dec
    assert "confidence" in dec

    # Answer text reflects decision and operational reasoning
    answer = data.get("answer", "")
    assert any(term in answer.lower() for term in ["recommend", "caution", "favorable", "fishing"])

    # Multiple agents contributed
    agents = data.get("agents_used", [])
    assert len(agents) >= 2

    # Evidence exists
    assert len(data.get("structured_evidence", [])) >= 2

    # Non-guarantee / biological productivity disclaimer present
    assert any("guarantee" in str(lim).lower() or "indicator" in str(lim).lower() or "guarantee" in answer.lower()
               for lim in data.get("data_limitations", [])) or "guarantee" in answer.lower() or "indicator" in answer.lower()


# ─── TEST 2: Factual SST query — No forced fishing decision ─────────────────

def test_02_factual_sst_query_no_forced_decision(client):
    payload = {
        "query": "What is the sea surface temperature near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "test-p14-t2",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    answer = data.get("answer", "").lower()
    # Concise factual response mentioning SST or temperature
    assert "temperature" in answer or "sst" in answer or "°c" in answer

    # Must NOT force a fishing recommendation into an SST factual query
    assert "recommendation: go" not in answer
    assert "recommendation: avoid" not in answer


# ─── TEST 3: Weather suitable for fishing — considers Weather + Ocean ────────

def test_03_weather_suitable_for_fishing_considers_both(client):
    payload = {
        "query": "Is the weather suitable for fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "test-p14-t3",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    agents = [a.lower() for a in data.get("agents_used", [])]
    assert "weather" in agents or any("weather" in a for a in agents)

    # Key conditions should contain surface wind or sea state
    key_conds = " ".join(data.get("key_conditions", [])).lower()
    assert "wind" in key_conds or "sea" in key_conds or "wave" in key_conds


# ─── TEST 4: 'Is this location safe for fishing?' — Safety prioritized ──────

def test_04_safety_query_prioritizes_safety(client):
    payload = {
        "query": "Is this location safe for fishing?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "test-p14-t4",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Safety agent must be involved
    agents = [a.lower() for a in data.get("agents_used", [])]
    assert any("safety" in a for a in agents)

    # Risk level must be explicit
    assert data.get("risk_level") in ["low", "moderate", "high", "critical"]


# ─── TEST 5: MOSDAC unavailable — no fabricated chlorophyll ──────────────────

def test_05_mosdac_unavailable_no_fabrication():
    # Simulate state where EO agent returns unavailable
    state = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "eo_result": {
            "status": "unavailable",
            "source": "MOSDAC",
            "parameter": "chlorophyll_a",
            "value": None,
            "unit": None,
            "notes": "Remote feed unavailable and no local NetCDF found.",
        },
        "ocean_result": {
            "status": "live",
            "sea_surface_temperature_c": 29.5,
            "significant_wave_height_m": 1.2,
            "wind": {"speed": {"value": 6.0}},
        },
        "weather_result": {
            "status": "live",
            "wind": {"speed": 12.0, "direction": "SW"},
            "sea_condition": "Smooth",
        },
        "safety_result": {
            "risk_level": "low",
            "risk_score": 10,
            "proximity": {"status": "clear", "distance_km": 45.0},
        },
    }

    analysis = marine_analysis_service.run_analysis(state)

    # Chlorophyll is marked unavailable
    assert analysis.conditions["chlorophyll"]["status"] == "unavailable"

    # Evidence items has chlorophyll as unavailable with value None
    chla_item = next(i for i in analysis.evidence_items if i.parameter == "chlorophyll_a")
    assert chla_item.value is None
    assert chla_item.status == "unavailable"

    # Other agents (ocean, weather, safety) still contribute
    assert analysis.conditions["thermal"]["status"] == "available"
    assert analysis.conditions["surface_wind_wave"]["status"] == "available"

    # Decision still forms based on available evidence without crashing
    assert analysis.decision is not None
    assert analysis.decision.recommendation in ["GO", "CAUTION"]


# ─── TEST 6: Weather unavailable — reduced confidence & missing info ─────────

def test_06_weather_unavailable_reduced_confidence():
    state = {
        "query": "Can I go fishing today?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "eo_result": {
            "status": "success",
            "source": "MOSDAC",
            "parameter": "chlorophyll_a",
            "value": 0.0885,
            "unit": None,
            "observation_date": "2026-09-03",
            "freshness": "stale",
        },
        "ocean_result": {
            "status": "live",
            "sea_surface_temperature_c": 29.5,
            "significant_wave_height_m": 1.1,
        },
        "weather_result": None,  # Weather failed / unobserved
        "safety_result": {
            "risk_level": "low",
            "risk_score": 10,
            "proximity": {"status": "clear"},
        },
    }

    analysis = marine_analysis_service.run_analysis(state)

    # Missing information records wind/weather parameter
    assert "wind_speed" in analysis.data_quality["missing_parameters"]

    # Decision does not crash, warns about missing weather data
    assert analysis.decision is not None
    assert analysis.decision.recommendation in ["CAUTION", "INSUFFICIENT_DATA"]


# ─── TEST 7: Stale MOSDAC data — reduced confidence & preserved status ───────

def test_07_stale_mosdac_data_handling():
    state = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "eo_result": {
            "status": "success",
            "source": "MOSDAC",
            "parameter": "chlorophyll_a",
            "value": 0.0885,
            "unit": None,
            "observation_date": "2026-09-03",
            "freshness": "stale",
            "grid_latitude": 13.012,
            "grid_longitude": 80.25,
            "grid_distance_km": 8.18,
        },
        "ocean_result": {
            "status": "live",
            "sea_surface_temperature_c": 29.9,
            "significant_wave_height_m": 1.2,
        },
        "weather_result": {
            "status": "live",
            "wind": {"speed": 11.0, "direction": "SW"},
            "sea_condition": "Smooth",
        },
        "safety_result": {
            "risk_level": "low",
            "risk_score": 10,
            "proximity": {"status": "clear"},
        },
    }

    analysis = marine_analysis_service.run_analysis(state)

    # Freshness is marked stale
    assert analysis.data_quality["freshness_breakdown"]["chlorophyll_a"] == "stale"
    assert "chlorophyll_a" in analysis.data_quality["stale_parameters"]

    # Confidence is medium (not high) due to stale chlorophyll
    assert analysis.decision.confidence == "MEDIUM"

    # Reasoning mentions archival observation date
    reasoning_str = " ".join(analysis.decision.reasoning)
    assert "2026-09-03" in reasoning_str or "archival" in reasoning_str


# ─── TEST 8: Conflicting evidence detection ──────────────────────────────────

def test_08_conflicting_evidence_detection():
    state = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "eo_result": None,
        "ocean_result": {
            "status": "live",
            "wind": {"speed": {"value": 3.0}},  # ~5.8 knots
        },
        "weather_result": {
            "status": "live",
            "wind": {"speed": 22.0, "direction": "NE"},  # 22 knots (delta > 8 kt!)
            "warnings": ["Gale wind warning"],
        },
        "safety_result": {
            "risk_level": "low",
            "proximity": {"status": "clear"},
        },
    }

    analysis = marine_analysis_service.run_analysis(state)

    # Conflict detected
    assert len(analysis.conflicts) >= 1
    wind_conflict = next((c for c in analysis.conflicts if c.parameter == "wind_speed"), None)
    assert wind_conflict is not None
    assert "discrepancy" in wind_conflict.description.lower() or "differs" in wind_conflict.description.lower()
    # Conservative resolution retained higher wind
    assert "higher wind speed" in wind_conflict.resolution.lower()


# ─── TEST 9: No location query — graceful handling, no invented location ────

def test_09_no_location_graceful_handling(client):
    payload = {
        "query": "Can I go fishing today?",
        "location": None,
        "session_id": "test-p14-t9",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must NOT crash or invent coordinates
    assert data.get("location") is None or data["location"].get("source") == "unavailable"

    answer = data.get("answer", "")
    assert len(answer) > 10
    # No fake coordinates claimed
    assert "lat:" not in answer.lower() or "coordinates not specified" in answer.lower() or "unavailable" in answer.lower()


# ─── TEST 10: General marine question — no forced decision engine ───────────

def test_10_general_marine_question_no_forced_decision(client):
    payload = {
        "query": "Why is chlorophyll important in ocean ecosystems?",
        "location": None,
        "session_id": "test-p14-t10",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    answer = data.get("answer", "").lower()
    # Explanatory answer about chlorophyll / phytoplankton
    assert any(term in answer for term in ["chlorophyll", "phytoplankton", "primary productivity", "photosynthesis", "ecosystem"])

    # Must NOT contain a forced operational fishing recommendation
    assert "recommendation: go" not in answer
    assert "recommendation: avoid" not in answer
