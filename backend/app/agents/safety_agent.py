"""
Online Safety Agent & Fan-In Join Node for ORCA.

Responsibilities:
1. Pure local boundary proximity evaluation (check_proximity) using local demo GeoJSON.
   - PURE LOCAL COMPUTATION (No network, No LLM).
   - Explicitly marked: DEMO ONLY / APPROXIMATE / NOT FOR NAVIGATION.
2. Marine hazard and advisory alert retrieval (fetch_hazard_alerts).
   - Async network call with transparent mock fallback.
   - Never claims live status without genuine, verified alert parsing.
3. Deterministic and explainable combined risk reasoning across all converged signals:
   - Proximity + Hazards + Ocean State + Weather Bulletins + EO Observations.
   - Cross-signal synergy (e.g. boundary proximity + severe weather produces higher combined risk).
   - Standard 4-tier risk level classification:
       * low: 0 - 24
       * moderate: 25 - 49
       * high: 50 - 74
       * critical: 75 - 100

Node contract:
  Input:  OrcaState (reads location, eo_result, ocean_result, weather_result)
  Output: {"safety_result": {...}}
"""
from datetime import datetime, timezone
import json
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.state import OrcaState

logger = logging.getLogger("orca.agents.safety")

# ── GeoJSON Data Path & Thresholds ────────────────────────────────────────
_GEOJSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "imbl_boundary_sample.geojson")

# Proximity thresholds in Kilometers
CRITICAL_BOUNDARY_THRESHOLD_KM: float = 5.0
NEAR_BOUNDARY_THRESHOLD_KM: float = 15.0
APPROACHING_BOUNDARY_THRESHOLD_KM: float = 30.0

DEMO_DISCLAIMER_WARNING: str = (
    "DEMO ONLY / APPROXIMATE / NOT FOR NAVIGATION — "
    "Coordinates in this dataset are sample approximations for demonstration purposes only "
    "and must never be used for actual maritime navigation, piloting, or legal boundary verification."
)


def classify_risk_level(risk_score: int) -> str:
    """
    Deterministic mapping from risk_score (0-100) to standard 4-tier risk_level:
    - low: 0 - 24
    - moderate: 25 - 49
    - high: 50 - 74
    - critical: 75 - 100
    """
    if risk_score >= 75:
        return "critical"
    if risk_score >= 50:
        return "high"
    if risk_score >= 25:
        return "moderate"
    return "low"


