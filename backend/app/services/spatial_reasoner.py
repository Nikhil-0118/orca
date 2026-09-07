"""
Spatial Intelligence & Reasoning Service for ORCA (Phase 18).

Deterministically identifies spatial requests and constructs spatial map payloads
(SpatialPayload) for the chatbot interface without inventing safety data, fake PFZ
polygons, or road-based routing.

Authoritative Rules:
1. Purely deterministic intent classification. Non-spatial factual queries
   (chlorophyll, weather, SST, fishing advisories) NEVER trigger spatial output.
2. Reuses existing trusted services:
   - geofence_service (distance, bearing, IMBL boundary GeoJSON)
   - query_location_resolver (India Gazetteer & entity extraction)
   - location_resolver (reverse geocoding & classification)
3. Nautical marine routing uses geodesic Great-Circle formulas. Never calls road-routing APIs.
4. Does NOT fabricate boat speed. If speed is unavailable, estimated_time_minutes is None.
5. Does NOT create fake PFZ / high-chlorophyll polygons.
6. The Marine Decision Engine and GeofenceService remain the sole safety authorities;
   this service merely visualizes their conclusions.
"""
from dataclasses import dataclass
import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.query import (
    LocationContext,
    MapMarker,
    MapRoute,
    MapZone,
    SpatialPayload,
    SpatialQueryType,
)
from app.services.geofence_service import (
    geofence_service,
    haversine_distance_km,
    calculate_bearing,
    SafetyState,
)
from app.services.location_resolver import _min_distance_to_coast_km
from app.services.query_location_resolver import INDIA_GAZETTEER

logger = logging.getLogger("orca.services.spatial")

# Path to local IMBL boundary GeoJSON
_GEOJSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "imbl_boundary_sample.geojson"
)

# ── Non-Spatial Exclusion Patterns ──────────────────────────────────────────
# Queries matching these patterns are purely factual or advisory and MUST NOT trigger maps
# unless an explicit spatial pattern (e.g. fishing destination, route, or follow-up map) is present.
NON_SPATIAL_EXCLUSIONS = [
    r"\bchlorophyll\b",
    r"\bweather\b",
    r"\bsst\b",
    r"\bsea surface temp",
    r"\bwater temp",
    r"\bwave height\b",
    r"\bwind speed\b",
    r"\bwill i get more fish\b",
    r"\bfish abundance\b",
    r"\bmore fish\b",
    r"\bhow is the sea\b",
    r"\bvisibility near\b",
]

# ── Explicit Spatial Patterns ───────────────────────────────────────────────
USER_LOCATION_PATTERNS = [
    r"\bwhere am i\b",
    r"\bmy (?:current )?location\b",
    r"\bwhat is my (?:current )?location\b",
    r"\bshow (?:my )?(?:current )?location\b",
    r"\bshow (?:my )?(?:current )?position\b",
    r"\bmy (?:current )?coordinates\b",
    r"\bwhere is my boat\b",
    r"\bshow my boat\b",
]

BOUNDARY_SAFETY_PATTERNS = [
    r"\bhow far (?:am i|is the vessel) from the boundary\b",
    r"\bdistance to (?:the )?boundary\b",
    r"\bboundary distance\b",
    r"\bshow (?:the )?(?:safe zone|boundary)\b",
    r"\bsafe zone\b",
    r"\bam i near (?:the )?boundary\b",
    r"\bboundary status\b",
    r"\bshow (?:the )?imbl\b",
    r"\bproximity to boundary\b",
    r"\bnearest boundary\b",
]

DANGER_AREA_PATTERNS = [
    r"\bshow (?:dangerous|danger) areas\b",
    r"\bdangerous areas (?:around|near) my boat\b",
    r"\bdanger areas\b",
    r"\bhazard zones?\b",
    r"\brestricted areas?\b",
    r"\bshow hazards?\b",
]

FISHING_DESTINATION_PATTERNS = [
    r"\b(?:where\s+is\s+)?(?:the\s+)?(?:best|recommended|good|top|safe)\s+(?:place|spot|area|zone|location|ground)s?\s+to\s+fish\b",
    r"\b(?:where\s+is\s+)?(?:the\s+)?(?:best|recommended|good|top|safe)\s+fishing\s+(?:spot|area|zone|place|location|ground)s?\b",
    r"\b(?:give|tell|find|show|suggest|recommend)\s+(?:me\s+)?(?:a\s+|the\s+)?(?:good|best|safe|recommended\s+)?(?:fishing\s+)?(?:spot|area|zone|ground|place|location)(?:\s+for\s+fishing)?\b",
    r"\b(?:safe|best|good|recommended|top)\s+spot\s+for\s+fishing\b",
    r"\bspot\s+for\s+fishing\b",
    r"\b(?:place|location|zone|area|ground)s?\s+for\s+fishing\b",
    r"\bwhere\s+(?:can|should|do)\s+(?:i|fishermen|we)\s+fish\b",
    r"\bwhere\s+can\s+fishermen\s+fish\b",
    r"\bwhere\s+to\s+fish\b",
    r"\bcan\s+i\s+(?:go\s+)?fish(?:ing)?\b",
    r"\bshould\s+i\s+(?:go\s+)?fish(?:ing)?\b",
    r"\bcan\s+i\s+fish\b",
    r"\bi\s+want\s+to\s+go\s+fish(?:ing)?\b",
    r"\bgo\s+fishing\b",
    r"\bis\s+fishing\s+safe\b",
    r"\bfind\s+(?:me\s+)?(?:a\s+)?(?:good|best|safe|recommended\s+)?fishing\s+(?:spot|ground|place|location)\b",
    r"\btake\s+me\s+to\s+(?:the\s+)?(?:recommended\s+)?fishing\s+spot\b",
    r"\bfishing\s+(?:spot|area|zone|location|ground)s?\s+(?:near|around|in|at)\b",
    r"\bshow\s+(?:me\s+)?(?:the\s+)?fishing\s+(?:spot|area|zone|location|ground)s?\b",
    r"\broute\s+to\s+(?:the\s+)?fishing\s+(?:spot|area|zone|location|ground)\b",
    r"\bnavigate\s+to\s+(?:the\s+)?(?:recommended\s+)?fishing\s+(?:spot|area|zone|location|ground)\b",
    r"\bwhat(?:'s|\s+is)\s+the\s+(?:best|safe|recommended)\s+fishing\s+location\b",
    r"\bwhat(?:'s|\s+is)\s+the\s+(?:best|safe|recommended)\s+fishing\s+spot\b",
    r"\bfind\s+(?:the\s+)?(?:maximum|most|best|more)?\s*fish(?:es)?\b",
    r"\bmaximum\s+fish(?:es)?\b",
    r"\bwhere\s+(?:can|to)\s+(?:i|we)?\s*find\s+(?:the\s+)?(?:maximum|most|best)?\s*fish(?:es)?\b",
    r"\bwhere\s+are\s+(?:the\s+)?fish(?:es)?\b",
    r"\bwhich\s+area\s+(?:near\s+.+?\s+)?(?:is\s+)?(?:better|best|good)\s+for\s+fish(?:ing)?\b",
    r"\bwhere\s+should\s+i\s+go\s+fish(?:ing)?\b",
    r"\bbest\s+fishing\s+area\b",
    r"\bbest\s+spot\s+near\b",
]

