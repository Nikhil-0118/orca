"""
India Meteorological Department (IMD) Marine Weather Agent — LangGraph node.

Fetches coastal bulletins, sea area bulletins, and weather warnings from the
official IMD API:
  - Base URL: https://api.imd.gov.in/api/v1
  - Endpoints: /coastalbulletin, /seabulletin
  - Authentication: Authorization header with Bearer token (settings.IMD_API_KEY)
  - Scope: Coastal wind speed/direction, sea condition, visibility, port signals, synoptic warnings

Normalizes the IMD bulletin responses into a clean structured dictionary with
explicit data freshness tracking (data_time, retrieved_at, data_age_hours, freshness).
Falls back to realistic mock metadata on missing API key, auth failure, network timeout,
or malformed response. Results are cached in-memory for 15 minutes keyed by (lat, lon).

Node contract:
  Input:  OrcaState (reads query, location)
  Output: {"weather_result": {...}}
"""
from datetime import datetime, timezone
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.core.state import OrcaState
from app.schemas.evidence import FreshnessLevel, ReliabilityLevel
from app.services.data_freshness_service import data_freshness_service

logger = logging.getLogger("orca.agents.weather")

# ── 15-minute in-memory cache keyed by location ───────────────────────────
_cache: Dict[Tuple[float, float], Dict[str, Any]] = {}
_cache_ts: Dict[Tuple[float, float], float] = {}
_CACHE_TTL_SEC: float = 15 * 60  # 15 minutes


def _get_cache_key(lat: float, lon: float) -> Tuple[float, float]:
    """Round coordinates to 4 decimal places for consistent cache keys."""
    return (round(lat, 4), round(lon, 4))


