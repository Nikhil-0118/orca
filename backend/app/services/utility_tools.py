"""
Authoritative Utility Tools for ORCA (Phase 8.2).

Provides trusted, system-clock-derived time, date, day-of-week, and timezone-aware
telemetry (Asia/Kolkata / IST). Prevents the LLM from fabricating timestamps or dates.
"""
from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

logger = logging.getLogger("orca.services.utility")

DEFAULT_TIMEZONE = "Asia/Kolkata"


def get_current_time_data(tz_name: str = DEFAULT_TIMEZONE) -> Dict[str, Any]:
    """
    Returns authoritative current time, date, and day of week for the specified timezone.
    Defaults to Indian Standard Time (Asia/Kolkata, UTC+05:30).
    """
    # IST is UTC+05:30 without daylight saving time
    ist_tz = timezone(timedelta(hours=5, minutes=30))

    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
    except Exception:
        # On Windows systems without tzdata package, use fixed IST offset
        if tz_name == "Asia/Kolkata":
            now = datetime.now(ist_tz)
        else:
            now = datetime.now(timezone.utc)

    time_12h = now.strftime("%I:%M %p").lstrip("0")
    time_24h = now.strftime("%H:%M:%S")
    date_formatted = now.strftime("%A, %B %d, %Y")
    day_of_week = now.strftime("%A")
    iso_datetime = now.isoformat()

    return {
        "current_datetime": iso_datetime,
        "time_12h": time_12h,
        "time_24h": time_24h,
        "date_formatted": date_formatted,
        "day_of_week": day_of_week,
        "year": now.year,
        "month": now.strftime("%B"),
        "day": now.day,
        "timezone": tz_name,
        "timezone_label": "IST (Indian Standard Time)" if tz_name == "Asia/Kolkata" else tz_name,
    }


def format_utility_context(data: Dict[str, Any]) -> str:
    """Format utility data into a clean factual context block for the LLM."""
    return (
        f"FACTUAL SYSTEM TIME CONTEXT:\n"
        f"• Current Date: {data['date_formatted']}\n"
        f"• Current Time: {data['time_12h']} {data['timezone_label']} ({data['time_24h']})\n"
        f"• Day of Week: {data['day_of_week']}\n"
        f"• Timezone: {data['timezone']}\n"
        f"• System ISO Timestamp: {data['current_datetime']}"
    )