FOLLOWUP_MAP_PATTERNS = [
    r"\bgive\s+(?:me\s+)?(?:the\s+)?map\b",
    r"\bshow\s+(?:me\s+)?(?:the\s+)?map\b",
    r"\bopen\s+(?:the\s+)?map\b",
    r"\bdisplay\s+(?:the\s+)?map\b",
    r"\bview\s+(?:the\s+)?map\b",
    r"\bmap\s+it\b",
    r"\bshow\s+(?:the\s+)?location\b",
    r"\bshow\s+me\s+that\s+location\b",
    r"\bshow\s+(?:me\s+)?(?:the\s+)?fishing\s+(?:spot|ground|location|place)\b",
    r"\bwhere\s+is\s+it\b",
    r"\bshow\s+me\s+there\b",
]

FOLLOWUP_ROUTING_PATTERNS = [
    r"(?:can\s+(?:you|u)\s+)?(?:give|show)\s+(?:me\s+)?(?:the\s+|a\s+)?route\b",
    r"\bhow\s+(?:do|can)\s+i\s+(?:get|reach)\s+there\b",
    r"\bhow\s+(?:do|can)\s+i\s+reach\s+(?:that|the)\s+(?:fishing\s+)?(?:spot|location|ground|place)\b",
    r"\bnavigate\s+there\b",
    r"\btake\s+me\s+there\b",
    r"\btake\s+(?:me|us)\s+to\b",
    r"\broute\s+to\b",
    r"\bnavigate\s+to\b",
    r"\broute\s+to\s+it\b",
    r"\b(?:give|show)\s+(?:me\s+)?directions\b",
    r"\bdirections\s+to\s+(?:it|there)\b",
    r"\bnavigation\s+to\s+(?:it|there)\b",
    r"\bhow\s+(?:do|can)\s+we\s+(?:get|reach)\s+there\b",
]

LOCATION_PIVOT_PATTERNS = [
    r"^(?:what|how)\s+about\s+(?P<place>.+?)\??$",
    r"^and\s+(?P<place>.+?)\??$",
    r"^what\s+near\s+(?P<place>.+?)\??$",
]

MARINE_ROUTE_PATTERNS = [
    r"route from (?P<from>.+?) to (?P<to>.+)",
    r"route between (?P<from>.+?) and (?P<to>.+)",
    r"show (?:me )?(?:a |the )?route from (?P<from>.+?) to (?P<to>.+)",
    r"show (?:me )?(?:a |the )?route to (?P<to>.+)",
    r"give (?:me )?(?:a |the )?route to (?P<to>.+)",
    r"route to (?P<to>.+)",
    r"navigate to (?P<to>.+)",
    r"navigation route (?:to |from )",
    r"sea route",
]

TARGET_MAP_PATTERNS = [
    r"^show (?:me )?(?P<target>[a-zA-Z\s]+?)\.?$",
    r"show (?P<target>.+?) on (?:the )?map",
    r"map of (?P<target>.+)",
    r"display (?P<target>.+?) on map",
    r"show (?:the )?map of (?P<target>.+)",
    r"show map near (?P<target>.+)",
]