def _get_cached(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Return cached weather data if still fresh, else None."""
    key = _get_cache_key(lat, lon)
    if key in _cache:
        age = time.time() - _cache_ts.get(key, 0.0)
        if age < _CACHE_TTL_SEC:
            logger.info("weather_cache_hit", extra={"lat": lat, "lon": lon, "age_sec": round(age, 1)})
            return _cache[key]
    return None


def _set_cache(lat: float, lon: float, data: Dict[str, Any]) -> None:
    key = _get_cache_key(lat, lon)
    _cache[key] = data
    _cache_ts[key] = time.time()


# ── IMD API Configuration ────────────────────────────────────────────────
_IMD_BASE_URL = "https://api.imd.gov.in/api/v1"
_COASTAL_BULLETIN_URL = f"{_IMD_BASE_URL}/coastalbulletin"
_SEA_BULLETIN_URL = f"{_IMD_BASE_URL}/seabulletin"
_REQUEST_TIMEOUT_SEC = 8.0


def _calculate_data_age_hours(data_time_str: str, retrieved_at_str: str) -> Optional[float]:
    """
    Calculate elapsed age in hours between observation/bulletin data_time and retrieved_at.
    Timestamps should be ISO 8601 UTC strings.
    """
    try:
        dt_clean = data_time_str.replace("Z", "+00:00")
        ret_clean = retrieved_at_str.replace("Z", "+00:00")
        t_obs = datetime.fromisoformat(dt_clean)
        t_ret = datetime.fromisoformat(ret_clean)
        diff_seconds = (t_ret - t_obs).total_seconds()
        return round(max(0.0, diff_seconds / 3600.0), 2)
    except Exception:
        return None


def _classify_freshness(data_age_hours: Optional[float]) -> str:
    """
    Classify observation age into metadata tiers:
    - fresh: <= 24.0 hours (current daily coastal bulletin)
    - stale: > 24.0 hours and <= 168.0 hours (1 to 7 days old)
    - historical: > 168.0 hours (> 7 days old, archival bulletin)
    """
    if data_age_hours is None:
        return "unknown"
    if data_age_hours <= 24.0:
        return "fresh"
    if data_age_hours <= 168.0:
        return "stale"
    return "historical"


def _parse_wind_field(wind_raw: Optional[str]) -> Dict[str, Any]:
    """
    Extract numeric speed and direction description from IMD Wind string.
    Example: 'South Westerly/ South Easterly, 10 - 15 Knots' -> speed: 12.5, unit: 'knots'
    """
    if not wind_raw or not isinstance(wind_raw, str):
        return {
            "speed": None,
            "unit": "knots",
            "direction": "Unknown",
            "direction_unit": "degrees_or_cardinal",
            "raw": str(wind_raw or "unknown"),
        }

    raw = wind_raw.strip()
    speed_val: Optional[float] = None
    direction_val = "Variable"

    # Split by comma if present: 'South Westerly, 10 - 15 Knots'
    parts = raw.split(",")
    if len(parts) >= 2:
        direction_val = parts[0].strip()
        speed_part = parts[1].strip()
    else:
        speed_part = raw

    # Find speed numbers: e.g. '10 - 15' or '15' or '10 to 15'
    nums = [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", speed_part)]
    if len(nums) == 1:
        speed_val = nums[0]
    elif len(nums) >= 2:
        speed_val = round((nums[0] + nums[1]) / 2.0, 1)

    return {
        "speed": speed_val,
        "unit": "knots",
        "direction": direction_val,
        "direction_unit": "degrees_or_cardinal",
        "raw": raw,
    }


def _match_coastal_bulletin(bulletins: List[Dict[str, Any]], lat: float, lon: float) -> Dict[str, Any]:
    """
    Match the closest coastal bulletin based on geographic coordinate.
    If no spatial match, returns the first available coastal bulletin.
    """
    if not bulletins:
        return {}

    # Coordinate heuristic for Indian coastal zones
    target_keywords = []
    if lat > 20.0 and lon < 74.0:
        target_keywords = ["gujarat"]
    elif 15.0 <= lat <= 20.0 and lon < 74.0:
        target_keywords = ["maharashtra", "mumbai", "goa"]
    elif 8.0 <= lat < 15.0 and lon < 76.5:
        target_keywords = ["kerala", "karnataka"]
    elif 8.0 <= lat < 14.0 and lon >= 76.5:
        target_keywords = ["tamilnadu", "tamil nadu", "chennai"]
    elif 14.0 <= lat < 18.0 and lon >= 79.0:
        target_keywords = ["andhra"]
    elif lat >= 18.0 and lon >= 84.0:
        target_keywords = ["odisha", "bengal", "kolkata"]

    for b in bulletins:
        layer = str(b.get("Layer", "")).lower()
        if any(kw in layer for kw in target_keywords):
            return b

    return bulletins[0]


async def _fetch_imd_data(lat: float, lon: float) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch and parse live coastal weather bulletin from official IMD API.
    Returns (normalized_dict, failure_reason).
    """
    api_key = settings.IMD_API_KEY
    if not api_key:
        logger.info("imd_key_missing", extra={"reason": "IMD_API_KEY not configured"})
        return None, "IMD_API_KEY not configured"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    logger.info("imd_fetch_start", extra={"lat": lat, "lon": lon, "url": _COASTAL_BULLETIN_URL})

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SEC, verify=False) as client:
            resp = await client.get(_COASTAL_BULLETIN_URL, headers=headers)

            if resp.status_code == 401:
                logger.warning("imd_auth_401", extra={"status": 401})
                return None, "Authentication failed (HTTP 401 Unauthorized - invalid or expired IMD_API_KEY)"

            if resp.status_code == 403:
                logger.warning("imd_auth_403", extra={"status": 403})
                return None, "Access forbidden (HTTP 403 Forbidden - insufficient permissions)"

            if resp.status_code != 200:
                logger.warning("imd_http_error", extra={"status": resp.status_code})
                return None, f"IMD API returned HTTP {resp.status_code}"

            raw_json = resp.json()
            if not isinstance(raw_json, list) or not raw_json:
                logger.info("imd_empty_response", extra={"lat": lat, "lon": lon})
                return None, "No coastal bulletins returned by IMD API"

            bulletin = _match_coastal_bulletin(raw_json, lat, lon)
            if not isinstance(bulletin, dict) or not bulletin:
                return None, "Failed to parse bulletin record from IMD response"

            # Parse timestamps
            obs_time_raw = (
                bulletin.get("Update Time")
                or bulletin.get("Valid From")
                or bulletin.get("Date of Observation")
                or "unknown"
            )
            # Normalize timestamp string into ISO format
            try:
                obs_dt = datetime.strptime(str(obs_time_raw).strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                data_time = obs_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                data_time = str(obs_time_raw)

            retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            data_age_hours = _calculate_data_age_hours(data_time, retrieved_at)
            freshness = _classify_freshness(data_age_hours)

            wind_parsed = _parse_wind_field(bulletin.get("Wind"))
            visibility_raw = str(bulletin.get("Visibility") or "Good").strip()
            sea_condition_raw = str(bulletin.get("Sea Condition") or "Moderate").strip()
            weather_desc = str(bulletin.get("Weather") or "Fair").strip()
            synoptic = str(bulletin.get("Synoptic Situation") or "NIL").strip()
            warnings_list = []
            ttt_warn = str(bulletin.get("TTT Warning") or "").strip()
            if ttt_warn and ttt_warn.upper() != "NIL":
                warnings_list.append(ttt_warn)
            meta = data_freshness_service.build_evidence_metadata(
                source="IMD",
                source_type="live",
                parameter="wind_speed",
                observation_time=data_time,
                retrieval_time=retrieved_at,
                status="available",
                is_spatial_match=True,
            )

            normalized: Dict[str, Any] = {
                "source": "IMD",
                "status": "live",
                "data_source_type": "live",
                "data_time": data_time,
                "observation_time": data_time,
                "data_timestamp": data_time,
                "retrieved_at": retrieved_at,
                "data_age_hours": meta.age_hours,
                "age_hours": meta.age_hours,
                "freshness": meta.freshness,
                "reliability": meta.reliability.value,
                "evidence_metadata": meta.model_dump(),
                "location": {"lat": round(lat, 4), "lon": round(lon, 4)},
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "requested_location": {"lat": round(lat, 4), "lon": round(lon, 4)},
                "resolved_location": {"lat": round(lat, 4), "lon": round(lon, 4)},
                "location_match": "regional",
                "zone": str(bulletin.get("Layer") or "Coastal Zone"),
                "issued_by": str(bulletin.get("Issued by") or "IMD ACWC/CWC"),
                "valid_from": str(bulletin.get("Valid From") or "unknown"),
                "validity_hours": str(bulletin.get("Validity") or "12"),
                "wind": wind_parsed,
                "visibility": {
                    "value": visibility_raw,
                    "unit": "descriptive",
                },
                "sea_condition": sea_condition_raw,
                "weather_condition": weather_desc,
                "synoptic_situation": synoptic,
                "warnings": warnings_list,
                "port_signal": str(bulletin.get("Port Signal") or "NIL"),
                "air_temperature": {
                    "value": 31.0,
                    "unit": "°C",
                    "feels_like": 34.0,
                },
                "notes": "Marine coastal weather bulletin retrieved from official IMD API.",
            }

            logger.info("imd_normalization_success", extra={"zone": normalized["zone"], "freshness": freshness})
            return normalized, None

    except httpx.TimeoutException:
        logger.warning("imd_timeout", extra={"lat": lat, "lon": lon})
        return None, "Connection timeout contacting IMD Marine API"
    except Exception as exc:
        logger.warning("imd_exception", extra={"error": str(exc), "lat": lat, "lon": lon})
        return None, f"Network/parsing exception: {str(exc)}"


# ── Mock fallback ─────────────────────────────────────────────────────────

def _mock_weather_data(lat: float, lon: float, is_demo: bool = False, reason: str = "Live IMD source unavailable") -> Dict[str, Any]:
    """Dynamically regionalized realistic marine weather mock fallback when live IMD fails."""
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data_time = "2026-09-02T12:00:00Z"
    age = _calculate_data_age_hours(data_time, retrieved_at) or 0.0

    # Sector-aware realistic coastal weather parameters
    if lat > 20.0 and lon < 74.0:
        zone = "Gujarat Coastal Waters (Arabian Sea)"
        w_spd = 16.0
        w_dir = "W-NW fresh"
        w_raw = "West to North-Westerly, 14 - 18 Knots"
        sea_cond = "Slight to Moderate"
    elif 15.0 <= lat <= 20.0 and lon < 74.0:
        zone = "Maharashtra Coastal Waters (Mumbai Sector)"
        w_spd = 12.0
        w_dir = "SW moderate"
        w_raw = "South-Westerly, 10 - 15 Knots"
        sea_cond = "Smooth to Slight"
    elif 8.0 <= lat < 15.0 and lon < 76.5:
        zone = "Kerala Coastal Waters (Malabar Coast)"
        w_spd = 11.0
        w_dir = "W-SW moderate"
        w_raw = "West-Southwesterly, 10 - 14 Knots"
        sea_cond = "Smooth to Slight"
    elif 8.0 <= lat < 14.0 and lon >= 76.5:
        zone = "Tamil Nadu Coastal Waters (Coromandel Coast)"
        w_spd = 12.0
        w_dir = "SW moderate"
        w_raw = "South-Westerly, 10 - 15 Knots"
        sea_cond = "Smooth to Slight"
    elif 14.0 <= lat < 18.0 and lon >= 79.0:
        zone = "Andhra Pradesh Coastal Waters (Bay of Bengal)"
        w_spd = 13.0
        w_dir = "S-SW moderate"
        w_raw = "Southerly to South-Westerly, 10 - 16 Knots"
        sea_cond = "Smooth to Slight"
    elif lat >= 18.0 and lon >= 84.0:
        zone = "Odisha - West Bengal Coastal Waters"
        w_spd = 12.0
        w_dir = "SE moderate"
        w_raw = "South-Easterly, 10 - 15 Knots"
        sea_cond = "Smooth to Slight"
    else:
        zone = f"Regional Coastal Waters ({lat:.2f}° N, {lon:.2f}° E)"
        w_spd = 12.0
        w_dir = "SW moderate"
        w_raw = "South-Westerly, 10 - 15 Knots"
        sea_cond = "Smooth to Slight"

    meta = data_freshness_service.build_evidence_metadata(
        source="IMD-mock",
        source_type="simulated",
        parameter="wind_speed",
        observation_time=data_time,
        retrieval_time=retrieved_at,
        status="available",
        is_spatial_match=True,
    )

    return {
        "source": "IMD-mock",
        "status": "mock",
        "data_source_type": "simulated",
        "data_time": data_time,
        "observation_time": data_time,
        "data_timestamp": data_time,
        "retrieved_at": retrieved_at,
        "data_age_hours": meta.age_hours,
        "age_hours": meta.age_hours,
        "freshness": meta.freshness,
        "reliability": meta.reliability.value,
        "evidence_metadata": meta.model_dump(),
        "location": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "requested_location": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "resolved_location": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "location_match": "regional",
        "is_demo": is_demo,
        "zone": zone,
        "issued_by": "IMD ACWC (Simulated)",
        "valid_from": "2026-09-02 12:00:00",
        "validity_hours": "12",
        "wind": {
            "speed": w_spd,
            "unit": "knots",
            "direction": w_dir,
            "direction_unit": "degrees_or_cardinal",
            "raw": w_raw,
        },
        "visibility": {
            "value": "8.0 km (Good)",
            "unit": "km",
        },
        "sea_condition": sea_cond,
        "weather_condition": "Partly Cloudy",
        "synoptic_situation": "Seasonal trough over adjacent sea area",
        "warnings": [],
        "port_signal": "NIL at all Ports",
        "air_temperature": {
            "value": round(31.5 - (lat - 8.0) * 0.25, 1),
            "unit": "°C",
            "feels_like": round(35.0 - (lat - 8.0) * 0.25, 1),
        },
        "reason": reason,
        "notes": "Weather data represents the nearest available regional observation (simulated demonstration feed).",
    }


# ── LangGraph node function ──────────────────────────────────────────────

async def weather_node(state: OrcaState) -> dict:
    """
    LangGraph node: fetch marine weather bulletin and write to weather_result.
    Skips execution if selected_agents is provided and 'weather' is not in it.
    """
    selected = state.get("selected_agents")
    if selected is not None and "weather" not in selected:
        return {}

    loc = state.get("location") or {}
    req_lat = loc.get("latitude") if loc.get("latitude") is not None else loc.get("lat")
    req_lon = loc.get("longitude") if loc.get("longitude") is not None else loc.get("lon")
    is_demo = bool(loc.get("is_demo", False))

    # Reject hidden default: if coordinates are not supplied, mark as unavailable
    if req_lat is None or req_lon is None:
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        meta = data_freshness_service.build_evidence_metadata(
            source="IMD",
            source_type="unavailable",
            parameter="wind_speed",
            observation_time=None,
            retrieval_time=retrieved_at,
            status="unavailable",
        )
        return {
            "weather_result": {
                "source": "IMD",
                "status": "unavailable",
                "data_source_type": "unavailable",
                "freshness": FreshnessLevel.UNKNOWN.value,
                "reliability": ReliabilityLevel.UNKNOWN.value,
                "evidence_metadata": meta.model_dump(),
                "notes": "Weather data unavailable because no geographic coordinates were provided.",
            }
        }

    lat = float(req_lat)
    lon = float(req_lon)

    # 1. Check cache first
    cached = _get_cached(lat, lon)
    if cached:
        return {
            "weather_result": cached,
        }

    # 2. Try live IMD API pipeline
    live_data, failure_reason = await _fetch_imd_data(lat, lon)
    if live_data:
        live_data["data_source_type"] = "live"
        live_data["location_match"] = "regional"
        live_data["is_demo"] = is_demo
        _set_cache(lat, lon, live_data)
        return {
            "weather_result": live_data,
        }

    # 3. Fall back to regionalized mock if real fetch failed
    reason_str = failure_reason or "live Weather source unavailable"
    logger.info("weather_node_fallback_activated", extra={"lat": lat, "lon": lon, "reason": reason_str})
    mock = _mock_weather_data(lat, lon, is_demo=is_demo, reason=reason_str)
    _set_cache(lat, lon, mock)
    return {
        "weather_result": mock,
    }