def get_location_context(location: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Resolves human-readable geographic area name, coordinates, and provenance
    for the vessel/client location. Never fabricates coordinates if unavailable.
    """
    if not location or not isinstance(location, dict):
        return {
            "available": False,
            "source": "unavailable",
            "region_name": "Location Unavailable",
            "short_name": "location unavailable",
            "is_demo": False,
            "source_label": "No device GPS or coordinates available",
            "coordinates_formatted": "Unavailable",
            "lat": None,
            "lon": None,
        }

    raw_lat = location.get("latitude") if location.get("latitude") is not None else location.get("lat")
    raw_lon = location.get("longitude") if location.get("longitude") is not None else location.get("lon")

    if raw_lat is None or raw_lon is None:
        return {
            "available": False,
            "source": "unavailable",
            "region_name": "Location Unavailable",
            "short_name": "location unavailable",
            "is_demo": False,
            "source_label": "No device GPS or coordinates available",
            "coordinates_formatted": "Unavailable",
            "lat": None,
            "lon": None,
        }

    try:
        lat = float(raw_lat)
        lon = float(raw_lon)
    except (ValueError, TypeError):
        return {
            "available": False,
            "source": "invalid",
            "region_name": "Invalid Coordinates",
            "short_name": "invalid location",
            "is_demo": False,
            "source_label": "Invalid latitude or longitude",
            "coordinates_formatted": "Invalid",
            "lat": None,
            "lon": None,
        }

    is_demo = bool(location.get("is_demo", False))
    source = location.get("source", "demo" if is_demo else "browser_gps")
    accuracy_m = location.get("accuracy_m")

    # Delegate to LocationResolver (using pure-Python geometry & spatial cache)
    from app.services.location_resolver import location_resolver
    resolved = location_resolver.resolve_sync(lat, lon, source=source, is_demo=is_demo)

    lat_str = f"{abs(lat):.2f}° {'N' if lat >= 0 else 'S'}"
    lon_str = f"{abs(lon):.2f}° {'E' if lon >= 0 else 'W'}"

    # Formulate contextual region_name and short_name respecting geographic_type
    place = resolved.place_name or ""
    state_str = f", {resolved.state}" if resolved.state else ""

    if resolved.geographic_type == "inland":
        region_name = f"{place}{state_str} (Inland, approx. {lat_str}, {lon_str})"
        short_name = f"near {place}{state_str} (inland location)"
    elif resolved.geographic_type == "coastal":
        region_name = f"{place}{state_str} (Coastal Region, approx. {lat_str}, {lon_str})"
        short_name = f"near the {place} coastal region"
    elif resolved.geographic_type == "marine":
        region_name = f"{place} ({lat_str}, {lon_str})"
        short_name = f"in {place}"
    else:
        region_name = f"Coordinates ({lat_str}, {lon_str})"
        short_name = f"near coordinates {lat_str}, {lon_str}"

    if is_demo or source == "demo":
        source_label = "Application demonstration coordinates (SIH Demo Mode)"
    elif source == "browser_gps":
        source_label = f"Live Device GPS fix (±{int(accuracy_m)}m)" if accuracy_m else "Live Device GPS fix"
    elif source == "user_override":
        source_label = "Manually specified user coordinates"
    else:
        source_label = "Client-reported session position"

    return {
        "available": True,
        "lat": lat,
        "lon": lon,
        "latitude": lat,
        "longitude": lon,
        "lat_str": lat_str,
        "lon_str": lon_str,
        "coordinates_formatted": f"{lat_str}, {lon_str}",
        "region_name": region_name,
        "short_name": short_name,
        "place_name": resolved.place_name,
        "district": resolved.district,
        "state": resolved.state,
        "country": resolved.country,
        "geographic_type": resolved.geographic_type,
        "is_demo": is_demo,
        "source": source,
        "source_label": source_label,
        "accuracy_m": accuracy_m,
    }


async def get_location_context_async(location: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Asynchronous location context resolution querying live Nominatim reverse-geocoder."""
    if not location:
        return {
            "available": False,
            "source": "unavailable",
            "region_name": "Location unavailable",
            "short_name": "location unavailable",
            "is_demo": False,
            "source_label": "No client coordinates provided",
            "coordinates_formatted": "Unavailable",
            "lat": None,
            "lon": None,
        }

    raw_lat = location.get("latitude") if location.get("latitude") is not None else location.get("lat")
    raw_lon = location.get("longitude") if location.get("longitude") is not None else location.get("lon")

    if raw_lat is None or raw_lon is None:
        return {
            "available": False,
            "source": "unavailable",
            "region_name": "Location unavailable",
            "short_name": "location unavailable",
            "is_demo": False,
            "source_label": "No client coordinates provided",
            "coordinates_formatted": "Unavailable",
            "lat": None,
            "lon": None,
        }

    try:
        lat = float(raw_lat)
        lon = float(raw_lon)
    except (ValueError, TypeError):
        return {
            "available": False,
            "source": "invalid",
            "region_name": "Invalid Coordinates",
            "short_name": "invalid location",
            "is_demo": False,
            "source_label": "Invalid latitude or longitude",
            "coordinates_formatted": "Invalid",
            "lat": None,
            "lon": None,
        }

    is_demo = bool(location.get("is_demo", False))
    source = location.get("source", "demo" if is_demo else "browser_gps")
    accuracy_m = location.get("accuracy_m")

    from app.services.location_resolver import location_resolver
    resolved = await location_resolver.resolve(lat, lon, source=source, is_demo=is_demo)

    lat_str = f"{abs(lat):.2f}° {'N' if lat >= 0 else 'S'}"
    lon_str = f"{abs(lon):.2f}° {'E' if lon >= 0 else 'W'}"

    place = resolved.place_name or ""
    state_str = f", {resolved.state}" if resolved.state else ""

    if resolved.geographic_type == "inland":
        region_name = f"{place}{state_str} (Inland, approx. {lat_str}, {lon_str})"
        short_name = f"near {place}{state_str} (inland location)"
    elif resolved.geographic_type == "coastal":
        region_name = f"{place}{state_str} (Coastal Region, approx. {lat_str}, {lon_str})"
        short_name = f"near the {place} coastal region"
    elif resolved.geographic_type == "marine":
        region_name = f"{place} ({lat_str}, {lon_str})"
        short_name = f"in {place}"
    else:
        region_name = f"Coordinates ({lat_str}, {lon_str})"
        short_name = f"near coordinates {lat_str}, {lon_str}"

    if is_demo or source == "demo":
        source_label = "Application demonstration coordinates (SIH Demo Mode)"
    elif source == "browser_gps":
        source_label = f"Live Device GPS fix (±{int(accuracy_m)}m)" if accuracy_m else "Live Device GPS fix"
    elif source == "user_override":
        source_label = "Manually specified user coordinates"
    else:
        source_label = "Client-reported session position"

    return {
        "available": True,
        "lat": lat,
        "lon": lon,
        "latitude": lat,
        "longitude": lon,
        "lat_str": lat_str,
        "lon_str": lon_str,
        "coordinates_formatted": f"{lat_str}, {lon_str}",
        "region_name": region_name,
        "short_name": short_name,
        "place_name": resolved.place_name,
        "district": resolved.district,
        "state": resolved.state,
        "country": resolved.country,
        "geographic_type": resolved.geographic_type,
        "is_demo": is_demo,
        "source": source,
        "source_label": source_label,
        "accuracy_m": accuracy_m,
    }


def format_location_context(data: Dict[str, Any]) -> str:
    """Format location data into a clean factual context block for the LLM."""
    if not data.get("available", True):
        return (
            "FACTUAL LOCATION CONTEXT:\n"
            "• Status: Location access is currently UNAVAILABLE.\n"
            "• Details: The browser or client has not provided GPS coordinates or location permissions.\n"
            "• Guidance: Inform the user honestly that location access is unavailable and they can enable GPS or select a demonstration region."
        )

    accuracy_info = f" (Accuracy: ±{int(data['accuracy_m'])}m)" if data.get('accuracy_m') else ""
    geo_type_note = f"• Geographic Type: {data.get('geographic_type', 'unknown').upper()}\n"
    place_note = f"• Area/Place: {data.get('place_name')}\n" if data.get('place_name') else ""
    return (
        f"FACTUAL LOCATION CONTEXT:\n"
        f"• Region: {data['region_name']}\n"
        f"{place_note}"
        f"{geo_type_note}"
        f"• Coordinates: {data['coordinates_formatted']}\n"
        f"• Position Source: {data['source_label']}{accuracy_info}\n"
        f"• Is Demo Coordinates: {data['is_demo']}"
    )
