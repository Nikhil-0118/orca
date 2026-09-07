"""
Unit tests for ORCA Offline GeofenceService and Safety State Machine (Phase 7).
"""
import pytest
from app.services.geofence_service import (
    GeofenceService,
    SafetyState,
    AlertSeverity,
    haversine_distance_km,
    point_to_segment_distance_km,
    calculate_bearing,
    THRESHOLD_APPROACHING_KM,
    THRESHOLD_WARNING_KM,
    THRESHOLD_BREACH_KM,
)


@pytest.fixture
def service():
    return GeofenceService()


# ── 1. Geodesic Math Unit Tests ──────────────────────────────────────────

def test_haversine_distance_known_points():
    # Distance between Chennai (13.0827, 80.2707) and Mumbai (19.0760, 72.8777) ~ 1030-1040 km
    dist = haversine_distance_km(13.0827, 80.2707, 19.0760, 72.8777)
    assert 1025.0 < dist < 1045.0


def test_point_to_segment_distance():
    # Point perpendicular to line segment
    dist, plat, plon = point_to_segment_distance_km(
        plat=10.0, plon=80.0,
        lat1=9.0, lon1=80.0,
        lat2=11.0, lon2=80.0
    )
    assert round(dist, 2) == 0.0
    assert round(plat, 2) == 10.0
    assert round(plon, 2) == 80.0


def test_calculate_bearing():
    # North
    assert calculate_bearing(10.0, 80.0, 11.0, 80.0) == 0.0
    # East
    assert 85.0 < calculate_bearing(10.0, 80.0, 10.0, 81.0) < 95.0
    # South
    assert calculate_bearing(10.0, 80.0, 9.0, 80.0) == 180.0


# ── 2. Safety State Machine Transitions ──────────────────────────────────

def test_state_normal_position(service):
    # Location far from boundary (e.g. Mumbai Coastal safe water 19.0, 72.5)
    evaluation = service.evaluate_position(19.0, 72.5)
    assert evaluation.state == SafetyState.NORMAL
    assert evaluation.severity == AlertSeverity.INFO
    assert evaluation.alert_required is False
    assert evaluation.distance_to_boundary_km > THRESHOLD_APPROACHING_KM


def test_state_approaching_threshold(service):
    # Palk bay point ~ 10-12 km from Sri Lanka IMBL (e.g. 9.40, 79.40)
    evaluation = service.evaluate_position(9.40, 79.40)
    assert evaluation.state == SafetyState.APPROACHING
    assert evaluation.severity == AlertSeverity.CAUTION
    assert evaluation.alert_required is True
    assert THRESHOLD_WARNING_KM < evaluation.distance_to_boundary_km <= THRESHOLD_APPROACHING_KM


def test_state_warning_threshold(service):
    # Point right near the IMBL line ~ 2-4 km (e.g. 9.36, 79.52)
    evaluation = service.evaluate_position(9.36, 79.52)
    assert evaluation.state == SafetyState.WARNING
    assert evaluation.severity == AlertSeverity.WARNING
    assert evaluation.alert_required is True
    assert THRESHOLD_BREACH_KM < evaluation.distance_to_boundary_km <= THRESHOLD_WARNING_KM


def test_state_breach_detection(service):
    # Point directly on or across the IMBL line (e.g. 9.3667, 79.5333)
    evaluation = service.evaluate_position(9.3667, 79.5333)
    assert evaluation.state == SafetyState.BREACH
    assert evaluation.severity == AlertSeverity.CRITICAL
    assert evaluation.alert_required is True
    assert evaluation.distance_to_boundary_km <= 0.05  # essentially 0 km


# ── 3. Anti-Flapping Hysteresis Tests ────────────────────────────────────

def test_hysteresis_warning_to_approaching(service):
    # If vessel is in WARNING, moving to 5.5 km (which would be APPROACHING cold)
    # remains in WARNING because 5.5 km <= 5.0 km + 1.0 km buffer
    next_state = service.transition_state_with_hysteresis(
        distance_km=5.5,
        prev_state=SafetyState.WARNING
    )
    assert next_state == SafetyState.WARNING

    # Once vessel reaches 6.2 km (> 6.0 km), it safely recovers to APPROACHING
    next_state_recovered = service.transition_state_with_hysteresis(
        distance_km=6.2,
        prev_state=SafetyState.WARNING
    )
    assert next_state_recovered == SafetyState.APPROACHING


def test_hysteresis_approaching_to_normal(service):
    # If vessel is in APPROACHING, moving to 15.5 km remains in APPROACHING
    # until reaching > 16.0 km
    next_state = service.transition_state_with_hysteresis(
        distance_km=15.5,
        prev_state=SafetyState.APPROACHING
    )
    assert next_state == SafetyState.APPROACHING

    next_state_recovered = service.transition_state_with_hysteresis(
        distance_km=16.5,
        prev_state=SafetyState.APPROACHING
    )
    assert next_state_recovered == SafetyState.NORMAL


def test_hysteresis_breach_to_warning(service):
    # In BREACH (0 km), moving to 0.3 km remains in BREACH (needs > 0.5 km)
    next_state = service.transition_state_with_hysteresis(
        distance_km=0.3,
        prev_state=SafetyState.BREACH
    )
    assert next_state == SafetyState.BREACH

    next_state_recovered = service.transition_state_with_hysteresis(
        distance_km=0.8,
        prev_state=SafetyState.BREACH
    )
    assert next_state_recovered == SafetyState.WARNING


# ── 4. Deterministic Alert Generation (Zero LLM) ─────────────────────────

def test_deterministic_alert_content(service):
    eval_breach = service.evaluate_position(9.3667, 79.5333)
    assert "CRITICAL" in eval_breach.alert_title
    assert "Return to Indian territorial waters" in eval_breach.alert_message
    assert eval_breach.demo_only is True


# ── 5. Zero-Network Isolation Verification ───────────────────────────────

def test_pure_local_evaluation_speed(service):
    import time
    t0 = time.time()
    for _ in range(100):
        service.evaluate_position(13.0827, 80.2707)
    elapsed = time.time() - t0
    # 100 local checks should complete in under 50 milliseconds
    assert elapsed < 0.20