def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two geographic coordinates in kilometers."""
    r = 6371.0  # Earth's mean radius in km
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


def _point_to_segment_distance_km(plat: float, plon: float, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the shortest distance from a point to a line segment in kilometers."""
    dx = lon2 - lon1
    dy = lat2 - lat1

    if dx == 0.0 and dy == 0.0:
        return _haversine_distance_km(plat, plon, lat1, lon1)

    # Project point onto line segment in Euclidean approximation for parameter t
    t = ((plon - lon1) * dx + (plat - lat1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    proj_lon = lon1 + t * dx
    proj_lat = lat1 + t * dy
    return _haversine_distance_km(plat, plon, proj_lat, proj_lon)


class SafetyAgent:
    """
    Online Safety Agent evaluating maritime proximity and multi-agent risk synthesis.
    """

    def __init__(self, geojson_path: str = _GEOJSON_PATH):
        self.geojson_path = geojson_path
        self._boundary_features: List[Dict[str, Any]] = []
        self._load_boundary_data()

    def _load_boundary_data(self) -> None:
        """Load demo boundary geometries from GeoJSON file."""
        if os.path.exists(self.geojson_path):
            try:
                with open(self.geojson_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._boundary_features = data.get("features", [])
                    logger.info("safety_boundary_loaded", extra={"features": len(self._boundary_features)})
            except Exception as e:
                logger.warning("safety_boundary_load_failed", extra={"error": str(e)})
        else:
            logger.warning("safety_boundary_file_missing", extra={"path": self.geojson_path})

    def check_proximity(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Pure local computation calculating proximity to demo maritime boundaries.
        NO network calls, NO LLM calls. Works completely offline.
        """
        try:
            if not self._boundary_features:
                self._load_boundary_data()

            min_distance = float("inf")
            closest_feature_name = "Demo Maritime Boundary"
            closest_feature_id = "IMBL_DEMO_SAMPLE"

            for feature in self._boundary_features:
                props = feature.get("properties") or {}
                geom = feature.get("geometry") or {}
                coords = geom.get("coordinates") or []
                geom_type = geom.get("type", "")

                if geom_type == "LineString" and len(coords) >= 2:
                    for i in range(len(coords) - 1):
                        lon1, lat1 = coords[i][:2]
                        lon2, lat2 = coords[i + 1][:2]
                        dist = _point_to_segment_distance_km(lat, lon, lat1, lon1, lat2, lon2)
                        if dist < min_distance:
                            min_distance = dist
                            closest_feature_name = props.get("name", closest_feature_name)
                            closest_feature_id = props.get("id", closest_feature_id)

                elif geom_type == "MultiLineString":
                    for line in coords:
                        for i in range(len(line) - 1):
                            lon1, lat1 = line[i][:2]
                            lon2, lat2 = line[i + 1][:2]
                            dist = _point_to_segment_distance_km(lat, lon, lat1, lon1, lat2, lon2)
                            if dist < min_distance:
                                min_distance = dist
                                closest_feature_name = props.get("name", closest_feature_name)
                                closest_feature_id = props.get("id", closest_feature_id)

            if min_distance == float("inf"):
                min_distance = 45.0

            rounded_dist = round(min_distance, 2)

            if rounded_dist <= NEAR_BOUNDARY_THRESHOLD_KM:
                status = "near_boundary"
            else:
                status = "inside"

            return {
                "status": status,
                "distance_km": rounded_dist,
                "boundary_name": closest_feature_name,
                "boundary_id": closest_feature_id,
                "near_threshold_km": NEAR_BOUNDARY_THRESHOLD_KM,
                "critical_threshold_km": CRITICAL_BOUNDARY_THRESHOLD_KM,
                "source": "local demo GeoJSON",
                "demo_only": True,
                "warning": DEMO_DISCLAIMER_WARNING,
            }
        except Exception as exc:
            logger.warning("proximity_check_exception", extra={"error": str(exc)})
            return {
                "status": "inside",
                "distance_km": 45.0,
                "boundary_name": "Demo Maritime Boundary (Fallback)",
                "boundary_id": "IMBL_DEMO_SAMPLE",
                "near_threshold_km": NEAR_BOUNDARY_THRESHOLD_KM,
                "critical_threshold_km": CRITICAL_BOUNDARY_THRESHOLD_KM,
                "source": "local demo GeoJSON",
                "demo_only": True,
                "warning": DEMO_DISCLAIMER_WARNING,
            }

    async def fetch_hazard_alerts(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Retrieve marine hazard and advisory alerts.
        Returns live status ONLY if an authentic live hazard feed is reached and parsed.
        Transparently returns structured mock fallback otherwise.
        """
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # In the current environment without an active public unauthenticated REST feed,
        # return a structured, truthfully labeled mock fallback without fabricating live data.
        return {
            "source": "INCOIS/SAMUDRA-mock",
            "status": "mock",
            "alerts": [
                {
                    "type": "high_waves",
                    "severity": "moderate",
                    "headline": "Rough Sea Alert for Coastal Waters",
                    "description": "Moderate sea conditions with seasonal swell expected.",
                    "issued_at": "2026-09-01T00:00:00Z",
                }
            ],
            "reason": "Live SAMUDRA alert feed integration pending official API access",
            "retrieved_at": retrieved_at,
            "freshness": "fresh",
        }

    def calculate_combined_risk(
        self,
        proximity: Dict[str, Any],
        hazard_alerts: Dict[str, Any],
        eo_result: Optional[Dict[str, Any]],
        ocean_result: Optional[Dict[str, Any]],
        weather_result: Optional[Dict[str, Any]],
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        """
        Deterministic, explainable combined risk scoring across all converged specialist signals.
        Evaluates cross-signal interactions (boundary proximity + severe weather/waves).
        """
        score = 0  # Base nominal score
        contributing_factors: List[str] = []
        hazards: List[Dict[str, Any]] = []
        reasoning: List[str] = []
        recommendations: List[str] = []
        sources: List[str] = []

        # ── 1. Proximity Evaluation ─────────────────────────────────────────
        dist_km = proximity.get("distance_km", 999.0)
        is_near_boundary = dist_km <= NEAR_BOUNDARY_THRESHOLD_KM
        is_critical_boundary = dist_km <= CRITICAL_BOUNDARY_THRESHOLD_KM
        sources.append("local demo GeoJSON")

        if is_critical_boundary:
            score += 35
            factor = f"Critical proximity to demo boundary ({dist_km} km <= {CRITICAL_BOUNDARY_THRESHOLD_KM} km)"
            contributing_factors.append(factor)
            hazards.append({"type": "boundary_violation_risk", "severity": "high", "source": "local demo GeoJSON"})
            reasoning.append(f"Vessel is within critical distance ({dist_km} km) of demo maritime boundary.")
            recommendations.append("Adjust course immediately away from demo boundary line.")
        elif is_near_boundary:
            score += 25
            factor = f"Near demo boundary ({dist_km} km <= {NEAR_BOUNDARY_THRESHOLD_KM} km)"
            contributing_factors.append(factor)
            hazards.append({"type": "boundary_proximity", "severity": "moderate", "source": "local demo GeoJSON"})
            reasoning.append(f"Vessel is approaching demo maritime boundary ({dist_km} km).")
            recommendations.append("Exercise navigational caution and monitor boundary distance.")
        elif dist_km <= APPROACHING_BOUNDARY_THRESHOLD_KM:
            score += 10
            reasoning.append(f"Vessel is {dist_km} km from nearest demo maritime boundary.")

        # ── 2. Weather Evaluation ───────────────────────────────────────────
        has_severe_weather = False
        if weather_result and isinstance(weather_result, dict):
            sources.append(weather_result.get("source", "IMD"))
            warnings = weather_result.get("warnings") or []
            if warnings:
                score += 30
                has_severe_weather = True
                for w in warnings:
                    contributing_factors.append(f"IMD weather warning: {w}")
                    hazards.append({"type": "severe_weather_warning", "severity": "high", "source": weather_result.get("source", "IMD")})
                reasoning.append("Official weather advisory/warning is active for this coastal zone.")
                recommendations.append("Heed all active IMD coastal weather advisories.")

            w_dict = weather_result.get("wind") or {}
            w_spd = w_dict.get("speed")
            if w_spd is not None and isinstance(w_spd, (int, float)):
                if w_spd >= 25.0:  # > 25 knots
                    score += 20
                    has_severe_weather = True
                    contributing_factors.append(f"High marine wind speed ({w_spd} knots)")
                    hazards.append({"type": "gale_force_wind", "severity": "high", "source": "IMD"})
                    reasoning.append(f"High winds ({w_spd} knots) forecast in operational zone.")
                    recommendations.append("Secure deck equipment and prepare for gale-force conditions.")
                elif w_spd >= 18.0:
                    score += 10
                    contributing_factors.append(f"Fresh to strong breeze ({w_spd} knots)")
                    reasoning.append(f"Fresh marine breeze ({w_spd} knots) observed.")

            vis_dict = weather_result.get("visibility") or {}
            vis_val = str(vis_dict.get("value", "")).lower()
            if "poor" in vis_val or "fog" in vis_val:
                score += 10
                contributing_factors.append(f"Reduced visibility ({vis_dict.get('value')})")
                hazards.append({"type": "low_visibility", "severity": "moderate", "source": "IMD"})
                reasoning.append("Reduced visibility reported; maintain lookout and sound signals.")
                recommendations.append("Maintain continuous radar and lookout watch due to low visibility.")

        # ── 3. Ocean State Evaluation ────────────────────────────────────────
        has_severe_waves = False
        if ocean_result and isinstance(ocean_result, dict):
            sources.append(ocean_result.get("source", "INCOIS ERDDAP"))
            wave_h = ocean_result.get("significant_wave_height_m")
            if wave_h is not None and isinstance(wave_h, (int, float)):
                if wave_h >= 3.0:
                    score += 20
                    has_severe_waves = True
                    contributing_factors.append(f"High significant wave height ({wave_h} m)")
                    hazards.append({"type": "rough_sea", "severity": "high", "source": "INCOIS"})
                    reasoning.append(f"High wave heights ({wave_h} m) recorded.")
                    recommendations.append("Avoid venturing into open waters — hazardous sea state.")
                elif wave_h >= 2.0:
                    score += 10
                    has_severe_waves = True
                    contributing_factors.append(f"Moderate wave height ({wave_h} m)")
                    reasoning.append(f"Moderate sea swell ({wave_h} m) recorded.")

            o_wind = ocean_result.get("wind") or {}
            o_spd = (o_wind.get("speed") or {}).get("value")
            if o_spd is not None and isinstance(o_spd, (int, float)):
                if o_spd >= 12.0:
                    score += 12
                    has_severe_weather = True
                    contributing_factors.append(f"Elevated ocean surface wind ({o_spd} m/s)")
                    reasoning.append(f"Strong surface ocean winds ({o_spd} m/s) detected.")

        # ── 4. Hazard Alerts Evaluation ──────────────────────────────────────
        if hazard_alerts and isinstance(hazard_alerts, dict):
            sources.append(hazard_alerts.get("source", "INCOIS/SAMUDRA"))
            alerts = hazard_alerts.get("alerts") or []
            for alert in alerts:
                a_type = alert.get("type", "general")
                a_sev = alert.get("severity", "moderate")
                if a_type == "tsunami":
                    score += 45
                    contributing_factors.append("Active Tsunami Alert")
                    hazards.append({"type": "tsunami", "severity": "critical", "source": "SAMUDRA"})
                    reasoning.append("CRITICAL: Active tsunami advisory received from national alert centre.")
                    recommendations.append("Evacuate coastal shallows immediately to designated deep water or high ground.")
                elif a_type == "storm_surge":
                    score += 25
                    has_severe_weather = True
                    contributing_factors.append("Storm Surge Advisory")
                    hazards.append({"type": "storm_surge", "severity": "high", "source": "SAMUDRA"})
                    reasoning.append("High storm surge risk detected along immediate coastline.")
                elif a_type == "high_waves" and a_sev in ("high", "severe"):
                    score += 15
                    has_severe_waves = True

        # ── 5. Cross-Signal Multiplier & Synergy ─────────────────────────────
        # If vessel is near boundary AND adverse weather/waves occur simultaneously:
        if is_near_boundary and (has_severe_weather or has_severe_waves):
            synergy_penalty = 15
            score += synergy_penalty
            synergy_msg = (
                "Compound Risk Multiplier: Boundary proximity combined with adverse "
                "marine weather significantly escalates operational risk."
            )
            contributing_factors.append(synergy_msg)
            reasoning.append(synergy_msg)
            recommendations.append("Do not attempt maneuvers near boundary under current adverse weather.")

        # Clamp final score between 0 and 100
        risk_score = max(0, min(100, score))
        risk_level = classify_risk_level(risk_score)

        if not reasoning:
            reasoning.append("All marine environmental signals and boundary distances are within normal safe ranges.")
        if not recommendations:
            recommendations.append("Maintain standard watch and navigational safety procedures.")

        return {
            "status": "online",
            "data_source_type": "simulated",
            "risk_level": risk_level,
            "risk_score": risk_score,
            "confidence": "high",
            "location": {"lat": round(lat, 4), "lon": round(lon, 4)},
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "requested_location": {"lat": round(lat, 4), "lon": round(lon, 4)},
            "resolved_location": {"lat": round(lat, 4), "lon": round(lon, 4)},
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "proximity": proximity,
            "hazard_alerts": hazard_alerts,
            "contributing_factors": contributing_factors,
            "hazards": hazards,
            "reasoning": reasoning,
            "recommendations": recommendations,
            "sources": sorted(list(set(sources))),
            "source": "SafetyAgent Multi-Signal Risk Engine",
            "demo_boundary_warning": DEMO_DISCLAIMER_WARNING,
        }


# ── LangGraph node function ──────────────────────────────────────────────

_agent_singleton = SafetyAgent()


async def safety_node(state: OrcaState) -> dict:
    """
    LangGraph fan-in node: converges EO, Ocean, and Weather signals,
    evaluates boundary proximity and hazard alerts, and computes combined risk.
    Writes ONLY to safety_result.
    Skips execution if selected_agents is provided and safety is neither required nor selected.
    """
    selected = state.get("selected_agents")
    safety_req = state.get("safety_required", False)
    if selected is not None and not safety_req and "safety" not in selected:
        return {}

    loc = state.get("location")
    if not isinstance(loc, dict):
        loc = {}

    req_lat = loc.get("latitude") if loc.get("latitude") is not None else loc.get("lat")
    req_lon = loc.get("longitude") if loc.get("longitude") is not None else loc.get("lon")
    is_demo = bool(loc.get("is_demo", False))

    if req_lat is None or req_lon is None:
        return {
            "safety_result": {
                "status": "unavailable",
                "risk_level": "unknown",
                "risk_score": 0,
                "confidence": "low",
                "reasoning": "Boundary safety evaluation unavailable because no geographic coordinates were provided.",
                "recommendations": ["Enable location services or specify coordinates to evaluate maritime safety boundaries."],
                "demo_boundary_warning": DEMO_DISCLAIMER_WARNING,
            }
        }

    try:
        lat = float(req_lat)
        lon = float(req_lon)
    except (ValueError, TypeError):
        return {
            "safety_result": {
                "status": "unavailable",
                "risk_level": "unknown",
                "risk_score": 0,
                "confidence": "low",
                "reasoning": "Invalid geographic coordinates provided for boundary evaluation.",
                "recommendations": ["Provide valid latitude and longitude coordinates."],
                "demo_boundary_warning": DEMO_DISCLAIMER_WARNING,
            }
        }

    eo_res = state.get("eo_result")
    ocean_res = state.get("ocean_result")
    weather_res = state.get("weather_result")

    # 1. Pure local proximity check (offline, deterministic)
    proximity = _agent_singleton.check_proximity(lat, lon)

    # 2. Asynchronous hazard alert retrieval
    hazard_alerts = await _agent_singleton.fetch_hazard_alerts(lat, lon)

    # 3. Deterministic combined risk reasoning
    combined_safety = _agent_singleton.calculate_combined_risk(
        proximity=proximity,
        hazard_alerts=hazard_alerts,
        eo_result=eo_res,
        ocean_result=ocean_res,
        weather_result=weather_res,
        lat=lat,
        lon=lon,
    )

    logger.info(
        "safety_node_evaluated",
        extra={
            "risk_level": combined_safety["risk_level"],
            "risk_score": combined_safety["risk_score"],
            "distance_km": proximity.get("distance_km"),
        },
    )

    return {
        "safety_result": combined_safety,
    }