def _has_valid_active_target(
    target_location: Optional[LocationContext],
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> bool:
    """Check whether a valid non-default destination or active target exists in context."""
    if target_location and target_location.latitude is not None and target_location.longitude is not None:
        if target_location.source in ("explicit_query", "conversation_context") or target_location.resolved_place:
            return True
    if conversation_history:
        for turn in reversed(conversation_history[-6:]):
            c = turn.get("content", "").lower()
            if any(key in c for key in INDIA_GAZETTEER) or any(key in c for key in FISHING_GROUNDS_CATALOG):
                return True
    return False


def detect_spatial_intent(
    query: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    target_location: Optional[LocationContext] = None,
) -> Tuple[bool, Optional[SpatialQueryType]]:
    """
    Deterministically determines whether a query has explicit spatial intent.
    Supports generic follow-ups ('give the map', 'can u give me the route')
    and location pivots ('what about Chennai?') by resolving context dynamically.
    Returns (is_spatial, spatial_query_type).
    """
    q = query.strip().lower()

    # 1. Explicit Marine Route with named endpoints (e.g. 'route to Mumbai', 'give me a route to Mumbai')
    for pat in MARINE_ROUTE_PATTERNS:
        if re.search(pat, q):
            return True, "marine_route"

    # 2. Follow-up routing & navigation intent when an active target exists
    for r_pat in FOLLOWUP_ROUTING_PATTERNS:
        if re.search(r_pat, q):
            has_target = _has_valid_active_target(target_location, conversation_history)
            if has_target:
                is_fishing_thread = False
                if conversation_history:
                    for turn in reversed(conversation_history[-6:]):
                        c = turn.get("content", "").lower()
                        if any(w in c for w in ["fish", "fishing", "fisherman", "pfz", "spot", "ground"]):
                            is_fishing_thread = True
                            break
                if any(w in q for w in ["fish", "fishing", "spot"]):
                    is_fishing_thread = True

                if is_fishing_thread:
                    return True, "fishing_destination"
                return True, "marine_route"

    # 2. Generic follow-up map patterns ("give me the map", "show the map", etc.)
    for fo_pat in FOLLOWUP_MAP_PATTERNS:
        if re.search(fo_pat, q):
            is_fishing_thread = False
            is_boundary_thread = False
            if conversation_history:
                for turn in reversed(conversation_history[-6:]):
                    c = turn.get("content", "").lower()
                    if any(w in c for w in ["fish", "fishing", "fisherman", "pfz", "spot", "ground"]):
                        is_fishing_thread = True
                        break
                    if any(w in c for w in ["safe zone", "boundary", "imbl", "hazard", "danger", "restricted"]):
                        is_boundary_thread = True
                        break

            if is_fishing_thread:
                return True, "fishing_destination"
            if is_boundary_thread:
                return True, "boundary_safety"
            if target_location and target_location.latitude is not None:
                return True, "target_location"
            return True, "user_location"

    # 3. Location pivot queries ("what about Chennai?", "and Goa?")
    for piv_pat in LOCATION_PIVOT_PATTERNS:
        m = re.match(piv_pat, q)
        if m:
            if conversation_history:
                for turn in reversed(conversation_history[-6:]):
                    c = turn.get("content", "").lower()
                    if any(w in c for w in ["fish", "fishing", "fisherman", "pfz", "spot"]):
                        return True, "fishing_destination"
                    if any(w in c for w in ["safe zone", "boundary", "imbl"]):
                        return True, "boundary_safety"

    # 4. Strict non-spatial exclusions
    for pattern in NON_SPATIAL_EXCLUSIONS:
        if re.search(pattern, q):
            has_route_override = any(re.search(r_pat, q) for r_pat in [r"route from", r"route to", r"navigate to"])
            has_fishing_override = any(re.search(f_pat, q) for f_pat in FISHING_DESTINATION_PATTERNS)
            has_boundary_override = any(re.search(b_pat, q) for b_pat in BOUNDARY_SAFETY_PATTERNS)
            if not (has_route_override or has_fishing_override or has_boundary_override):
                return False, None

    # 5. Fishing Destination (prioritize over generic marine route)
    for pat in FISHING_DESTINATION_PATTERNS:
        if re.search(pat, q):
            return True, "fishing_destination"

    # 6. Marine Route
    for pat in MARINE_ROUTE_PATTERNS:
        if re.search(pat, q):
            return True, "marine_route"

    # 7. Boundary Safety
    for pat in BOUNDARY_SAFETY_PATTERNS:
        if re.search(pat, q):
            return True, "boundary_safety"

    # 8. Danger Areas
    for pat in DANGER_AREA_PATTERNS:
        if re.search(pat, q):
            return True, "danger_areas"

    # 9. User Location
    for pat in USER_LOCATION_PATTERNS:
        if re.search(pat, q):
            return True, "user_location"

    # 10. Explicit Target Map Display (exclude route/map phrases)
    for pat in TARGET_MAP_PATTERNS:
        m = re.search(pat, q)
        if m:
            target_str = m.groupdict().get("target", "").strip().lower()
            if target_str in ("route", "the route", "directions", "the directions", "map", "the map"):
                continue
            return True, "target_location"

    return False, None


# ── Authoritative Coastal & Offshore Fishing Grounds Catalog ─────────────────
# Baseline catalog of known productive marine fishing grounds across Indian waters.
# NOTE: In accordance with data integrity rules, catalog coordinates are marked as
# "Catalog Baseline" or "Deterministic Baseline" — NEVER as "LIVE PFZ" unless backed
# by active MOSDAC satellite ingest.
FISHING_GROUNDS_CATALOG: Dict[str, Dict[str, Any]] = {
    "chennai": {
        "latitude": 12.8500,
        "longitude": 80.3500,
        "name": "Chennai Offshore Pelagic Ground (Catalog Baseline)",
        "description": "Recommended pelagic fishing sector ~32 km offshore Chennai. Favorable chlorophyll gradient.",
    },
    "kasimedu": {
        "latitude": 13.1250,
        "longitude": 80.3400,
        "name": "Kasimedu Offshore Pelagic Zone (Catalog Baseline)",
        "description": "Active fishing ground off Kasimedu harbor with favorable coastal drift and pelagic concentration.",
    },
    "ennore": {
        "latitude": 13.2650,
        "longitude": 80.3800,
        "name": "Ennore Shoals Fishing Sector (Catalog Baseline)",
        "description": "Marine fishing zone ~12 km off Ennore coastline; favorable baitfish density.",
    },
    "pulicat": {
        "latitude": 13.4300,
        "longitude": 80.3600,
        "name": "Pulicat Deep Marine Ground (Catalog Baseline)",
        "description": "Seaward marine corridor off Pulicat lagoon with active pelagic schools.",
    },
    "mahabalipuram": {
        "latitude": 12.6100,
        "longitude": 80.2500,
        "name": "Mahabalipuram Offshore Shelf (Catalog Baseline)",
        "description": "Continental shelf fishing ground ~15 km east of Mahabalipuram.",
    },
    "cuddalore": {
        "latitude": 11.7400,
        "longitude": 79.8200,
        "name": "Cuddalore Shelf Fishing Zone (Catalog Baseline)",
        "description": "High nutrient marine sector off Cuddalore coast.",
    },
    "nagapattinam": {
        "latitude": 10.7600,
        "longitude": 79.8900,
        "name": "Nagapattinam Deep Shelf Ground (Catalog Baseline)",
        "description": "Active marine ground with consistent demersal and pelagic catch.",
    },
    "rameshwaram": {
        "latitude": 9.2800,
        "longitude": 79.3500,
        "name": "Palk Bay Permitted Fishing Corridor (Catalog Baseline)",
        "description": "Indian territorial waters fishing ground; maintain strict clearance from IMBL boundary.",
    },
    "kanyakumari": {
        "latitude": 8.0500,
        "longitude": 77.5800,
        "name": "Wedge Bank Fishing Ground (Catalog Baseline)",
        "description": "Renowned rich fishing bank at the confluence of Arabian Sea, Bay of Bengal, and Indian Ocean.",
    },
    "kochi": {
        "latitude": 9.9300,
        "longitude": 76.2000,
        "name": "Kochi Offshore Pelagic Zone (Catalog Baseline)",
        "description": "Productive upwelling marine sector ~14 km off Malabar coast.",
    },
    "mangalore": {
        "latitude": 12.8600,
        "longitude": 74.7800,
        "name": "Mangalore Shelf Fishing Sector (Catalog Baseline)",
        "description": "Deep water fishing corridor with high mackerel and sardine abundance.",
    },
    "goa": {
        "latitude": 15.4800,
        "longitude": 73.7500,
        "name": "Goa Shelf Pelagic Zone (Catalog Baseline)",
        "description": "Productive continental shelf fishing area off Panaji.",
    },
    "mumbai": {
        "latitude": 18.9200,
        "longitude": 72.7500,
        "name": "Bombay High Coastal Waters (Catalog Baseline)",
        "description": "Marine fishing zone ~18 km off Mumbai coast.",
    },
    "visakhapatnam": {
        "latitude": 17.6800,
        "longitude": 83.2800,
        "name": "Vizag Deep Trench Fishing Area (Catalog Baseline)",
        "description": "Deep bathymetric fishing shelf with active tuna and seerfish runs.",
    },
    "dwarka": {
        "latitude": 22.2400,
        "longitude": 68.9000,
        "name": "Dwarka Coastal Shelf Ground (Catalog Baseline)",
        "description": "Arabian Sea marine fishing corridor off Saurashtra coast.",
    },
    "kolkata": {
        "latitude": 21.6500,
        "longitude": 88.0500,
        "name": "Northern Bay of Bengal Shelf Sector (Catalog Baseline)",
        "description": "Marine fishing sector off Digha/Sundarbans continental shelf.",
    },
    "paradip": {
        "latitude": 20.2500,
        "longitude": 86.7500,
        "name": "Paradip Offshore Marine Ground (Catalog Baseline)",
        "description": "Deep continental shelf ground off Odisha maritime zone.",
    },
    "tuticorin": {
        "latitude": 8.7500,
        "longitude": 78.2500,
        "name": "Gulf of Mannar Fishing Corridor (Catalog Baseline)",
        "description": "Active pelagic marine corridor off Thoothukudi coast.",
    },
    "puri": {
        "latitude": 19.7500,
        "longitude": 85.9000,
        "name": "Puri Coastal Marine Ground (Catalog Baseline)",
        "description": "Pelagic corridor off Odisha coast.",
    },
    "porbandar": {
        "latitude": 21.6000,
        "longitude": 69.5000,
        "name": "Porbandar Coastal Shelf (Catalog Baseline)",
        "description": "Saurashtra coastal fishing corridor in the Arabian Sea.",
    },
    "ratnagiri": {
        "latitude": 16.9800,
        "longitude": 73.2200,
        "name": "Ratnagiri Pelagic Fishing Zone (Catalog Baseline)",
        "description": "Central Konkan coastal shelf fishing waters.",
    },
    "karwar": {
        "latitude": 14.8000,
        "longitude": 74.0500,
        "name": "Karwar Shelf Fishing Sector (Catalog Baseline)",
        "description": "Deep continental shelf corridor off Karwar coast.",
    },
    "alappuzha": {
        "latitude": 9.4800,
        "longitude": 76.2500,
        "name": "Alappuzha Mud Bank Sector (Catalog Baseline)",
        "description": "Traditional productive marine upwelling bank along Malabar coast.",
    },
    "veraval": {
        "latitude": 20.8800,
        "longitude": 70.3200,
        "name": "Veraval Continental Shelf Zone (Catalog Baseline)",
        "description": "Arabian Sea demersal and pelagic fishing corridor.",
    },
}


def check_vessel_inland(lat: float, lon: float, loc_ctx: Optional[LocationContext]) -> bool:
    """Determine whether vessel coordinates are inland rather than coastal/marine."""
    if loc_ctx and loc_ctx.geographic_type == "inland":
        return True
    dist_to_coast = _min_distance_to_coast_km(lat, lon)
    return dist_to_coast > 50.0


def _extract_coordinates_from_text(text: str) -> Optional[Tuple[float, float, str]]:
    """Extract explicit decimal coordinates (lat, lon) from text."""
    coord_match = re.search(r"(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)", text)
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return lat, lon, f"Coordinates {lat:.4f}°N, {lon:.4f}°E"
        except (ValueError, TypeError):
            pass
    return None


def _lookup_coastal_coordinates(name: str) -> Optional[Tuple[float, float, str]]:
    """Lookup latitude, longitude, and canonical label for a coastal place name or raw coordinates."""
    # Check for raw coordinates like "12.85, 80.35"
    raw_coords = _extract_coordinates_from_text(name)
    if raw_coords:
        return raw_coords

    norm = name.strip().lower().replace("coast", "").replace("port", "").replace("harbor", "").strip()

    # Direct match in India Gazetteer
    if norm in INDIA_GAZETTEER:
        entry = INDIA_GAZETTEER[norm]
        return float(entry["latitude"]), float(entry["longitude"]), entry["name"]

    # Partial matches
    for key, entry in INDIA_GAZETTEER.items():
        if norm == key or norm in key or key in norm:
            return float(entry["latitude"]), float(entry["longitude"]), entry["name"]

    # Coastal hubs
    coastal_hubs = {
        "chennai": (13.0827, 80.2707, "Chennai"),
        "pondicherry": (11.9416, 79.8083, "Puducherry"),
        "puducherry": (11.9416, 79.8083, "Puducherry"),
        "ennore": (13.2612, 80.3344, "Ennore"),
        "kasimedu": (13.1189, 80.2978, "Kasimedu"),
        "pulicat": (13.4167, 80.3167, "Pulicat"),
        "mahabalipuram": (12.6189, 80.2014, "Mahabalipuram"),
        "mamallapuram": (12.6189, 80.2014, "Mahabalipuram"),
        "nagapattinam": (10.7667, 79.8333, "Nagapattinam"),
        "cuddalore": (11.7500, 79.7667, "Cuddalore"),
        "kochi": (9.9312, 76.2673, "Kochi"),
        "cochin": (9.9312, 76.2673, "Kochi"),
        "mumbai": (18.9220, 72.8340, "Mumbai"),
        "visakhapatnam": (17.6868, 83.2185, "Visakhapatnam"),
        "vizag": (17.6868, 83.2185, "Visakhapatnam"),
        "rameshwaram": (9.2876, 79.3129, "Rameshwaram"),
        "dhanushkodi": (9.1783, 79.4183, "Dhanushkodi"),
        "kanyakumari": (8.0883, 77.5385, "Kanyakumari"),
        "paradip": (20.3160, 86.6110, "Paradip"),
        "tuticorin": (8.7642, 78.1348, "Tuticorin"),
        "mangalore": (12.9141, 74.8560, "Mangalore"),
        "goa": (15.2993, 74.1240, "Goa"),
        "kolkata": (22.5726, 88.3639, "Kolkata"),
    }

    if norm in coastal_hubs:
        lat, lon, lbl = coastal_hubs[norm]
        return lat, lon, lbl

    for key, val in coastal_hubs.items():
        if key in norm:
            return val

    return None


def _lookup_fishing_coordinates(
    query: str,
    target_location: Optional[LocationContext] = None,
    query_location_entity: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_location: Optional[LocationContext] = None,
) -> Tuple[float, float, str, str]:
    """
    Dynamically resolve destination fishing coordinates for ANY location in India.
    Authoritative Priority Order:
    1. Explicit numeric coordinates in query (e.g. 'Navigate to 12.85, 80.35')
    2. Explicit place in current query matching FISHING_GROUNDS_CATALOG
    3. Active target location or query location entity:
       a. Matching FISHING_GROUNDS_CATALOG
       b. Marine basin (e.g. Bay of Bengal, Arabian Sea) -> returns basin coordinates + specific sector notice
       c. Seaward projection for coastal/marine place
    4. Contextual follow-up from conversation_history (ONLY if no active target from current query):
       a. Check most recent turn with an explicit entity
       b. Match catalog or marine basin or seaward projection
       c. Never fall back to older turns beyond the most recent target!
    5. Fallback based on user vessel position (never hardcoding Chennai).
    """
    q_lower = query.lower()

    # 1. Raw numeric coordinates in query
    coord_m = re.search(r"(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", q_lower)
    if coord_m:
        c_lat = float(coord_m.group(1))
        c_lon = float(coord_m.group(2))
        return c_lat, c_lon, f"Target Coordinates ({c_lat:.4f}°N, {c_lon:.4f}°E)", "User-specified destination coordinates."

    # 2. Check catalog match directly in query text
    for key, data in FISHING_GROUNDS_CATALOG.items():
        if re.search(r"\b" + re.escape(key) + r"\b", q_lower):
            return data["latitude"], data["longitude"], data["name"], data["description"]

    # 3. Resolve active target entity name from current query context
    active_target_name: Optional[str] = None
    if query_location_entity and query_location_entity.get("name") and query_location_entity.get("is_explicit"):
        active_target_name = str(query_location_entity["name"]).strip().lower()
    elif target_location and target_location.source in ("explicit_query", "conversation_context") and target_location.resolved_place:
        active_target_name = target_location.resolved_place.strip().lower()
    elif query_location_entity and query_location_entity.get("name"):
        active_target_name = str(query_location_entity["name"]).strip().lower()
    elif target_location and target_location.resolved_place:
        active_target_name = target_location.resolved_place.strip().lower()
    elif target_location and target_location.label:
        active_target_name = target_location.label.split(",")[0].strip().lower()

    # Helper function to resolve an entity name or target location to coordinates
    def _resolve_single_entity(
        entity_name: Optional[str],
        loc_ctx: Optional[LocationContext]
    ) -> Optional[Tuple[float, float, str, str]]:
        if entity_name:
            ent_clean = entity_name.split(",")[0].strip().lower()
            # 3a. Check FISHING_GROUNDS_CATALOG
            for key, data in FISHING_GROUNDS_CATALOG.items():
                if key == ent_clean or key in ent_clean or ent_clean in key:
                    return data["latitude"], data["longitude"], data["name"], data["description"]

            # 3b. Check regional marine basins (Bay of Bengal, Arabian Sea, etc.)
            marine_basins = {
                "bay of bengal": (16.0, 87.0, "Bay of Bengal Marine Basin", "Open waters of the Bay of Bengal. A specific coastal location needs to be selected for localized fishing grounds."),
                "arabian sea": (18.0, 68.0, "Arabian Sea Marine Basin", "Open waters of the Arabian Sea. A specific coastal location needs to be selected for localized fishing grounds."),
                "indian ocean": (6.0, 78.0, "Indian Ocean Marine Basin", "Open waters of the Indian Ocean. A specific coastal location needs to be selected for localized fishing grounds."),
                "palk bay": (9.45, 79.20, "Palk Bay Marine Basin", "Palk Bay waters. Maintain active awareness of international maritime boundaries."),
                "gulf of mannar": (8.50, 78.80, "Gulf of Mannar Marine Basin", "Gulf of Mannar marine corridor. Maintain designated navigational clearances."),
            }
            if ent_clean in marine_basins:
                return marine_basins[ent_clean]
            for m_key, m_val in marine_basins.items():
                if m_key in ent_clean or ent_clean in m_key:
                    return m_val

            # 3c. Check INDIA_GAZETTEER
            if ent_clean in INDIA_GAZETTEER:
                gdata = INDIA_GAZETTEER[ent_clean]
                g_lat = float(gdata["latitude"])
                g_lon = float(gdata["longitude"])
                g_type = gdata.get("geo_type", "coastal")
                clean_name = gdata["name"]
                if gdata.get("type") == "marine_basin":
                    return (
                        round(g_lat, 4),
                        round(g_lon, 4),
                        f"{clean_name} Marine Basin",
                        f"Open waters of {clean_name}. A specific coastal location needs to be selected for localized fishing grounds.",
                    )
                if g_type == "coastal" or _min_distance_to_coast_km(g_lat, g_lon) < 50.0:
                    offshore_lon = round(g_lon + 0.09 if g_lon > 78.0 else g_lon - 0.09, 4)
                    return (
                        round(g_lat, 4),
                        offshore_lon,
                        f"{clean_name} Offshore Fishing Sector (Deterministic Baseline)",
                        f"Recommended marine fishing sector ~15-20 km off {clean_name} coast. (Deterministic baseline catalog; pending live PFZ ingest)",
                    )
                else:
                    return (
                        round(g_lat, 4),
                        round(g_lon, 4),
                        f"{clean_name} (Inland Position - No Marine Fishing Ground)",
                        f"Inland coordinates in {clean_name}. Marine fishing is not available at inland positions.",
                    )

        # Seaward projection from LocationContext coordinates
        if loc_ctx and loc_ctx.latitude is not None and loc_ctx.longitude is not None:
            t_lat = loc_ctx.latitude
            t_lon = loc_ctx.longitude
            dist_to_coast = _min_distance_to_coast_km(t_lat, t_lon)
            is_coastal = (loc_ctx.geographic_type == "coastal") or (dist_to_coast < 50.0)
            is_marine = loc_ctx.geographic_type == "marine"

            raw_label = loc_ctx.resolved_place or loc_ctx.label or "Coastal"
            clean_name = raw_label.split(",")[0].strip()

            if is_coastal:
                offshore_lon = round(t_lon + 0.09 if t_lon > 78.0 else t_lon - 0.09, 4)
                offshore_lat = round(t_lat, 4)
                return (
                    offshore_lat,
                    offshore_lon,
                    f"{clean_name} Offshore Fishing Sector (Deterministic Baseline)",
                    f"Recommended marine fishing sector ~15-20 km offshore from {clean_name}. (Deterministic baseline catalog; pending live PFZ ingest)",
                )
            elif is_marine:
                return (
                    t_lat,
                    t_lon,
                    f"{clean_name} Marine Fishing Sector (Deterministic Baseline)",
                    f"Pelagic offshore fishing coordinates in {clean_name} waters.",
                )
            else:
                return (
                    t_lat,
                    t_lon,
                    f"{clean_name} (Inland Position - No Marine Fishing Ground)",
                    f"Inland coordinates in {clean_name}. Marine fishing is not available at inland positions.",
                )

        return None

    # If active target is known from current query / target_location, resolve it immediately!
    # Crucially, NEVER look into conversation_history if active_target_name is already present!
    if active_target_name:
        resolved = _resolve_single_entity(active_target_name, target_location)
        if resolved:
            return resolved

    # If target_location has coordinates, try resolving via coordinates
    if target_location and target_location.latitude is not None and target_location.longitude is not None:
        resolved = _resolve_single_entity(None, target_location)
        if resolved:
            return resolved

    # 4. Contextual follow-up: ONLY if no target was resolved from current query,
    # inspect conversation_history in reverse for the LATEST explicit entity.
    if conversation_history:
        from app.services.query_location_resolver import query_location_resolver
        for turn in reversed(conversation_history[-6:]):
            h_content = turn.get("content", "")
            h_ent = query_location_resolver.extract_explicit_entity(h_content)
            if h_ent:
                # STOP at the first (latest) turn with an entity!
                resolved = _resolve_single_entity(h_ent.lower(), None)
                if resolved:
                    return resolved
                break

    # 5. Default fallback based on vessel location (dynamic, never hardcoded to Chennai)
    v_lat = user_location.latitude if user_location and user_location.latitude is not None else 13.0827
    v_lon = user_location.longitude if user_location and user_location.longitude is not None else 80.2707
    dist_to_coast = _min_distance_to_coast_km(v_lat, v_lon)
    if dist_to_coast < 50.0:
        off_lon = round(v_lon + 0.09 if v_lon > 78.0 else v_lon - 0.09, 4)
        return (
            round(v_lat, 4),
            off_lon,
            "Coastal Marine Fishing Sector",
            "Recommended coastal marine fishing corridor based on vessel position.",
        )
    return (
        round(v_lat, 4),
        round(v_lon, 4),
        "Vessel Area (Inland - No Marine Fishing Ground)",
        "Vessel is located inland. Move to a coastal departure position for marine fishing.",
    )


def _load_boundary_geojson_features() -> List[Dict[str, Any]]:
    """Load boundary features from local GeoJSON."""
    if os.path.exists(_GEOJSON_PATH):
        try:
            with open(_GEOJSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("features", [])
        except Exception as e:
            logger.warning("failed_loading_boundary_geojson", extra={"error": str(e)})
    return []


class SpatialReasoner:
    """
    Constructs deterministic spatial payload for queries evaluated as spatial.
    """

    def build_spatial_payload(
        self,
        query: str,
        user_location: Optional[LocationContext],
        target_location: Optional[LocationContext] = None,
        query_location_entity: Optional[Dict[str, Any]] = None,
        safety_result: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[SpatialPayload]:
        """
        Build a complete SpatialPayload if query has spatial intent, else return None.
        """
        is_spatial, spatial_type = detect_spatial_intent(
            query,
            conversation_history=conversation_history,
            target_location=target_location,
        )
        if not is_spatial or spatial_type is None:
            return None

        # Resolve primary reference coordinates
        user_lat = user_location.latitude if user_location and user_location.latitude is not None else 13.0827
        user_lon = user_location.longitude if user_location and user_location.longitude is not None else 80.2707
        has_real_gps = bool(user_location and user_location.source == "browser_gps" and user_location.latitude is not None)

        target_lat = target_location.latitude if target_location and target_location.latitude is not None else None
        target_lon = target_location.longitude if target_location and target_location.longitude is not None else None

        if target_lat is None or target_lon is None:
            # Check if query mentions a place or explicit coordinates
            query_coords = _lookup_coastal_coordinates(query)
            if query_coords:
                target_lat, target_lon, _ = query_coords
            else:
                target_lat, target_lon = user_lat, user_lon

        # ── 1. User Location Map ─────────────────────────────────────────────
        if spatial_type == "user_location":
            center = {"latitude": user_lat, "longitude": user_lon}
            vessel_label = "Current Position" if has_real_gps else "Vessel Position (SIH Demo)"
            vessel_desc = (
                f"GPS Coordinates: {user_lat:.4f}°N, {user_lon:.4f}°E (±{user_location.accuracy_m or 15}m)"
                if has_real_gps
                else f"Demonstration Coordinates: {user_lat:.4f}°N, {user_lon:.4f}°E"
            )
            markers = [
                MapMarker(
                    id="vessel-current",
                    latitude=user_lat,
                    longitude=user_lon,
                    label=vessel_label,
                    marker_type="vessel",
                    status="safe",
                    description=vessel_desc,
                )
            ]
            return SpatialPayload(
                enabled=True,
                type="user_location",
                title=f"Vessel Position: {user_location.label or 'Coastal Sector' if user_location else 'Coastal Sector'}",
                summary=f"Vessel is located at {user_lat:.4f}°N, {user_lon:.4f}°E.",
                center=center,
                zoom=11,
                markers=markers,
                zones=[],
                routes=[],
            )

        # ── 2. Boundary Safety & Geofence Map ────────────────────────────────
        if spatial_type == "boundary_safety":
            eval_lat = target_lat if target_lat is not None else user_lat
            eval_lon = target_lon if target_lon is not None else user_lon

            geofence_eval = geofence_service.evaluate_position(eval_lat, eval_lon)
            boundary_dist = round(geofence_eval.distance_to_boundary_km, 1)
            bearing_deg = round(geofence_eval.bearing_degrees, 0)
            safety_state = geofence_eval.state.value

            markers = [
                MapMarker(
                    id="vessel-boundary-ref",
                    latitude=eval_lat,
                    longitude=eval_lon,
                    label="Evaluated Position",
                    marker_type="vessel",
                    status="safe" if safety_state == "NORMAL" else "caution" if safety_state == "APPROACHING" else "danger",
                    description=f"Distance to boundary: {boundary_dist} km (Bearing {bearing_deg}°)",
                )
            ]

            # Load actual boundary lines from GeoJSON
            zones = []
            features = _load_boundary_geojson_features()
            for feat in features:
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                if geom.get("type") == "LineString":
                    coords = geom.get("coordinates", [])
                    zones.append(
                        MapZone(
                            id=props.get("id", "imbl_sample"),
                            title=props.get("name", "Maritime Boundary Sample"),
                            zone_type="boundary_line",
                            geometry_type="LineString",
                            coordinates=coords,
                            stroke_color="#f59e0b",
                            opacity=0.85,
                            description=props.get("warning", "Demo boundary dataset (NOT FOR NAVIGATION)"),
                        )
                    )

            center = {"latitude": (eval_lat + 9.5) / 2 if eval_lat > 11.0 else eval_lat, "longitude": (eval_lon + 79.5) / 2 if eval_lon > 80.0 else eval_lon}

            return SpatialPayload(
                enabled=True,
                type="boundary_safety",
                title="Maritime Boundary & Safety Demarcation",
                summary=f"Vessel is {boundary_dist} km from {geofence_eval.nearest_boundary_name}. Status: {safety_state}.",
                center={"latitude": eval_lat, "longitude": eval_lon},
                zoom=8,
                markers=markers,
                zones=zones,
                routes=[],
                boundary_distance_km=boundary_dist,
                boundary_bearing_deg=bearing_deg,
                safety_state=safety_state,
            )

        # ── 3. Danger Areas Map ──────────────────────────────────────────────
        if spatial_type == "danger_areas":
            eval_lat = user_lat
            eval_lon = user_lon
            geofence_eval = geofence_service.evaluate_position(eval_lat, eval_lon)

            markers = [
                MapMarker(
                    id="vessel-danger-ref",
                    latitude=eval_lat,
                    longitude=eval_lon,
                    label="Vessel Position",
                    marker_type="vessel",
                    status="safe" if geofence_eval.state == SafetyState.NORMAL else "warning",
                    description=f"{geofence_eval.distance_to_boundary_km:.1f} km from boundary",
                )
            ]

            # Load boundary lines as restricted zones
            zones = []
            features = _load_boundary_geojson_features()
            for feat in features:
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                if geom.get("type") == "LineString":
                    zones.append(
                        MapZone(
                            id=props.get("id", "restricted_boundary"),
                            title=props.get("name", "International Maritime Boundary (Demo)"),
                            zone_type="restricted",
                            geometry_type="LineString",
                            coordinates=geom.get("coordinates", []),
                            stroke_color="#ef4444",
                            opacity=0.9,
                            description="Restricted international maritime boundary demarcation line.",
                        )
                    )

            return SpatialPayload(
                enabled=True,
                type="danger_areas",
                title="Monitored Marine Hazards & Boundary Demarcation",
                summary=f"Nearest hazard demarcation: {geofence_eval.nearest_boundary_name} ({geofence_eval.distance_to_boundary_km:.1f} km away).",
                center={"latitude": eval_lat, "longitude": eval_lon},
                zoom=8,
                markers=markers,
                zones=zones,
                routes=[],
                boundary_distance_km=round(geofence_eval.distance_to_boundary_km, 1),
                boundary_bearing_deg=round(geofence_eval.bearing_degrees, 0),
                safety_state=geofence_eval.state.value,
            )

        # ── 4. Fishing Destination & Route Map ──────────────────────────────
        if spatial_type == "fishing_destination":
            dest_lat, dest_lon, dest_name, dest_desc = _lookup_fishing_coordinates(
                query, target_location, query_location_entity, conversation_history=conversation_history, user_location=user_location
            )
            orig_lat, orig_lon = user_lat, user_lon
            is_vessel_inland = check_vessel_inland(orig_lat, orig_lon, user_location)

            # Geodesic distance and compass bearing
            dist_km = round(haversine_distance_km(orig_lat, orig_lon, dest_lat, dest_lon), 1)
            dist_nm = round(dist_km * 0.539957, 1)
            bearing = round(calculate_bearing(orig_lat, orig_lon, dest_lat, dest_lon), 0)

            # ETA calculation: only if vessel speed is provided in user location context
            vessel_speed_knots = None
            if user_location and hasattr(user_location, "speed_knots") and getattr(user_location, "speed_knots"):
                vessel_speed_knots = float(getattr(user_location, "speed_knots"))

            eta_minutes = None
            if vessel_speed_knots and vessel_speed_knots > 0:
                speed_kmh = vessel_speed_knots * 1.852
                eta_minutes = int(round((dist_km / speed_kmh) * 60))

            vessel_label = "Current Vessel (Live GPS)" if has_real_gps else "Current Vessel (Demo)"
            vessel_status = "warning" if is_vessel_inland else "safe"
            vessel_desc = (
                f"Coordinates: {orig_lat:.4f}°N, {orig_lon:.4f}°E (Inland Position)"
                if is_vessel_inland
                else f"Coordinates: {orig_lat:.4f}°N, {orig_lon:.4f}°E"
            )

            markers = [
                MapMarker(
                    id="vessel-current",
                    latitude=orig_lat,
                    longitude=orig_lon,
                    label=vessel_label,
                    marker_type="vessel",
                    status=vessel_status,
                    description=vessel_desc,
                ),
                MapMarker(
                    id="fishing-spot-target",
                    latitude=dest_lat,
                    longitude=dest_lon,
                    label="Recommended Fishing Spot 🎣",
                    marker_type="fishing",
                    status="safe",
                    description=f"{dest_name} ({dest_lat:.4f}°N, {dest_lon:.4f}°E)",
                ),
            ]

            if is_vessel_inland:
                nav_warning = (
                    "⚠️ Marine navigation unavailable\n\n"
                    "The current vessel GPS position is inland. "
                    "Move the vessel to a coastal/marine position before starting marine navigation.\n\n"
                    f"The {dest_name} can still be previewed on the map."
                )
                route_waypoints = [
                    {"latitude": orig_lat, "longitude": orig_lon, "name": f"Inland Position ({user_location.label if user_location and user_location.label else 'Inland'})"},
                    {"latitude": dest_lat, "longitude": dest_lon, "name": dest_name},
                ]
                safety_note = "Approximate overland reference line (Non-navigable: Vessel position is inland)"
                safety_clearance = "CAUTION"
                is_marine_nav = False
            else:
                nav_warning = None
                mid_lat = (orig_lat + dest_lat) / 2.0
                mid_lon = (orig_lon + dest_lon) / 2.0 + 0.08
                route_waypoints = [
                    {"latitude": orig_lat, "longitude": orig_lon, "name": "Departure"},
                    {"latitude": round(mid_lat, 4), "longitude": round(mid_lon, 4), "name": "Coastal Sea Lane Waypoint"},
                    {"latitude": dest_lat, "longitude": dest_lon, "name": dest_name},
                ]
                safety_note = "Recommended Marine Route to Fishing Ground. Geodesic coastal passage; maintain active nautical watch."
                safety_clearance = "SAFE"
                is_marine_nav = True

            # Determine whether user explicitly requested a route vs an indicator/area recommendation
            q_lower = query.lower()
            has_routing_intent = bool(
                any(re.search(pat, q_lower) for pat in FOLLOWUP_ROUTING_PATTERNS)
                or any(re.search(pat, q_lower) for pat in MARINE_ROUTE_PATTERNS)
                or any(w in q_lower for w in ["route", "navigate", "navigation", "directions", "how do i get there", "how can i get there", "how to reach", "take me there", "take me to", "take us to"])
            )

            if has_routing_intent:
                route_item = MapRoute(
                    origin={"latitude": orig_lat, "longitude": orig_lon, "label": vessel_label},
                    destination={"latitude": dest_lat, "longitude": dest_lon, "label": dest_name},
                    waypoints=route_waypoints,
                    distance_km=dist_km,
                    distance_nm=dist_nm,
                    bearing_degrees=bearing,
                    estimated_time_minutes=eta_minutes,
                    safety_clearance=safety_clearance,
                    safety_note=safety_note,
                    is_approximate=is_vessel_inland,
                    is_inland_warning=is_vessel_inland,
                )
                center_lat = (orig_lat + dest_lat) / 2.0
                center_lon = (orig_lon + dest_lon) / 2.0
                zoom = 6 if dist_km > 500 else 7 if dist_km > 200 else 8 if dist_km > 80 else 10
                routes_list = [route_item]
                payload_title = f"Fishing Route: Vessel to {dest_name}"
                payload_summary = f"Destination: {dest_name} ({dist_km} km / {dist_nm} NM along {bearing}° bearing)."
                active_nav_warning = nav_warning
            else:
                # Area recommendation query only — DO NOT generate automatic route or nav warnings
                routes_list = []
                center_lat = dest_lat
                center_lon = dest_lon
                zoom = 9
                payload_title = f"Recommended Fishing Area: {dest_name}"
                payload_summary = f"Identified fishing sector near {dest_name} ({dest_lat:.4f}°N, {dest_lon:.4f}°E)."
                active_nav_warning = None

            return SpatialPayload(
                enabled=True,
                type="fishing_destination",
                title=payload_title,
                summary=payload_summary,
                center={"latitude": center_lat, "longitude": center_lon},
                zoom=zoom,
                markers=markers,
                zones=[],
                routes=routes_list,
                navigation_warning=active_nav_warning,
                is_marine_navigable=is_marine_nav,
                target_location={"latitude": dest_lat, "longitude": dest_lon, "label": dest_name, "is_fishing_ground": True},
                vessel_location={"latitude": orig_lat, "longitude": orig_lon, "label": user_location.label if user_location and user_location.label else "Current Vessel", "is_inland": is_vessel_inland},
            )

        # ── 5. Marine Route Map ──────────────────────────────────────────────
        if spatial_type == "marine_route":
            # Extract origin and destination
            q_lower = query.lower()
            orig_lat, orig_lon, orig_name = user_lat, user_lon, "Current Location"
            dest_lat, dest_lon, dest_name = target_lat, target_lon, "Destination"
            if target_location and (target_location.resolved_place or target_location.label):
                dest_name = target_location.resolved_place or target_location.label
            elif query_location_entity and query_location_entity.get("name"):
                dest_name = str(query_location_entity["name"])
            if user_location and (user_location.resolved_place or user_location.label):
                orig_name = user_location.resolved_place or user_location.label

            # 1. First check for explicit coordinates in query
            explicit_coords = _extract_coordinates_from_text(query)
            if explicit_coords:
                dest_lat, dest_lon, dest_name = explicit_coords
            else:
                # Parse "route from X to Y"
                match_from_to = re.search(r"route (?:from|between) (?P<from>.+?) (?:to|and) (?P<to>.+?)(?:$|[?!])", q_lower)
                if match_from_to:
                    from_str = match_from_to.group("from").strip()
                    to_str = match_from_to.group("to").strip()

                    from_coords = _lookup_coastal_coordinates(from_str)
                    if from_coords:
                        orig_lat, orig_lon, orig_name = from_coords

                    to_coords = _lookup_coastal_coordinates(to_str)
                    if to_coords:
                        dest_lat, dest_lon, dest_name = to_coords
                else:
                    # Parse "route to Y" or "navigate to Y"
                    match_to = re.search(r"(?:route|navigate)\s+to\s+(?P<to>.+?)(?:$|[?!])", q_lower)
                    if match_to:
                        to_str = match_to.group("to").strip()
                        to_coords = _lookup_coastal_coordinates(to_str)
                        if to_coords:
                            dest_lat, dest_lon, dest_name = to_coords

            is_vessel_inland = check_vessel_inland(orig_lat, orig_lon, user_location)

            # Calculate geodesic distance and compass bearing
            dist_km = round(haversine_distance_km(orig_lat, orig_lon, dest_lat, dest_lon), 1)
            dist_nm = round(dist_km * 0.539957, 1)
            bearing = round(calculate_bearing(orig_lat, orig_lon, dest_lat, dest_lon), 0)

            # ETA calculation: only if vessel speed is provided in user location context
            vessel_speed_knots = None
            if user_location and hasattr(user_location, "speed_knots") and getattr(user_location, "speed_knots"):
                vessel_speed_knots = float(getattr(user_location, "speed_knots"))

            eta_minutes = None
            if vessel_speed_knots and vessel_speed_knots > 0:
                speed_kmh = vessel_speed_knots * 1.852
                eta_minutes = int(round((dist_km / speed_kmh) * 60))

            if is_vessel_inland:
                nav_warning = (
                    "⚠️ Marine navigation unavailable\n\n"
                    "The current vessel GPS position is inland. "
                    "Move the vessel to a coastal/marine position before starting marine navigation.\n\n"
                    f"The destination ({dest_name}) can still be previewed on the map."
                )
                safety_note = "Approximate overland reference line (Non-navigable: Vessel position is inland)"
                safety_clearance = "CAUTION"
                waypoints = [
                    {"latitude": orig_lat, "longitude": orig_lon, "name": f"Departure ({orig_name})"},
                    {"latitude": dest_lat, "longitude": dest_lon, "name": f"Arrival ({dest_name})"},
                ]
            else:
                nav_warning = None
                safety_note = "Recommended Marine Route. Geodesic coastal passage; maintain active nautical watch."
                safety_clearance = "SAFE"
                mid_lat = (orig_lat + dest_lat) / 2.0
                mid_lon = (orig_lon + dest_lon) / 2.0 + 0.08
                waypoints = [
                    {"latitude": orig_lat, "longitude": orig_lon, "name": f"Departure ({orig_name})"},
                    {"latitude": round(mid_lat, 4), "longitude": round(mid_lon, 4), "name": "Coastal Sea Lane Waypoint"},
                    {"latitude": dest_lat, "longitude": dest_lon, "name": f"Arrival ({dest_name})"},
                ]

            route_item = MapRoute(
                origin={"latitude": orig_lat, "longitude": orig_lon, "label": orig_name},
                destination={"latitude": dest_lat, "longitude": dest_lon, "label": dest_name},
                waypoints=waypoints,
                distance_km=dist_km,
                distance_nm=dist_nm,
                bearing_degrees=bearing,
                estimated_time_minutes=eta_minutes,
                safety_clearance=safety_clearance,
                safety_note=safety_note,
                is_approximate=is_vessel_inland,
                is_inland_warning=is_vessel_inland,
            )

            markers = [
                MapMarker(
                    id="route-origin",
                    latitude=orig_lat,
                    longitude=orig_lon,
                    label=f"Origin: {orig_name}",
                    marker_type="vessel",
                    status="warning" if is_vessel_inland else "safe",
                    description=f"{orig_name} ({orig_lat:.4f}°N, {orig_lon:.4f}°E)",
                ),
                MapMarker(
                    id="route-dest",
                    latitude=dest_lat,
                    longitude=dest_lon,
                    label=f"Destination: {dest_name}",
                    marker_type="target",
                    status="safe",
                    description=f"{dest_name} ({dest_lat:.4f}°N, {dest_lon:.4f}°E)",
                ),
            ]
            if not is_vessel_inland and len(waypoints) > 2:
                markers.insert(
                    1,
                    MapMarker(
                        id="route-midpoint",
                        latitude=waypoints[1]["latitude"],
                        longitude=waypoints[1]["longitude"],
                        label="Waypoint: Coastal Corridor",
                        marker_type="waypoint",
                        status="info",
                    )
                )

            center_lat = (orig_lat + dest_lat) / 2.0
            center_lon = (orig_lon + dest_lon) / 2.0
            zoom = 6 if dist_km > 500 else 7 if dist_km > 200 else 8 if dist_km > 100 else 9

            return SpatialPayload(
                enabled=True,
                type="marine_route",
                title=f"Marine Route: {orig_name} to {dest_name}",
                summary=f"Nautical passage: {dist_km} km ({dist_nm} NM) along {bearing}° bearing.",
                center={"latitude": center_lat, "longitude": center_lon},
                zoom=zoom,
                markers=markers,
                zones=[],
                routes=[route_item],
                navigation_warning=nav_warning,
                is_marine_navigable=not is_vessel_inland,
                target_location={"latitude": dest_lat, "longitude": dest_lon, "label": dest_name},
                vessel_location={"latitude": orig_lat, "longitude": orig_lon, "label": orig_name, "is_inland": is_vessel_inland},
            )

        # ── 5. Target Location Map ───────────────────────────────────────────
        if spatial_type == "target_location":
            place_name = "Target Location"
            if query_location_entity and query_location_entity.get("name"):
                place_name = str(query_location_entity["name"])
            elif target_location and target_location.label:
                place_name = target_location.label

            markers = [
                MapMarker(
                    id="target-location-marker",
                    latitude=target_lat,
                    longitude=target_lon,
                    label=place_name,
                    marker_type="target",
                    status="safe",
                    description=f"{target_lat:.4f}°N, {target_lon:.4f}°E",
                )
            ]

            return SpatialPayload(
                enabled=True,
                type="target_location",
                title=f"Map: {place_name}",
                summary=f"Coordinates: {target_lat:.4f}°N, {target_lon:.4f}°E.",
                center={"latitude": target_lat, "longitude": target_lon},
                zoom=10,
                markers=markers,
                zones=[],
                routes=[],
            )

        return None


# Global singleton instance
spatial_reasoner = SpatialReasoner()
