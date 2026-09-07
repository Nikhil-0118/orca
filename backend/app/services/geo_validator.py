"""
Geospatial Consistency & Provenance Validator for ORCA (Phase 8.4).

Verifies whether specialist agent observations (Ocean, Weather, Satellite, Ecosystem)
correspond to the client's requested geographic coordinates within source-specific thresholds.
Prevents mismatched data from being falsely attributed to the user's area.
"""
import math
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.query import LocationContext

logger = logging.getLogger("orca.services.geo_validator")

# Source-dependent maximum distance thresholds in Kilometers
GEO_THRESHOLDS_KM = {
    "weather": 200.0,   # Regional coastal bulletin coverage (~100-200 km)
    "ocean": 60.0,      # Gridded SST/Wind model resolution (~0.25° to 0.5°)
    "satellite": 300.0, # Satellite optical/SAR swath footprint
    "ecosystem": 100.0, # OCM Chlorophyll grid footprint
    "default": 150.0,
}

NAMED_MARITIME_REGIONS: Dict[str, Dict[str, Any]] = {
    "sri lanka": {"latitude": 9.45, "longitude": 79.20, "label": "Palk Bay / Sri Lanka Maritime Sector", "is_demo": True},
    "sri lankan": {"latitude": 9.45, "longitude": 79.20, "label": "Palk Bay / Sri Lanka Maritime Sector", "is_demo": True},
    "palk bay": {"latitude": 9.45, "longitude": 79.20, "label": "Palk Bay / IMBL Sector", "is_demo": True},
    "palk strait": {"latitude": 9.80, "longitude": 79.50, "label": "Palk Strait Sector", "is_demo": True},
    "mumbai": {"latitude": 18.922, "longitude": 72.834, "label": "Mumbai Coastal Waters (Maharashtra)", "is_demo": False},
    "bombay": {"latitude": 18.922, "longitude": 72.834, "label": "Mumbai Coastal Waters (Maharashtra)", "is_demo": False},
    "kochi": {"latitude": 9.931, "longitude": 76.267, "label": "Kochi Coastal Waters (Kerala)", "is_demo": False},
    "cochin": {"latitude": 9.931, "longitude": 76.267, "label": "Kochi Coastal Waters (Kerala)", "is_demo": False},
    "chennai": {"latitude": 13.0827, "longitude": 80.2707, "label": "Chennai Coastal Waters (Tamil Nadu)", "is_demo": False},
    "madras": {"latitude": 13.0827, "longitude": 80.2707, "label": "Chennai Coastal Waters (Tamil Nadu)", "is_demo": False},
    "visakhapatnam": {"latitude": 17.686, "longitude": 83.218, "label": "Visakhapatnam Coastal Waters (Andhra Pradesh)", "is_demo": False},
    "vizag": {"latitude": 17.686, "longitude": 83.218, "label": "Visakhapatnam Coastal Waters (Andhra Pradesh)", "is_demo": False},
    "gujarat": {"latitude": 21.0, "longitude": 70.5, "label": "Gujarat Coastal Waters", "is_demo": False},
    "porbandar": {"latitude": 21.64, "longitude": 69.60, "label": "Porbandar Coastal Waters (Gujarat)", "is_demo": False},
    "odisha": {"latitude": 19.5, "longitude": 85.8, "label": "Odisha Coastal Waters", "is_demo": False},
    "orissa": {"latitude": 19.5, "longitude": 85.8, "label": "Odisha Coastal Waters", "is_demo": False},
    "puri": {"latitude": 19.8, "longitude": 85.82, "label": "Puri Coastal Waters (Odisha)", "is_demo": False},
    "kolkata": {"latitude": 21.5, "longitude": 88.0, "label": "West Bengal / Kolkata Shelf Waters", "is_demo": False},
    "calcutta": {"latitude": 21.5, "longitude": 88.0, "label": "West Bengal / Kolkata Shelf Waters", "is_demo": False},
    "goa": {"latitude": 15.49, "longitude": 73.82, "label": "Goa Coastal Waters", "is_demo": False},
    "mangalore": {"latitude": 12.87, "longitude": 74.84, "label": "Mangalore Coastal Waters (Karnataka)", "is_demo": False},
    "kanyakumari": {"latitude": 8.08, "longitude": 77.55, "label": "Kanyakumari Confluence Waters", "is_demo": False},
    "andaman": {"latitude": 11.67, "longitude": 92.74, "label": "Andaman Sea Waters", "is_demo": False},
    "lakshadweep": {"latitude": 10.57, "longitude": 72.64, "label": "Lakshadweep Waters", "is_demo": False},
}


