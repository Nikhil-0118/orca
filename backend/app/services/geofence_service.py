"""
ORCA Offline Geofence & Maritime Boundary Safety Service (Phase 7).

Pure local, deterministic maritime boundary proximity evaluation and safety
state machine. Operates with ZERO network dependencies, ZERO LLM calls, and
executes completely offline.

Boundary Data:
  Loads sample geometries from `app/data/imbl_boundary_sample.geojson`.
  Explicitly marked: DEMO ONLY / APPROXIMATE / NOT FOR NAVIGATION.

Safety States:
  - NORMAL:      Distance > 15.0 km
  - APPROACHING: Distance <= 15.0 km
  - WARNING:     Distance <= 5.0 km
  - BREACH:      Distance <= 0.0 km (crossed boundary or inside restricted buffer)

Anti-Flapping Hysteresis:
  When recovering from a higher-severity state to a lower-severity state,
  a +1.0 km recovery margin is required (+0.5 km for breach recovery) to
  prevent alert oscillation near boundaries.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("orca.services.geofence")

_GEOJSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "imbl_boundary_sample.geojson"
)

# ── Maritime Safety Thresholds in Kilometers ──────────────────────────────
THRESHOLD_APPROACHING_KM: float = 15.0
THRESHOLD_WARNING_KM: float = 5.0
THRESHOLD_BREACH_KM: float = 0.0

# Hysteresis buffer gaps to prevent state flapping
HYSTERESIS_NORMAL_RECOVERY_KM: float = 1.0   # Must reach > 16.0 km to return to NORMAL from APPROACHING
HYSTERESIS_APPROACHING_RECOVERY_KM: float = 1.0 # Must reach > 6.0 km to return to APPROACHING from WARNING
HYSTERESIS_WARNING_RECOVERY_KM: float = 0.5    # Must reach > 0.5 km to return to WARNING from BREACH

DEMO_DISCLAIMER_WARNING: str = (
    "DEMO ONLY / APPROXIMATE / NOT FOR NAVIGATION — "
    "Coordinates in this dataset are sample approximations for demonstration purposes only "
    "and must never be used for actual maritime navigation, piloting, or legal boundary verification."
)


class SafetyState(str, Enum):
    NORMAL = "NORMAL"
    APPROACHING = "APPROACHING"
    WARNING = "WARNING"
    BREACH = "BREACH"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    CAUTION = "CAUTION"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class GeofenceEvaluation:
    latitude: float
    longitude: float
    nearest_boundary_name: str
    nearest_boundary_id: str
    distance_to_boundary_km: float
    bearing_degrees: float
    state: SafetyState
    severity: AlertSeverity
    alert_required: bool
    alert_title: str
    alert_message: str
    demo_only: bool = True
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    warning: str = DEMO_DISCLAIMER_WARNING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "nearest_boundary_name": self.nearest_boundary_name,
            "nearest_boundary_id": self.nearest_boundary_id,
            "distance_to_boundary_km": self.distance_to_boundary_km,
            "bearing_degrees": self.bearing_degrees,
            "state": self.state.value,
            "severity": self.severity.value,
            "alert_required": self.alert_required,
            "alert_title": self.alert_title,
            "alert_message": self.alert_message,
            "demo_only": self.demo_only,
            "evaluated_at": self.evaluated_at,
            "warning": self.warning,
        }


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance between two coordinates in kilometers."""
    r = 6371.0  # Earth mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def point_to_segment_distance_km(
    plat: float, plon: float, lat1: float, lon1: float, lat2: float, lon2: float
) -> Tuple[float, float, float]:
    """
    Calculate shortest distance from a point to a line segment in kilometers.
    Returns (distance_km, proj_lat, proj_lon).
    """
    dx = lon2 - lon1
    dy = lat2 - lat1

    if dx == 0.0 and dy == 0.0:
        dist = haversine_distance_km(plat, plon, lat1, lon1)
        return dist, lat1, lon1

    t = ((plon - lon1) * dx + (plat - lat1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    proj_lon = lon1 + t * dx
    proj_lat = lat1 + t * dy
    dist = haversine_distance_km(plat, plon, proj_lat, proj_lon)
    return dist, proj_lat, proj_lon


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate compass bearing (0-360 degrees) from point 1 to point 2."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return round((bearing + 360.0) % 360.0, 1)


class GeofenceService:
    """
    Local Geofencing & Safety State Engine.
    Evaluates vessel proximity to maritime boundary line strings and maintains state with hysteresis.
    """

    def __init__(self, geojson_path: str = _GEOJSON_PATH):
        self.geojson_path = geojson_path
        self._boundary_features: List[Dict[str, Any]] = []
        self.load_boundaries()

    def load_boundaries(self) -> None:
        """Load boundary line features from local GeoJSON."""
        if os.path.exists(self.geojson_path):
            try:
                with open(self.geojson_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._boundary_features = data.get("features", [])
                    logger.info("geofence_boundaries_loaded", extra={"count": len(self._boundary_features)})
            except Exception as exc:
                logger.warning("geofence_load_failed", extra={"error": str(exc)})
        else:
            logger.warning("geofence_file_missing", extra={"path": self.geojson_path})

    def find_nearest_boundary(
        self, lat: float, lon: float
    ) -> Tuple[float, float, str, str]:
        """
        Find minimum distance and bearing from (lat, lon) to any loaded boundary segment.
        Returns (min_distance_km, bearing_degrees, boundary_name, boundary_id).
        """
        if not self._boundary_features:
            self.load_boundaries()

        min_distance = float("inf")
        closest_bearing = 0.0
        closest_name = "Demo Maritime Boundary"
        closest_id = "IMBL_DEMO_SAMPLE"

        for feature in self._boundary_features:
            props = feature.get("properties") or {}
            geom = feature.get("geometry") or {}
            coords = geom.get("coordinates") or []
            geom_type = geom.get("type", "")

            lines: List[List[List[float]]] = []
            if geom_type == "LineString":
                lines = [coords]
            elif geom_type == "MultiLineString":
                lines = coords

            for line in lines:
                if len(line) < 2:
                    continue
                for i in range(len(line) - 1):
                    lon1, lat1 = line[i][:2]
                    lon2, lat2 = line[i + 1][:2]
                    dist, proj_lat, proj_lon = point_to_segment_distance_km(lat, lon, lat1, lon1, lat2, lon2)
                    if dist < min_distance:
                        min_distance = dist
                        closest_bearing = calculate_bearing(lat, lon, proj_lat, proj_lon)
                        closest_name = props.get("name", closest_name)
                        closest_id = props.get("id", closest_id)

        if min_distance == float("inf"):
            min_distance = 45.0
            closest_bearing = 90.0

        return round(min_distance, 3), closest_bearing, closest_name, closest_id

    def transition_state_with_hysteresis(
        self, distance_km: float, prev_state: Optional[SafetyState] = None
    ) -> SafetyState:
        """
        Evaluate next SafetyState from distance with anti-flapping hysteresis gaps.
        """
        if prev_state is None:
            # Cold start without prior state
            if distance_km <= THRESHOLD_BREACH_KM:
                return SafetyState.BREACH
            if distance_km <= THRESHOLD_WARNING_KM:
                return SafetyState.WARNING
            if distance_km <= THRESHOLD_APPROACHING_KM:
                return SafetyState.APPROACHING
            return SafetyState.NORMAL

        # Hysteresis state machine
        if prev_state == SafetyState.BREACH:
            # Must clear breach threshold + buffer to return to WARNING
            if distance_km > (THRESHOLD_BREACH_KM + HYSTERESIS_WARNING_RECOVERY_KM):
                if distance_km > (THRESHOLD_WARNING_KM + HYSTERESIS_APPROACHING_RECOVERY_KM):
                    if distance_km > (THRESHOLD_APPROACHING_KM + HYSTERESIS_NORMAL_RECOVERY_KM):
                        return SafetyState.NORMAL
                    return SafetyState.APPROACHING
                return SafetyState.WARNING
            return SafetyState.BREACH

        if prev_state == SafetyState.WARNING:
            if distance_km <= THRESHOLD_BREACH_KM:
                return SafetyState.BREACH
            # Must clear warning threshold + buffer to return to APPROACHING
            if distance_km > (THRESHOLD_WARNING_KM + HYSTERESIS_APPROACHING_RECOVERY_KM):
                if distance_km > (THRESHOLD_APPROACHING_KM + HYSTERESIS_NORMAL_RECOVERY_KM):
                    return SafetyState.NORMAL
                return SafetyState.APPROACHING
            return SafetyState.WARNING

        if prev_state == SafetyState.APPROACHING:
            if distance_km <= THRESHOLD_BREACH_KM:
                return SafetyState.BREACH
            if distance_km <= THRESHOLD_WARNING_KM:
                return SafetyState.WARNING
            # Must clear approaching threshold + buffer to return to NORMAL
            if distance_km > (THRESHOLD_APPROACHING_KM + HYSTERESIS_NORMAL_RECOVERY_KM):
                return SafetyState.NORMAL
            return SafetyState.APPROACHING

        # prev_state == SafetyState.NORMAL
        if distance_km <= THRESHOLD_BREACH_KM:
            return SafetyState.BREACH
        if distance_km <= THRESHOLD_WARNING_KM:
            return SafetyState.WARNING
        if distance_km <= THRESHOLD_APPROACHING_KM:
            return SafetyState.APPROACHING
        return SafetyState.NORMAL

    def generate_alert(
        self, state: SafetyState, distance_km: float, boundary_name: str
    ) -> Tuple[AlertSeverity, bool, str, str]:
        """
        Generate deterministic alert title, message, and severity based on SafetyState.
        """
        if state == SafetyState.BREACH:
            return (
                AlertSeverity.CRITICAL,
                True,
                "CRITICAL: Maritime Boundary Breach Detected",
                f"Vessel has crossed {boundary_name}. Return to Indian territorial waters immediately! Offline safety monitoring active.",
            )
        if state == SafetyState.WARNING:
            return (
                AlertSeverity.WARNING,
                True,
                "WARNING: Immediate Border Proximity",
                f"Vessel is {distance_km:.2f} km from {boundary_name}. Immediate course correction recommended.",
            )
        if state == SafetyState.APPROACHING:
            return (
                AlertSeverity.CAUTION,
                True,
                "CAUTION: Approaching Border Buffer",
                f"Vessel is approaching {boundary_name} ({distance_km:.2f} km). Monitor heading and radar watch.",
            )
        # NORMAL
        return (
            AlertSeverity.INFO,
            False,
            "NORMAL: Sector Safe",
            f"Vessel is {distance_km:.2f} km clear of {boundary_name}. Conditions nominal.",
        )

    def evaluate_position(
        self, lat: float, lon: float, prev_state: Optional[SafetyState] = None
    ) -> GeofenceEvaluation:
        """
        Execute full local geofencing evaluation:
        1. Find minimum distance & bearing to demo boundary.
        2. Evaluate state transitions with hysteresis.
        3. Formulate deterministic local alerts.
        """
        dist_km, bearing, b_name, b_id = self.find_nearest_boundary(lat, lon)
        state = self.transition_state_with_hysteresis(dist_km, prev_state)
        severity, alert_req, title, msg = self.generate_alert(state, dist_km, b_name)

        return GeofenceEvaluation(
            latitude=lat,
            longitude=lon,
            nearest_boundary_name=b_name,
            nearest_boundary_id=b_id,
            distance_to_boundary_km=dist_km,
            bearing_degrees=bearing,
            state=state,
            severity=severity,
            alert_required=alert_req,
            alert_title=title,
            alert_message=msg,
        )


# Global singleton instance for local imports
geofence_service = GeofenceService()
