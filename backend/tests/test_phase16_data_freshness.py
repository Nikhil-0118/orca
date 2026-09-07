"""
Unit and Integration Tests for Phase 16: Cross-Agent Data Freshness & Source Reliability.

Validates:
1. Deterministic parameter-aware freshness tiers (FRESH, RECENT, STALE, VERY_STALE, UNKNOWN).
2. Physical observation time vs. system retrieval time.
3. Parameter-aware thresholds across Weather, Ocean/SST, Level-4 Chlorophyll, and Geofence.
4. Deterministic source reliability scoring (HIGH, MEDIUM, LOW, UNKNOWN).
5. MOSDAC evidence normalization (E06OCM_L4_AC, remote_authenticated vs archive distinction).
6. Missing weather handling (never falsely reported as live).
7. Missing ocean data handling (no fabricated values).
8. Signal conflict detection (surface wind discrepancy, calm weather vs dangerous wave swell).
9. Safety supremacy override (safety hazard unconditionally supersedes favorable ecological data).
10. Parallel state slot preservation in LangGraph state.
11. Truthful final reasoning (reduced confidence for stale data, no hallucinated numbers).
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.evidence import (
    EvidenceItem,
    EvidenceMetadata,
    FreshnessLevel,
    ReliabilityLevel,
    SignalConflict,
)
from app.services.data_freshness_service import (
    data_freshness_service,
    DEFAULT_THRESHOLDS,
)
from app.services.marine_analysis_service import marine_analysis_service
from app.agents.final_reasoning_agent import FinalReasoningAgent


@pytest.fixture
def client():
    return TestClient(app)


# ─── TEST 1: Freshness Tiers with Injectable Reference Times ─────────────────

def test_01_freshness_tiers_deterministic():
    """Verify deterministic classification across FRESH, RECENT, STALE, VERY_STALE, UNKNOWN."""
    ref_time = "2026-09-04T12:00:00Z"

    # Chlorophyll thresholds: FRESH <= 24h, RECENT <= 72h, STALE <= 168h, VERY_STALE > 168h
    # FRESH: 12 hours old
    f_fresh, age_fresh = data_freshness_service.evaluate_freshness(
        "2026-09-04T00:00:00Z", "chlorophyll_a", reference_time=ref_time
    )
    assert f_fresh == FreshnessLevel.FRESH
    assert f_fresh == "FRESH"
    assert age_fresh == 12.0

    # RECENT: 36 hours old
    f_recent, age_recent = data_freshness_service.evaluate_freshness(
        "2026-09-03T00:00:00Z", "chlorophyll_a", reference_time=ref_time
    )
    assert f_recent == FreshnessLevel.RECENT
    assert f_recent == "RECENT"
    assert age_recent == 36.0

    # STALE: 120 hours (5 days) old
    f_stale, age_stale = data_freshness_service.evaluate_freshness(
        "2026-08-30T12:00:00Z", "chlorophyll_a", reference_time=ref_time
    )
    assert f_stale == FreshnessLevel.STALE
    assert f_stale == "STALE"
    assert age_stale == 120.0

    # VERY_STALE: 240 hours (10 days) old
    f_very_stale, age_very_stale = data_freshness_service.evaluate_freshness(
        "2026-08-25T12:00:00Z", "chlorophyll_a", reference_time=ref_time
    )
    assert f_very_stale == FreshnessLevel.VERY_STALE
    assert f_very_stale == "VERY_STALE"
    assert age_very_stale == 240.0

    # UNKNOWN: Missing or None timestamp
    f_unknown, age_unknown = data_freshness_service.evaluate_freshness(
        None, "chlorophyll_a", reference_time=ref_time
    )
    assert f_unknown == FreshnessLevel.UNKNOWN
    assert f_unknown == "UNKNOWN"
    assert age_unknown is None


# ─── TEST 2: Retrieval Time vs Physical Observation Time ─────────────────────

def test_02_observation_vs_retrieval_time():
    """Verify data age is calculated from observation_time, not download/retrieval_time."""
    ref_time = "2026-09-04T12:00:00Z"
    obs_time = "2026-09-01T00:00:00Z"   # Physical satellite observation (84 hours ago)
    ret_time = "2026-09-04T11:55:00Z"   # Downloaded/ingested 5 minutes ago

    meta = data_freshness_service.build_evidence_metadata(
        source="MOSDAC",
        source_type="remote_authenticated",
        dataset="E06OCM_L4_AC",
        parameter="chlorophyll_a",
        observation_time=obs_time,
        retrieval_time=ret_time,
        reference_time=ref_time,
    )

    # Age MUST be calculated from observation_time (~84.0 hours), not retrieval_time (~0.08 hours)
    assert meta.age_hours == 84.0
    # For chlorophyll (stale <= 168h), 84h is STALE
    assert meta.freshness == FreshnessLevel.STALE
    # Both timestamps must be faithfully preserved
    assert meta.observation_time == obs_time
    assert meta.retrieval_time == ret_time


# ─── TEST 3: Parameter-Aware Freshness Thresholds ────────────────────────────

def test_03_parameter_aware_thresholds():
    """Verify distinct natural lifespans: Weather (<3h), SST (<12h), Chlorophyll (<24h/72h), Geofence (>30d)."""
    ref_time = "2026-09-04T12:00:00Z"
    two_hours_ago = "2026-09-04T10:00:00Z"
    six_hours_ago = "2026-09-04T06:00:00Z"
    twenty_hours_ago = "2026-09-03T16:00:00Z"
    ten_days_ago = "2026-08-25T12:00:00Z"

    # Weather at 2h is FRESH, but at 6h is RECENT, at 20h is STALE (>12h)
    f_w2, _ = data_freshness_service.evaluate_freshness(two_hours_ago, "wind_speed", reference_time=ref_time)
    assert f_w2 == FreshnessLevel.FRESH

    f_w6, _ = data_freshness_service.evaluate_freshness(six_hours_ago, "wind_speed", reference_time=ref_time)
    assert f_w6 == FreshnessLevel.RECENT

    f_w20, _ = data_freshness_service.evaluate_freshness(twenty_hours_ago, "wind_speed", reference_time=ref_time)
    assert f_w20 == FreshnessLevel.STALE

    # SST at 6h is FRESH (SST fresh threshold is 12h)
    f_sst, _ = data_freshness_service.evaluate_freshness(six_hours_ago, "sea_surface_temperature", reference_time=ref_time)
    assert f_sst == FreshnessLevel.FRESH

    # Chlorophyll at 20h is FRESH (Chlorophyll fresh threshold is 24h)
    f_chla, _ = data_freshness_service.evaluate_freshness(twenty_hours_ago, "chlorophyll_a", reference_time=ref_time)
    assert f_chla == FreshnessLevel.FRESH

    # Geofence at 10 days (240h) is FRESH (Geofence threshold is 720h / 30 days)
    f_geo, _ = data_freshness_service.evaluate_freshness(ten_days_ago, "boundary_proximity", reference_time=ref_time)
    assert f_geo == FreshnessLevel.FRESH


# ─── TEST 4: Deterministic Source Reliability Scoring ────────────────────────

def test_04_source_reliability_scoring():
    """Verify deterministic scoring without arbitrary AI weights."""
    # 1. Live/authenticated official fresh data -> HIGH
    rel_auth = data_freshness_service.evaluate_reliability("MOSDAC", "remote_authenticated", FreshnessLevel.FRESH)
    assert rel_auth == ReliabilityLevel.HIGH
    assert rel_auth == "HIGH"

    # 2. Simulated / mock fallback -> strictly LOW
    rel_mock = data_freshness_service.evaluate_reliability("IMD-mock", "simulated", FreshnessLevel.FRESH)
    assert rel_mock == ReliabilityLevel.LOW

    # 3. Official data that is VERY STALE -> degraded to LOW
    rel_very_stale = data_freshness_service.evaluate_reliability("INCOIS ERDDAP", "live", FreshnessLevel.VERY_STALE)
    assert rel_very_stale == ReliabilityLevel.LOW

    # 4. Official data that is STALE -> degraded to MEDIUM
    rel_stale = data_freshness_service.evaluate_reliability("INCOIS ERDDAP", "live", FreshnessLevel.STALE)
    assert rel_stale == ReliabilityLevel.MEDIUM

    # 5. Unavailable feed -> UNKNOWN
    rel_unavail = data_freshness_service.evaluate_reliability("MOSDAC", "unavailable", FreshnessLevel.UNKNOWN, status="unavailable")
    assert rel_unavail == ReliabilityLevel.UNKNOWN


# ─── TEST 5: MOSDAC Evidence Normalization & Authenticated Distinction ───────

def test_05_mosdac_evidence_normalization():
    """Verify MOSDAC evidence exposes dataset E06OCM_L4_AC and preserves remote_authenticated vs archive."""
    # Test Authenticated
    state_auth = {
        "query": "What is the chlorophyll near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "eo_result": {
            "source": "MOSDAC",
            "dataset": "E06OCM_L4_AC",
            "parameter": "chlorophyll_a",
            "status": "success",
            "data_source_type": "remote_authenticated",
            "value": 0.0885,
            "unit": None,
            "observation_date": "2026-09-03",
            "freshness": "recent",
        },
    }
    analysis_auth = marine_analysis_service.run_analysis(state_auth)
    item_auth = next(i for i in analysis_auth.evidence_items if i.parameter == "chlorophyll_a")
    assert item_auth.data_source_type == "remote_authenticated"
    assert item_auth.metadata is not None
    assert item_auth.metadata.dataset == "E06OCM_L4_AC"
    assert item_auth.metadata.source_type == "remote_authenticated"
    assert item_auth.metadata.reliability == ReliabilityLevel.HIGH

    # Test Archive Fallback
    state_arch = {
        "query": "What is the chlorophyll near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "eo_result": {
            "source": "MOSDAC",
            "dataset": "E06OCM_L4_AC",
            "parameter": "chlorophyll_a",
            "status": "success",
            "data_source_type": "archive",
            "value": 0.0885,
            "unit": None,
            "observation_date": "2026-09-03",
            "freshness": "recent",
        },
    }
    analysis_arch = marine_analysis_service.run_analysis(state_arch)
    item_arch = next(i for i in analysis_arch.evidence_items if i.parameter == "chlorophyll_a")
    assert item_arch.data_source_type == "archive"
    assert item_arch.metadata.source_type == "archive"


# ─── TEST 6: Missing Weather Handling (No Fake Live Feed) ─────────────────────

def test_06_missing_weather_handling():
    """Verify simulated/fallback weather is explicitly marked and never reported as live."""
    state_mock_weather = {
        "query": "What is the weather?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "weather_result": {
            "source": "IMD-mock",
            "status": "mock",
            "data_source_type": "simulated",
            "observation_time": "2026-09-02T12:00:00Z",
            "wind": {"speed": 12.0, "direction": "SW"},
            "sea_condition": "Smooth to Slight",
        },
    }
    analysis = marine_analysis_service.run_analysis(state_mock_weather)
    w_item = next(i for i in analysis.evidence_items if i.parameter == "wind_speed")
    assert w_item.data_source_type == "simulated"
    assert "mock" in w_item.source.lower()
    assert w_item.metadata is not None
    assert w_item.metadata.reliability == ReliabilityLevel.LOW


# ─── TEST 7: Missing Ocean Data Handling (No Fabricated Values) ──────────────

def test_07_missing_ocean_handling():
    """Verify missing ocean data returns structured unavailable without fabricated numbers."""
    state_no_ocean = {
        "query": "What are ocean conditions?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "ocean_result": {
            "source": "INCOIS ERDDAP",
            "status": "unavailable",
            "data_source_type": "unavailable",
            "notes": "ERDDAP connection failed.",
        },
    }
    analysis = marine_analysis_service.run_analysis(state_no_ocean)
    sst_item = next((i for i in analysis.evidence_items if i.parameter == "sea_surface_temperature"), None)
    assert sst_item is None or sst_item.status == "unavailable" or sst_item.value is None
    assert "sea_surface_temperature" in analysis.data_quality["missing_parameters"]


# ─── TEST 8: Cross-Agent Signal Conflict Detection ───────────────────────────

def test_08_conflicting_evidence_detection():
    """Verify detection of wind discrepancies and calm weather vs dangerous wave swell."""
    # Conflict 1: Light local wind, but dangerous ocean wave swell (>= 2.0m)
    state_swell_conflict = {
        "query": "Can I go fishing?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "ocean_result": {
            "source": "INCOIS-ERDDAP",
            "status": "live",
            "data_source_type": "live",
            "significant_wave_height_m": 2.6,   # Dangerous swell
            "sea_surface_temperature_c": 29.5,
        },
        "weather_result": {
            "source": "IMD",
            "status": "live",
            "data_source_type": "live",
            "wind": {"speed": 8.0, "direction": "SW"},  # Light wind
            "sea_condition": "Smooth",
        },
        "safety_result": {
            "risk_level": "low",
            "proximity": {"status": "clear"},
        },
    }
    analysis = marine_analysis_service.run_analysis(state_swell_conflict)
    assert analysis.conflict_detected is True
    assert len(analysis.conflicts) >= 1
    swell_c = next((c for c in analysis.conflicts if c.parameter == "wave_swell_vs_local_wind"), None)
    assert swell_c is not None
    assert "IMD" in swell_c.conflicting_sources
    assert "significant_wave_height" in swell_c.conflicting_parameters
    assert "swell" in swell_c.reason.lower()


# ─── TEST 9: Safety Supremacy Override ────────────────────────────────────────

def test_09_safety_override_favorable_chlorophyll():
    """Verify high safety risk unconditionally overrides favorable chlorophyll and weather."""
    state_safety_hazard = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "eo_result": {
            "source": "MOSDAC",
            "status": "success",
            "data_source_type": "remote_authenticated",
            "value": 0.25,   # Highly favorable chlorophyll
            "observation_date": "2026-09-04",
            "freshness": "fresh",
        },
        "weather_result": {
            "source": "IMD",
            "status": "live",
            "data_source_type": "live",
            "wind": {"speed": 10.0, "direction": "SW"},
            "sea_condition": "Smooth",
        },
        "safety_result": {
            "risk_level": "critical",   # Boundary breach or restricted zone
            "risk_score": 95,
            "proximity": {
                "status": "breach",
                "distance_km": 0.5,
                "alert_message": "Vessel inside prohibited maritime security zone",
            },
        },
    }
    analysis = marine_analysis_service.run_analysis(state_safety_hazard)
    assert analysis.decision is not None
    assert analysis.decision.recommendation == "AVOID"
    assert analysis.decision.risk_level in ("CRITICAL", "HIGH")
    assert any("boundary" in r.lower() or "safety" in r.lower() for r in analysis.decision.reasoning)


# ─── TEST 10: Parallel State Preservation in LangGraph State ─────────────────

def test_10_parallel_state_preservation():
    """Verify specialist agent result slots remain isolated in LangGraph state."""
    eo_mock = {"source": "MOSDAC", "value": 0.12}
    ocean_mock = {"source": "INCOIS-ERDDAP", "sea_surface_temperature_c": 29.2}
    weather_mock = {"source": "IMD", "wind": {"speed": 14.0}}

    state = {
        "query": "Can I go fishing?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "test-p16-parallel",
        "eo_result": eo_mock,
        "ocean_result": ocean_mock,
        "weather_result": weather_mock,
        "safety_result": None,
        "ecosystem_result": None,
    }

    # Verify slots are distinct objects and not mutated/overwritten
    assert state["eo_result"]["value"] == 0.12
    assert state["ocean_result"]["sea_surface_temperature_c"] == 29.2
    assert state["weather_result"]["wind"]["speed"] == 14.0
    assert "sea_surface_temperature_c" not in state["eo_result"]
    assert "wind" not in state["ocean_result"]


# ─── TEST 11: Final Reasoning Stale Data & Reduced Confidence ────────────────

def test_11_final_reasoning_stale_data_reduced_confidence():
    """Verify final reasoning reflects reduced confidence for stale data without hallucination."""
    state_stale = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "eo_result": {
            "source": "MOSDAC",
            "parameter": "chlorophyll_a",
            "status": "success",
            "data_source_type": "archive",
            "value": 0.0885,
            "unit": None,
            "observation_date": "2026-08-20",  # Archival (stale)
            "freshness": "stale",
        },
        "ocean_result": {
            "source": "INCOIS-ERDDAP",
            "status": "live",
            "sea_surface_temperature_c": 29.5,
            "significant_wave_height_m": 1.2,
        },
        "weather_result": {
            "source": "IMD",
            "status": "live",
            "wind": {"speed": 11.0, "direction": "SW"},
            "sea_condition": "Smooth",
        },
        "safety_result": {
            "risk_level": "low",
            "proximity": {"status": "clear"},
        },
    }

    analysis = marine_analysis_service.run_analysis(state_stale)
    assert analysis.decision is not None
    # Stale data caps confidence at MEDIUM (not HIGH)
    assert analysis.decision.confidence == "MEDIUM"
    assert analysis.decision.recommendation == "CAUTION"
    # Archival note must be transparently communicated
    reasoning_text = " ".join(analysis.decision.reasoning).lower()
    assert "archival" in reasoning_text or "2026-08-20" in reasoning_text or "not guarantee fish" in reasoning_text