def resolve_query_spatial_target(
    query: str,
    client_location: LocationContext,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> LocationContext:
    """
    Determines the geographic target for agent queries.
    Checks named maritime regions first, then delegates to India-wide query_location_resolver.
    """
    q_norm = " " + query.lower().replace("?", " ").replace(".", " ").replace(",", " ") + " "
    for region_name, region_data in NAMED_MARITIME_REGIONS.items():
        if f" {region_name} " in q_norm or f"near {region_name}" in q_norm or f"in {region_name}" in q_norm:
            return LocationContext(
                latitude=region_data["latitude"],
                longitude=region_data["longitude"],
                source="named_region",
                is_demo=region_data["is_demo"],
                label=region_data["label"],
            )

    from app.services.query_location_resolver import query_location_resolver
    res = query_location_resolver.resolve_query_location_sync(query, client_location, conversation_history)
    return res.target_location


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two decimal degree points in kilometers."""
    r = 6371.0  # Earth's mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


def validate_agent_geo_consistency(
    requested_lat: Optional[float],
    requested_lon: Optional[float],
    agent_result: Optional[Dict[str, Any]],
    agent_type: str,
) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate spatial distance between user's requested location and agent's resolved location.

    Returns:
      (is_consistent: bool, distance_km: Optional[float], note: Optional[str])
    """
    if requested_lat is None or requested_lon is None:
        return True, None, None

    if not agent_result or not isinstance(agent_result, dict):
        return True, None, None

    # Check if agent result contains resolved location coordinates
    resolved_loc = agent_result.get("location")
    if not resolved_loc or not isinstance(resolved_loc, dict):
        return True, None, None

    res_lat = resolved_loc.get("lat") or resolved_loc.get("latitude")
    res_lon = resolved_loc.get("lon") or resolved_loc.get("longitude")

    if res_lat is None or res_lon is None:
        return True, None, None

    try:
        dist = haversine_distance_km(float(requested_lat), float(requested_lon), float(res_lat), float(res_lon))
    except (ValueError, TypeError):
        return True, None, None

    threshold = GEO_THRESHOLDS_KM.get(agent_type.lower(), GEO_THRESHOLDS_KM["default"])

    if dist > threshold:
        note = (
            f"Geospatial Mismatch: {agent_type.title()} data was sampled from a reference grid {dist:.1f} km away "
            f"({res_lat:.2f}°, {res_lon:.2f}°), exceeding the local threshold of {threshold:.0f} km. "
            f"The mismatched telemetry was discarded."
        )
        logger.warning(
            "geo_consistency_mismatch_detected",
            extra={
                "agent": agent_type,
                "requested": (requested_lat, requested_lon),
                "resolved": (res_lat, res_lon),
                "distance_km": dist,
                "threshold_km": threshold,
            },
        )
        return False, dist, note

    return True, dist, None


def validate_all_agent_locations(
    location_context: Optional[Dict[str, Any]],
    agent_results: Dict[str, Optional[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Run geospatial consistency validation across all converged agent results.
    Returns audit summary with consistency flags and limitation notices.
    """
    if not location_context:
        return {"all_consistent": True, "mismatches": [], "limitation_notes": []}

    req_lat = location_context.get("latitude") or location_context.get("lat")
    req_lon = location_context.get("longitude") or location_context.get("lon")

    if req_lat is None or req_lon is None:
        return {"all_consistent": True, "mismatches": [], "limitation_notes": []}

    mismatches = []
    limitation_notes = []

    for agent_type, res in agent_results.items():
        if res is not None:
            is_consistent, dist, note = validate_agent_geo_consistency(
                requested_lat=req_lat,
                requested_lon=req_lon,
                agent_result=res,
                agent_type=agent_type,
            )
            if not is_consistent:
                mismatches.append({
                    "agent": agent_type,
                    "distance_km": dist,
                    "note": note,
                })
                if note:
                    limitation_notes.append(note)

    return {
        "all_consistent": len(mismatches) == 0,
        "mismatches": mismatches,
        "limitation_notes": limitation_notes,
    }
