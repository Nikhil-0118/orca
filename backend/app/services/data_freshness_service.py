"""
Data Freshness and Source Reliability Service (Phase 16).

Centralized evaluator for:
1. Physical observation time vs. system retrieval time.
2. Parameter-aware freshness thresholds (Weather vs. SST vs. Chlorophyll vs. Geofence).
3. Deterministic source reliability scoring without arbitrary AI weights.
4. Production of standardized EvidenceMetadata objects.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple

from app.schemas.evidence import (
    EvidenceMetadata,
    FreshnessLevel,
    ObservationStatus,
    ReliabilityLevel,
)

logger = logging.getLogger("orca.data_freshness_service")

# ─────────────────────────────────────────────────────────────────────────────
# Parameter-Aware Freshness Thresholds (Hours)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_THRESHOLDS: Dict[str, Dict[str, float]] = {
    # Weather: Highly dynamic atmospheric conditions (IMD bulletin cycle is 3-6h)
    "weather": {
        "fresh_hours": 3.0,
        "recent_hours": 12.0,
        "stale_hours": 24.0,
    },
    # Ocean / SST: Sea surface temperature and wave spectra (update every 6-12h)
    "ocean": {
        "fresh_hours": 12.0,
        "recent_hours": 24.0,
        "stale_hours": 48.0,
    },
    # Chlorophyll: Satellite Level-4 multi-orbit daily composite (aggregation latency 24-72h)
    "chlorophyll": {
        "fresh_hours": 24.0,
        "recent_hours": 72.0,
        "stale_hours": 168.0,  # 7 days
    },
    # Geofence / Maritime Boundaries: Administrative/regulatory definitions (valid long term)
    "geofence": {
        "fresh_hours": 720.0,   # 30 days
        "recent_hours": 2160.0, # 90 days
        "stale_hours": 8760.0,  # 365 days
    },
    # Default fallback
    "default": {
        "fresh_hours": 24.0,
        "recent_hours": 48.0,
        "stale_hours": 168.0,
    },
}

PARAMETER_CATEGORY_MAP: Dict[str, str] = {
    # Weather parameters
    "wind_speed": "weather",
    "wind_direction": "weather",
    "weather_bulletin": "weather",
    "visibility": "weather",
    "sea_condition": "weather",
    "air_temperature": "weather",
    "precipitation": "weather",
    "rainfall": "weather",
    "humidity": "weather",
    "atmospheric_pressure": "weather",

    # Ocean / SST / Wave parameters
    "sea_surface_temperature": "ocean",
    "sst": "ocean",
    "significant_wave_height": "ocean",
    "wave_height": "ocean",
    "wave_period": "ocean",
    "wave_direction": "ocean",
    "ocean_surface_wind_speed": "ocean",
    "ocean_surface_wind_direction": "ocean",
    "current_speed": "ocean",
    "current_direction": "ocean",

    # Chlorophyll / Satellite EO Level-4 parameters
    "chlorophyll_a": "chlorophyll",
    "chla": "chlorophyll",
    "chlorophyll": "chlorophyll",
    "cloud_cover": "chlorophyll",

    # Geofence / Safety parameters
    "boundary_proximity": "geofence",
    "safety_hazard": "geofence",
    "geofence": "geofence",
    "security_zone": "geofence",
}


def parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse various timestamp representations into a UTC datetime object."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(ts, str):
        s = ts.strip()
        if not s or s.lower() in ["none", "null", "unknown", "n/a", ""]:
            return None
        # 1. ISO format (with Z or offset)
        try:
            clean_s = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
        # 2. Standard date formats
        for fmt in [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%Y%m%d",
        ]:
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                continue
    return None


def get_parameter_category(parameter: str) -> str:
    """Map observed parameter name to its freshness category."""
    p_norm = (parameter or "").lower().strip()
    if p_norm in PARAMETER_CATEGORY_MAP:
        return PARAMETER_CATEGORY_MAP[p_norm]
    if any(k in p_norm for k in ["wind", "weather", "rain", "visibility", "temp"]):
        if "sea" in p_norm or "surface" in p_norm:
            return "ocean"
        return "weather"
    if any(k in p_norm for k in ["sst", "wave", "swell", "current"]):
        return "ocean"
    if any(k in p_norm for k in ["chlorophyll", "chla", "ocm", "satellite"]):
        return "chlorophyll"
    if any(k in p_norm for k in ["boundary", "geofence", "hazard"]):
        return "geofence"
    return "default"


class DataFreshnessService:
    """
    Centralized service for evaluating marine data age, parameter-aware freshness,
    and deterministic source reliability.
    """

    def __init__(self, custom_thresholds: Optional[Dict[str, Dict[str, float]]] = None):
        self.thresholds = custom_thresholds or DEFAULT_THRESHOLDS

    def calculate_age_hours(
        self,
        observation_time: Any,
        reference_time: Optional[Any] = None,
    ) -> Optional[float]:
        """
        Calculate observation age in hours relative to an explicit or current reference time.
        Deterministic: Supports injectable reference_time for reproducible testing.
        """
        obs_dt = parse_timestamp(observation_time)
        if obs_dt is None:
            return None

        ref_dt = parse_timestamp(reference_time) if reference_time is not None else datetime.now(timezone.utc)
        if ref_dt is None:
            ref_dt = datetime.now(timezone.utc)

        delta = ref_dt - obs_dt
        age_hours = delta.total_seconds() / 3600.0
        return max(0.0, round(age_hours, 2))

    def evaluate_freshness(
        self,
        observation_time: Any,
        parameter: str,
        reference_time: Optional[Any] = None,
    ) -> Tuple[FreshnessLevel, Optional[float]]:
        """
        Classify freshness level based on parameter-aware natural lifespans.
        Returns (FreshnessLevel, age_hours).
        """
        age_hours = self.calculate_age_hours(observation_time, reference_time=reference_time)
        if age_hours is None:
            return FreshnessLevel.UNKNOWN, None

        cat = get_parameter_category(parameter)
        cfg = self.thresholds.get(cat, self.thresholds["default"])
        fresh_h = cfg.get("fresh_hours", 24.0)
        recent_h = cfg.get("recent_hours", 48.0)
        stale_h = cfg.get("stale_hours", 168.0)

        if age_hours <= fresh_h:
            return FreshnessLevel.FRESH, age_hours
        elif age_hours <= recent_h:
            return FreshnessLevel.RECENT, age_hours
        elif age_hours <= stale_h:
            return FreshnessLevel.STALE, age_hours
        else:
            return FreshnessLevel.VERY_STALE, age_hours

    def evaluate_reliability(
        self,
        source: str,
        source_type: str,
        freshness: FreshnessLevel,
        status: str = "available",
        is_spatial_match: bool = True,
    ) -> ReliabilityLevel:
        """
        Calculate deterministic, explainable source reliability score.
        Never presents mock/simulated feeds as high reliability.
        """
        src_norm = (source or "").lower()
        type_norm = (source_type or "").lower()
        stat_norm = (status or "").lower()

        # 1. Unavailable or unobserved data
        if stat_norm in ["unavailable", "missing", "error"] or type_norm == "unavailable":
            return ReliabilityLevel.UNKNOWN

        # 2. Simulated or mock fallback sources must be transparently LOW
        if "mock" in src_norm or type_norm in ["simulated", "demo"]:
            return ReliabilityLevel.LOW

        # 3. Missing observation timestamp
        if freshness == FreshnessLevel.UNKNOWN:
            return ReliabilityLevel.UNKNOWN

        # 4. Freshness-based baseline tier
        if freshness == FreshnessLevel.VERY_STALE:
            score = ReliabilityLevel.LOW
        elif freshness == FreshnessLevel.STALE:
            score = ReliabilityLevel.MEDIUM
        elif freshness in [FreshnessLevel.FRESH, FreshnessLevel.RECENT]:
            if type_norm in ["remote_authenticated", "live"]:
                score = ReliabilityLevel.HIGH
            elif type_norm == "archive":
                score = ReliabilityLevel.HIGH if freshness == FreshnessLevel.FRESH else ReliabilityLevel.MEDIUM
            else:
                score = ReliabilityLevel.MEDIUM
        else:
            score = ReliabilityLevel.UNKNOWN

        # 5. Spatial relevance penalty
        if not is_spatial_match and score == ReliabilityLevel.HIGH:
            score = ReliabilityLevel.MEDIUM
        elif not is_spatial_match and score == ReliabilityLevel.MEDIUM:
            score = ReliabilityLevel.LOW

        return score

    def build_evidence_metadata(
        self,
        source: str,
        parameter: str,
        source_type: str = "archive",
        dataset: Optional[str] = None,
        observation_time: Optional[Any] = None,
        retrieval_time: Optional[Any] = None,
        reference_time: Optional[Any] = None,
        status: str = "available",
        is_spatial_match: bool = True,
    ) -> EvidenceMetadata:
        """
        Construct a normalized EvidenceMetadata instance with computed age,
        freshness tier, and deterministic reliability scoring.
        """
        freshness, age_hours = self.evaluate_freshness(
            observation_time=observation_time,
            parameter=parameter,
            reference_time=reference_time,
        )
        reliability = self.evaluate_reliability(
            source=source,
            source_type=source_type,
            freshness=freshness,
            status=status,
            is_spatial_match=is_spatial_match,
        )

        obs_str = (
            observation_time.isoformat()
            if isinstance(observation_time, datetime)
            else (str(observation_time) if observation_time is not None else None)
        )
        ret_str = (
            retrieval_time.isoformat()
            if isinstance(retrieval_time, datetime)
            else (str(retrieval_time) if retrieval_time is not None else None)
        )

        stat_val = status if status in ["available", "unavailable", "degraded", "stale"] else "available"

        return EvidenceMetadata(
            source=source,
            source_type=source_type,
            dataset=dataset,
            parameter=parameter,
            observation_time=obs_str,
            retrieval_time=ret_str,
            age_hours=age_hours,
            freshness=freshness,
            reliability=reliability,
            status=stat_val,
        )


# Global singleton instance
data_freshness_service = DataFreshnessService()
