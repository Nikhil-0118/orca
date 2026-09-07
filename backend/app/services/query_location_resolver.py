"""
Query Location Resolver for ORCA.

Distinguishes between:
1. User Current Location (Client device GPS):
   - "my location", "where am I", "near me", "nearest ocean near me", "temperature here"
2. Explicit Query Location:
   - A location explicitly queried by the user:
     "Gujarat", "Mumbai", "Chennai", "Dwarka", "Ahmedabad", "Odisha", "Surat", "Kolkata",
     "Goa", "Kochi", "Visakhapatnam", "Kerala", "Andaman & Nicobar", "Lakshadweep",
     "Bay of Bengal", "Arabian Sea", "Delhi", "Kanpur", etc.

Authoritative Rules:
1. If the user explicitly mentions a location, that location becomes the query target.
2. The user's device GPS coordinates are NEVER overwritten or replaced by the query target.
3. State entities (e.g. Gujarat) are recognized as regional geometries/coastal states with
   extensive coastlines, not collapsed into arbitrary single points.
4. City entities (e.g. Dwarka, Ahmedabad, Kanpur) are resolved specifically.
5. Works dynamically across all of India via a comprehensive built-in gazetteer
   and OpenStreetMap Nominatim forward search fallback.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx
from pydantic import BaseModel, Field

from app.schemas.query import LocationContext, GeographicType

logger = logging.getLogger("orca.services.query_location_resolver")


class QueryLocationResult(BaseModel):
    """Result of query location resolution."""
    query_entity_name: Optional[str] = Field(None, description="Extracted geographic entity name")
    location_source: str = Field("browser_gps", description="explicit_query | browser_gps | conversation_context | unavailable")
    entity_type: str = Field("device_gps", description="coastal_state | inland_state | coastal_city | inland_city | marine_basin | island_territory | device_gps")
    is_explicit: bool = Field(False, description="True if location was explicitly specified in query")
    target_location: LocationContext = Field(..., description="Canonical target LocationContext for query evaluation")
    state_name: Optional[str] = Field(None, description="Associated state or union territory")
    coastline_length_km: Optional[float] = Field(None, description="Approximate coastline length for coastal states")
    bordering_oceans: List[str] = Field(default_factory=list, description="Oceans or seas directly bordering this entity")
    notes: Optional[str] = Field(None, description="Regional or approximation notes")


# ── COMPREHENSIVE INDIA GAZETTEER ─────────────────────────────────────────────
# Structured dataset of Indian States, UTs, Coastal Cities, Inland Cities, and Marine Basins.

INDIA_GAZETTEER: Dict[str, Dict[str, Any]] = {
    # ── Coastal States & Union Territories ──
    "gujarat": {
        "name": "Gujarat",
        "type": "coastal_state",
        "latitude": 22.2587,
        "longitude": 71.1924,
        "state": "Gujarat",
        "geo_type": "coastal",
        "coastline_km": 1600.0,
        "bordering_oceans": ["Arabian Sea", "Gulf of Kutch", "Gulf of Khambhat"],
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Gujarat Saurashtra / Kutch Coast",
        "is_state": True,
        "description": "Extensive maritime state on India's western coast with approximately 1,600 km of coastline bordering the Arabian Sea.",
    },
    "maharashtra": {
        "name": "Maharashtra",
        "type": "coastal_state",
        "latitude": 19.7515,
        "longitude": 75.7139,
        "state": "Maharashtra",
        "geo_type": "coastal",
        "coastline_km": 720.0,
        "bordering_oceans": ["Arabian Sea"],
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Konkan Coast",
        "is_state": True,
        "description": "Peninsular state with approximately 720 km of coastline along the Arabian Sea (Konkan coast).",
    },
    "goa": {
        "name": "Goa",
        "type": "coastal_state",
        "latitude": 15.2993,
        "longitude": 74.1240,
        "state": "Goa",
        "geo_type": "coastal",
        "coastline_km": 105.0,
        "bordering_oceans": ["Arabian Sea"],
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Goa / Konkan Coast",
        "is_state": True,
        "description": "Coastal state on India's southwestern coast with approximately 105 km of coastline along the Arabian Sea.",
    },
    "karnataka": {
        "name": "Karnataka",
        "type": "coastal_state",
        "latitude": 15.3173,
        "longitude": 75.7139,
        "state": "Karnataka",
        "geo_type": "coastal",
        "coastline_km": 320.0,
        "bordering_oceans": ["Arabian Sea"],
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Karavali / Karnataka Coast",
        "is_state": True,
        "description": "Peninsular state with approximately 320 km of coastline along the Arabian Sea (Karavali coast).",
    },
    "kerala": {
        "name": "Kerala",
        "type": "coastal_state",
        "latitude": 10.8505,
        "longitude": 76.2711,
        "state": "Kerala",
        "geo_type": "coastal",
        "coastline_km": 580.0,
        "bordering_oceans": ["Arabian Sea"],
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Malabar Coast",
        "is_state": True,
        "description": "Southwestern coastal state with approximately 580 km of coastline along the Arabian Sea (Malabar coast).",
    },
    "tamil nadu": {
        "name": "Tamil Nadu",
        "type": "coastal_state",
        "latitude": 11.1271,
        "longitude": 78.6569,
        "state": "Tamil Nadu",
        "geo_type": "coastal",
        "coastline_km": 1076.0,
        "bordering_oceans": ["Bay of Bengal", "Indian Ocean", "Gulf of Mannar", "Palk Bay"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Coromandel Coast",
        "is_state": True,
        "description": "Southeastern coastal state with approximately 1,076 km of coastline along the Bay of Bengal, Palk Strait, and Indian Ocean.",
    },
    "tamilnadu": {
        "name": "Tamil Nadu",
        "type": "coastal_state",
        "latitude": 11.1271,
        "longitude": 78.6569,
        "state": "Tamil Nadu",
        "geo_type": "coastal",
        "coastline_km": 1076.0,
        "bordering_oceans": ["Bay of Bengal", "Indian Ocean", "Gulf of Mannar", "Palk Bay"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Coromandel Coast",
        "is_state": True,
        "description": "Southeastern coastal state with approximately 1,076 km of coastline along the Bay of Bengal.",
    },
    "andhra pradesh": {
        "name": "Andhra Pradesh",
        "type": "coastal_state",
        "latitude": 15.9129,
        "longitude": 79.7400,
        "state": "Andhra Pradesh",
        "geo_type": "coastal",
        "coastline_km": 974.0,
        "bordering_oceans": ["Bay of Bengal"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Andhra Coast",
        "is_state": True,
        "description": "Eastern peninsular state with approximately 974 km of coastline along the Bay of Bengal.",
    },
    "odisha": {
        "name": "Odisha",
        "type": "coastal_state",
        "latitude": 20.9517,
        "longitude": 85.0985,
        "state": "Odisha",
        "geo_type": "coastal",
        "coastline_km": 480.0,
        "bordering_oceans": ["Bay of Bengal"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Odisha Coast",
        "is_state": True,
        "description": "Eastern maritime state with approximately 480 km of coastline along the Bay of Bengal.",
    },
    "orissa": {
        "name": "Odisha",
        "type": "coastal_state",
        "latitude": 20.9517,
        "longitude": 85.0985,
        "state": "Odisha",
        "geo_type": "coastal",
        "coastline_km": 480.0,
        "bordering_oceans": ["Bay of Bengal"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Odisha Coast",
        "is_state": True,
        "description": "Eastern maritime state with approximately 480 km of coastline along the Bay of Bengal.",
    },
    "west bengal": {
        "name": "West Bengal",
        "type": "coastal_state",
        "latitude": 22.9868,
        "longitude": 87.8550,
        "state": "West Bengal",
        "geo_type": "coastal",
        "coastline_km": 157.5,
        "bordering_oceans": ["Bay of Bengal"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Bengal / Sundarbans Coast",
        "is_state": True,
        "description": "Eastern maritime state bordering the northern head of the Bay of Bengal and Sundarbans delta.",
    },
    "puducherry": {
        "name": "Puducherry",
        "type": "coastal_state",
        "latitude": 11.9416,
        "longitude": 79.8083,
        "state": "Puducherry",
        "geo_type": "coastal",
        "coastline_km": 45.0,
        "bordering_oceans": ["Bay of Bengal", "Arabian Sea"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Coromandel Coast",
        "is_state": True,
        "description": "Union territory with coastal enclaves on the Bay of Bengal and Arabian Sea.",
    },
    "pondicherry": {
        "name": "Puducherry",
        "type": "coastal_state",
        "latitude": 11.9416,
        "longitude": 79.8083,
        "state": "Puducherry",
        "geo_type": "coastal",
        "coastline_km": 45.0,
        "bordering_oceans": ["Bay of Bengal"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Coromandel Coast",
        "is_state": True,
        "description": "Union territory with coastal enclaves on the Bay of Bengal.",
    },
    "andaman and nicobar": {
        "name": "Andaman & Nicobar Islands",
        "type": "island_territory",
        "latitude": 11.6670,
        "longitude": 92.7350,
        "state": "Andaman and Nicobar Islands",
        "geo_type": "coastal",
        "coastline_km": 1912.0,
        "bordering_oceans": ["Bay of Bengal", "Andaman Sea"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Andaman Sea Coast",
        "is_state": False,
        "description": "Archipelago in the Bay of Bengal and Andaman Sea with approximately 1,912 km of coastline.",
    },
    "andaman": {
        "name": "Andaman & Nicobar Islands",
        "type": "island_territory",
        "latitude": 11.6670,
        "longitude": 92.7350,
        "state": "Andaman and Nicobar Islands",
        "geo_type": "coastal",
        "coastline_km": 1912.0,
        "bordering_oceans": ["Bay of Bengal", "Andaman Sea"],
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Andaman Sea Coast",
        "is_state": False,
        "description": "Archipelago in the Bay of Bengal and Andaman Sea.",
    },
    "lakshadweep": {
        "name": "Lakshadweep",
        "type": "island_territory",
        "latitude": 10.5667,
        "longitude": 72.6417,
        "state": "Lakshadweep",
        "geo_type": "coastal",
        "coastline_km": 132.0,
        "bordering_oceans": ["Arabian Sea"],
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Lakshadweep Waters",
        "is_state": False,
        "description": "Archipelago of coral atolls in the Arabian Sea with approximately 132 km of coastline.",
    },

    # ── Inland States & UTs ──
    "uttar pradesh": {
        "name": "Uttar Pradesh",
        "type": "inland_state",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "state": "Uttar Pradesh",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Bay of Bengal",
        "is_state": True,
        "description": "Inland northern state situated in the fertile Gangetic Plain.",
    },
    "delhi": {
        "name": "Delhi",
        "type": "inland_city",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "state": "Delhi",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Arabian Sea",
        "is_state": False,
        "description": "National Capital Territory in inland Northern India.",
    },
    "new delhi": {
        "name": "New Delhi",
        "type": "inland_city",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "state": "Delhi",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Arabian Sea",
        "is_state": False,
        "description": "Capital of India in inland Northern India.",
    },
    "madhya pradesh": {
        "name": "Madhya Pradesh",
        "type": "inland_state",
        "latitude": 22.9734,
        "longitude": 78.6569,
        "state": "Madhya Pradesh",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Arabian Sea",
        "is_state": True,
        "description": "Inland central state of India.",
    },
    "rajasthan": {
        "name": "Rajasthan",
        "type": "inland_state",
        "latitude": 27.0238,
        "longitude": 74.2179,
        "state": "Rajasthan",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Arabian Sea",
        "is_state": True,
        "description": "Inland northwestern state of India.",
    },
    "bihar": {
        "name": "Bihar",
        "type": "inland_state",
        "latitude": 25.0961,
        "longitude": 85.3131,
        "state": "Bihar",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Bay of Bengal",
        "is_state": True,
        "description": "Inland eastern state situated along the Ganges river basin.",
    },
    "punjab": {
        "name": "Punjab",
        "type": "inland_state",
        "latitude": 31.1471,
        "longitude": 75.3412,
        "state": "Punjab",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Arabian Sea",
        "is_state": True,
        "description": "Inland northwestern state of India.",
    },
    "haryana": {
        "name": "Haryana",
        "type": "inland_state",
        "latitude": 29.0588,
        "longitude": 76.0856,
        "state": "Haryana",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Arabian Sea",
        "is_state": True,
        "description": "Inland northern state surrounding the National Capital Region.",
    },
    "telangana": {
        "name": "Telangana",
        "type": "inland_state",
        "latitude": 18.1124,
        "longitude": 79.0193,
        "state": "Telangana",
        "geo_type": "inland",
        "coastline_km": 0.0,
        "bordering_oceans": [],
        "nearest_ocean": "Bay of Bengal",
        "is_state": True,
        "description": "Inland southern plateau state of India.",
    },

    # ── Major Coastal Cities & Ports ──
    "dwarka": {
        "name": "Dwarka",
        "type": "coastal_city",
        "latitude": 22.2400,
        "longitude": 68.9685,
        "state": "Gujarat",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Dwarka / Saurashtra Coast",
        "description": "Ancient coastal city located at the western tip of the Saurashtra peninsula directly on the Arabian Sea.",
    },
    "mumbai": {
        "name": "Mumbai",
        "type": "coastal_city",
        "latitude": 18.9220,
        "longitude": 72.8340,
        "state": "Maharashtra",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Mumbai / Konkan Coast",
        "description": "Major maritime metropolis and port city situated on the Konkan coast of the Arabian Sea.",
    },
    "bombay": {
        "name": "Mumbai",
        "type": "coastal_city",
        "latitude": 18.9220,
        "longitude": 72.8340,
        "state": "Maharashtra",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Mumbai / Konkan Coast",
        "description": "Major maritime metropolis on the Arabian Sea.",
    },
    "chennai": {
        "name": "Chennai",
        "type": "coastal_city",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "state": "Tamil Nadu",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Chennai / Coromandel Coast",
        "description": "Major port metropolis situated directly on the Coromandel coast of the Bay of Bengal.",
    },
    "madras": {
        "name": "Chennai",
        "type": "coastal_city",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "state": "Tamil Nadu",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Chennai / Coromandel Coast",
        "description": "Major port city situated on the Coromandel coast of the Bay of Bengal.",
    },
    "kochi": {
        "name": "Kochi",
        "type": "coastal_city",
        "latitude": 9.9312,
        "longitude": 76.2673,
        "state": "Kerala",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Kochi / Malabar Coast",
        "description": "Major port city situated on the Malabar coast of the Arabian Sea.",
    },
    "cochin": {
        "name": "Kochi",
        "type": "coastal_city",
        "latitude": 9.9312,
        "longitude": 76.2673,
        "state": "Kerala",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Kochi / Malabar Coast",
        "description": "Major port city situated on the Malabar coast of the Arabian Sea.",
    },
    "visakhapatnam": {
        "name": "Visakhapatnam",
        "type": "coastal_city",
        "latitude": 17.6868,
        "longitude": 83.2185,
        "state": "Andhra Pradesh",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Visakhapatnam / Andhra Coast",
        "description": "Major port city and naval command center on the Bay of Bengal.",
    },
    "vizag": {
        "name": "Visakhapatnam",
        "type": "coastal_city",
        "latitude": 17.6868,
        "longitude": 83.2185,
        "state": "Andhra Pradesh",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Visakhapatnam / Andhra Coast",
        "description": "Major port city situated on the Bay of Bengal.",
    },
    "kolkata": {
        "name": "Kolkata",
        "type": "coastal_city",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "state": "West Bengal",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Digha / Bengal Shelf Waters",
        "description": "Major riverine and maritime gateway port near the northern head of the Bay of Bengal.",
    },
    "calcutta": {
        "name": "Kolkata",
        "type": "coastal_city",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "state": "West Bengal",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Digha / Bengal Shelf Waters",
        "description": "Major commercial port gateway near the Bay of Bengal.",
    },
    "surat": {
        "name": "Surat",
        "type": "coastal_city",
        "latitude": 21.1702,
        "longitude": 72.8311,
        "state": "Gujarat",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Surat / Gulf of Khambhat Coast",
        "description": "Coastal port and commercial hub situated near the mouth of the Tapti river at the Gulf of Khambhat (Arabian Sea).",
    },
    "porbandar": {
        "name": "Porbandar",
        "type": "coastal_city",
        "latitude": 21.6417,
        "longitude": 69.6293,
        "state": "Gujarat",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Porbandar / Saurashtra Coast",
        "description": "Coastal port city situated on the Arabian Sea in Gujarat.",
    },
    "mangalore": {
        "name": "Mangalore",
        "type": "coastal_city",
        "latitude": 12.9141,
        "longitude": 74.8560,
        "state": "Karnataka",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Mangalore / Karnataka Coast",
        "description": "Major port city located on the Arabian Sea in Karnataka.",
    },
    "mangaluru": {
        "name": "Mangalore",
        "type": "coastal_city",
        "latitude": 12.9141,
        "longitude": 74.8560,
        "state": "Karnataka",
        "geo_type": "coastal",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Mangalore / Karnataka Coast",
        "description": "Major port city located on the Arabian Sea in Karnataka.",
    },
    "puri": {
        "name": "Puri",
        "type": "coastal_city",
        "latitude": 19.8135,
        "longitude": 85.8312,
        "state": "Odisha",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Puri / Odisha Coast",
        "description": "Coastal pilgrimage city located directly on the Bay of Bengal.",
    },
    "kanyakumari": {
        "name": "Kanyakumari",
        "type": "coastal_city",
        "latitude": 8.0883,
        "longitude": 77.5385,
        "state": "Tamil Nadu",
        "geo_type": "coastal",
        "nearest_ocean": "Indian Ocean",
        "nearest_coast_sector": "Kanyakumari / Indian Ocean Confluence",
        "description": "Southernmost tip of the Indian subcontinent where the Arabian Sea, Bay of Bengal, and Indian Ocean converge.",
    },
    "port blair": {
        "name": "Port Blair",
        "type": "coastal_city",
        "latitude": 11.6234,
        "longitude": 92.7265,
        "state": "Andaman and Nicobar Islands",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Port Blair / Andaman Sea Coast",
        "description": "Capital city of Andaman & Nicobar Islands on the Andaman Sea and Bay of Bengal.",
    },
    "paradip": {
        "name": "Paradip",
        "type": "coastal_city",
        "latitude": 20.3160,
        "longitude": 86.6110,
        "state": "Odisha",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Paradip / Odisha Coast",
        "description": "Major deep-water sea port city on the Bay of Bengal coast in Odisha.",
    },
    "paradeep": {
        "name": "Paradip",
        "type": "coastal_city",
        "latitude": 20.3160,
        "longitude": 86.6110,
        "state": "Odisha",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Paradip / Odisha Coast",
        "description": "Major deep-water sea port city on the Bay of Bengal coast in Odisha.",
    },
    "tuticorin": {
        "name": "Tuticorin",
        "type": "coastal_city",
        "latitude": 8.7642,
        "longitude": 78.1348,
        "state": "Tamil Nadu",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Gulf of Mannar Coast",
        "description": "Historic major maritime port and pearling/fishing hub on the Gulf of Mannar in Tamil Nadu.",
    },
    "thoothukudi": {
        "name": "Tuticorin",
        "type": "coastal_city",
        "latitude": 8.7642,
        "longitude": 78.1348,
        "state": "Tamil Nadu",
        "geo_type": "coastal",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Gulf of Mannar Coast",
        "description": "Historic major maritime port and fishing hub on the Gulf of Mannar in Tamil Nadu.",
    },

    # ── Major Inland Cities ──
    "ahmedabad": {
        "name": "Ahmedabad",
        "type": "inland_city",
        "latitude": 23.0225,
        "longitude": 72.5714,
        "state": "Gujarat",
        "geo_type": "inland",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Gulf of Khambhat (Arabian Sea)",
        "description": "Major inland metropolis in central Gujarat, situated approximately 75-80 km north of the Gulf of Khambhat (Arabian Sea).",
    },
    "kanpur": {
        "name": "Kanpur",
        "type": "inland_city",
        "latitude": 26.4499,
        "longitude": 80.3319,
        "state": "Uttar Pradesh",
        "geo_type": "inland",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Balasore / Odisha Coast",
        "description": "Major industrial city in inland northern India on the banks of the Ganges river in Uttar Pradesh.",
    },
    "lucknow": {
        "name": "Lucknow",
        "type": "inland_city",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "state": "Uttar Pradesh",
        "geo_type": "inland",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Balasore / Odisha Coast",
        "description": "Capital city of Uttar Pradesh in inland northern India.",
    },
    "bengaluru": {
        "name": "Bengaluru",
        "type": "inland_city",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "state": "Karnataka",
        "geo_type": "inland",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Chennai / Coromandel Coast",
        "description": "Inland peninsular metropolis on the Deccan Plateau.",
    },
    "bangalore": {
        "name": "Bengaluru",
        "type": "inland_city",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "state": "Karnataka",
        "geo_type": "inland",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Chennai / Coromandel Coast",
        "description": "Inland peninsular metropolis on the Deccan Plateau.",
    },
    "hyderabad": {
        "name": "Hyderabad",
        "type": "inland_city",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "state": "Telangana",
        "geo_type": "inland",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Machilipatnam / Andhra Coast",
        "description": "Inland southern metropolis on the Deccan Plateau.",
    },
    "jaipur": {
        "name": "Jaipur",
        "type": "inland_city",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "state": "Rajasthan",
        "geo_type": "inland",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Gulf of Kutch (Arabian Sea)",
        "description": "Capital of Rajasthan in inland northwestern India.",
    },
    "pune": {
        "name": "Pune",
        "type": "inland_city",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "state": "Maharashtra",
        "geo_type": "inland",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Murud / Konkan Coast",
        "description": "Inland city in western Maharashtra, situated approximately 100 km east of the Konkan coast.",
    },

    # ── Major Marine Water Bodies ──
    "arabian sea": {
        "name": "Arabian Sea",
        "type": "marine_basin",
        "latitude": 18.0,
        "longitude": 68.0,
        "state": None,
        "geo_type": "marine",
        "nearest_ocean": "Arabian Sea",
        "nearest_coast_sector": "Open Arabian Sea Waters",
        "description": "Major oceanic basin of the northern Indian Ocean bounded by India to the east.",
    },
    "bay of bengal": {
        "name": "Bay of Bengal",
        "type": "marine_basin",
        "latitude": 16.0,
        "longitude": 87.0,
        "state": None,
        "geo_type": "marine",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Open Bay of Bengal Waters",
        "description": "Major oceanic basin forming the northeastern part of the Indian Ocean bounded by India to the west.",
    },
    "indian ocean": {
        "name": "Indian Ocean",
        "type": "marine_basin",
        "latitude": 6.0,
        "longitude": 78.0,
        "state": None,
        "geo_type": "marine",
        "nearest_ocean": "Indian Ocean",
        "nearest_coast_sector": "Equatorial Indian Ocean Waters",
        "description": "The oceanic body south of the Indian subcontinent.",
    },
    "palk bay": {
        "name": "Palk Bay",
        "type": "marine_basin",
        "latitude": 9.45,
        "longitude": 79.20,
        "state": "Tamil Nadu",
        "geo_type": "marine",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Palk Bay / IMBL Waters",
        "description": "Semi-enclosed shallow water body between southeastern India and Sri Lanka.",
    },
    "palk strait": {
        "name": "Palk Strait",
        "type": "marine_basin",
        "latitude": 9.80,
        "longitude": 79.50,
        "state": "Tamil Nadu",
        "geo_type": "marine",
        "nearest_ocean": "Bay of Bengal",
        "nearest_coast_sector": "Palk Strait Sector",
        "description": "Strait between Tamil Nadu and Jaffna, connecting the Bay of Bengal with Palk Bay.",
    },
}

# ── DEICTIC PHRASES (Refers to Live Device GPS) ───────────────────────────────
DEICTIC_GPS_SIGNALS = [
    "my location", "my current location", "where am i", "where am i now",
    "my position", "what is my location", "my coordinates", "where i am",
    "near me", "nearby me", "around me", "close to me",
    "here", "around here", "from here", "this area",
    "my boat", "my vessel", "our location",
]


class QueryLocationResolver:
    """
    India-wide query location resolution engine.
    Extracts geographic entities, resolves coordinates and spatial types,
    and preserves user GPS separately from explicit query targets.
    """

    def __init__(self, timeout_sec: float = 3.0):
        self.timeout_sec = timeout_sec
        self._osm_cache: Dict[str, Dict[str, Any]] = {}
        self._user_agent = "ORCA-Marine-Location-Resolver/1.0 (sih-isro-prototype)"

    def _normalize(self, text: str) -> str:
        """Clean and normalize query string for entity matching."""
        return " " + re.sub(r"[^\w\s]", " ", text.lower()) + " "

    def extract_explicit_entity(self, query: str) -> Optional[str]:
        """
        Extract explicitly mentioned Indian place/state/marine entity from query text.
        Handles patterns like:
        - "nearest ocean to Gujarat"
        - "weather in Mumbai"
        - "temperature in Gujarat"
        - "ocean near Dwarka"
        - "sea temperature near Gujarat"
        - "I am in Kanpur, what is the weather in Mumbai?"
        """
        q_norm = self._normalize(query)

        # 1. Handle mixed query: "I am in Kanpur, what is the weather in Mumbai?"
        # Look for target location in the question clause after user location clause
        mixed_match = re.search(r"(?:i am in|i'm in|currently in|from)\s+([a-z\s]+?)(?:,|\.|\band\b|\bwhat\b|\bhow\b|\bwhere\b)", q_norm)
        if mixed_match:
            user_loc_hint = mixed_match.group(1).strip()
            # Strip the user location clause from search string to find the real target
            remaining_query = q_norm.replace(mixed_match.group(0), " ")
            # Check remaining query for target entity
            target_entity = self._find_entity_in_string(remaining_query)
            if target_entity:
                return target_entity

        # 2. Check prepositional target patterns: "to {entity}", "in {entity}", "near {entity}", "around {entity}"
        prep_patterns = [
            r"\b(?:to|in|at|near|around|for|of|from)\s+([a-z\s&]+?)(?:\s+(?:coastal|coast|region|district|state|city|ocean|sea|waters)|\?|\.|$)",
            r"\b(?:ocean|sea|coast|weather|temperature|temp|conditions|waves)\s+(?:near|to|in|around|at)\s+([a-z\s&]+?)(?:\?|\.|$)",
            r"\bwhich ocean is near\s+([a-z\s&]+?)(?:\?|\.|$)",
        ]

        for pat in prep_patterns:
            for m in re.finditer(pat, q_norm):
                candidate = m.group(1).strip()
                # Check if candidate or substring matches gazetteer
                found = self._find_entity_in_string(" " + candidate + " ")
                if found:
                    return found

        # 3. Direct gazetteer entity scan (ordered by key length descending for longest match)
        return self._find_entity_in_string(q_norm)

    def _find_entity_in_string(self, text_norm: str) -> Optional[str]:
        """Search text for gazetteer keys using word boundary matching."""
        # Sort keys by length descending to match "andaman and nicobar" before "andaman", "tamil nadu" before "tamil"
        sorted_keys = sorted(INDIA_GAZETTEER.keys(), key=len, reverse=True)
        for key in sorted_keys:
            # Word boundary check
            pattern = r"\b" + re.escape(key) + r"\b"
            if re.search(pattern, text_norm):
                return key
        return None

    def is_deictic_query(self, query: str) -> bool:
        """
        Check if query refers purely to the user's current GPS position.
        e.g. "my location", "where am I", "nearest ocean near me", "temperature here".
        """
        q_norm = self._normalize(query)
        # If explicitly mentions another place, it's not purely deictic
        entity = self.extract_explicit_entity(query)
        if entity:
            return False

        return any(re.search(r"\b" + re.escape(sig) + r"\b", q_norm) for sig in DEICTIC_GPS_SIGNALS)

    def _extract_explicit_coordinates(self, query: str) -> Optional[Tuple[float, float]]:
        """Extract explicit decimal coordinates from query string if present."""
        m = re.search(r"\b(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\b", query)
        if m:
            lat = float(m.group(1))
            lon = float(m.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return lat, lon
        return None

    async def resolve_query_location(
        self,
        query: str,
        client_location: LocationContext,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> QueryLocationResult:
        """
        Main entry point: Resolve query target vs user device GPS.
        Always preserves client_location separately.
        """
        q_norm = self._normalize(query)

        # 0. Check for explicit numeric coordinates in query (e.g. "Navigate to 12.85, 80.35")
        coords = self._extract_explicit_coordinates(query)
        if coords:
            c_lat, c_lon = coords
            target_loc = LocationContext(
                latitude=c_lat,
                longitude=c_lon,
                source="explicit_query",
                accuracy_m=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
                is_demo=False,
                is_approximate=False,
                label=f"Target: {c_lat:.4f}°N, {c_lon:.4f}°E",
                geographic_type="marine" if c_lon > 80.2 else "coastal",
                resolved_place=f"{c_lat:.4f}°N, {c_lon:.4f}°E",
            )
            return QueryLocationResult(
                query_entity_name=f"{c_lat:.4f}°N, {c_lon:.4f}°E",
                location_source="explicit_query",
                entity_type="explicit_coordinates",
                is_explicit=True,
                target_location=target_loc,
                state_name=None,
                coastline_length_km=None,
                bordering_oceans=[],
                notes="Explicit numeric coordinates provided in query.",
            )

        # 1. Check if user explicitly queried a named geographic entity
        entity_key = self.extract_explicit_entity(query)

        if entity_key and entity_key in INDIA_GAZETTEER:
            gdata = INDIA_GAZETTEER[entity_key]
            state_s = f", {gdata['state']}" if gdata.get("state") else ""
            label_s = f"{gdata['name']}{state_s}" if gdata["type"] != "marine_basin" else gdata["name"]

            target_loc = LocationContext(
                latitude=gdata["latitude"],
                longitude=gdata["longitude"],
                source="explicit_query",
                accuracy_m=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
                is_demo=False,
                is_approximate=bool(gdata.get("is_state", False)),
                label=label_s,
                geographic_type=gdata["geo_type"],
                resolved_place=gdata["name"],
            )

            return QueryLocationResult(
                query_entity_name=gdata["name"],
                location_source="explicit_query",
                entity_type=gdata["type"],
                is_explicit=True,
                target_location=target_loc,
                state_name=gdata.get("state"),
                coastline_length_km=gdata.get("coastline_km"),
                bordering_oceans=gdata.get("bordering_oceans", []),
                notes=gdata.get("description"),
            )

        # 2. Check if deictic ("near me", "where am I", "temperature here")
        if self.is_deictic_query(query):
            user_label = client_location.label or client_location.resolved_place or "Your current position"
            return QueryLocationResult(
                query_entity_name=client_location.resolved_place or "Current Location",
                location_source=client_location.source or "browser_gps",
                entity_type="device_gps",
                is_explicit=False,
                target_location=client_location,
                state_name=None,
                coastline_length_km=None,
                bordering_oceans=[],
                notes="Target resolved from device GPS coordinates.",
            )

        # 3. Check conversation history for previously referenced named entity
        if conversation_history:
            for turn in reversed(conversation_history[-6:]):
                hist_text = turn.get("content", "")
                h_entity = self.extract_explicit_entity(hist_text)
                if h_entity and h_entity in INDIA_GAZETTEER:
                    gdata = INDIA_GAZETTEER[h_entity]
                    state_s = f", {gdata['state']}" if gdata.get("state") else ""
                    target_loc = LocationContext(
                        latitude=gdata["latitude"],
                        longitude=gdata["longitude"],
                        source="conversation_context",
                        accuracy_m=None,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        is_demo=False,
                        is_approximate=bool(gdata.get("is_state", False)),
                        label=f"{gdata['name']}{state_s}",
                        geographic_type=gdata["geo_type"],
                        resolved_place=gdata["name"],
                    )
                    return QueryLocationResult(
                        query_entity_name=gdata["name"],
                        location_source="conversation_context",
                        entity_type=gdata["type"],
                        is_explicit=True,
                        target_location=target_loc,
                        state_name=gdata.get("state"),
                        coastline_length_km=gdata.get("coastline_km"),
                        bordering_oceans=gdata.get("bordering_oceans", []),
                        notes=f"Contextually retained from conversation turn: {gdata['name']}",
                    )

        # 4. If no explicit entity was recognized in gazetteer, attempt dynamic Nominatim forward search
        pot_entity = self._extract_unknown_potential_entity(query)
        if pot_entity:
            dynamic_res = await self._forward_geocode_nominatim(pot_entity)
            if dynamic_res:
                return dynamic_res

        # 5. Default fallback: Use client_location
        return QueryLocationResult(
            query_entity_name=client_location.resolved_place,
            location_source=client_location.source or "browser_gps",
            entity_type="device_gps",
            is_explicit=False,
            target_location=client_location,
            state_name=None,
            coastline_length_km=None,
            bordering_oceans=[],
            notes="Defaulted to client device location.",
        )

    def _extract_unknown_potential_entity(self, query: str) -> Optional[str]:
        """Extract candidate unknown place name after prepositions."""
        q_norm = self._normalize(query)
        m = re.search(r"\b(?:to|in|at|near|around|for|of)\s+([a-z]{3,25})\b", q_norm)
        if m:
            cand = m.group(1).strip()
            # Ignore common non-place words
            stop_words = {"the", "a", "an", "me", "my", "here", "this", "our", "all", "ocean", "sea", "water", "weather", "temp", "temperature"}
            if cand not in stop_words:
                return cand
        return None

    async def _forward_geocode_nominatim(self, place_name: str) -> Optional[QueryLocationResult]:
        """Query Nominatim forward search with caching for arbitrary places in India."""
        place_clean = place_name.strip().lower()
        if place_clean in self._osm_cache:
            cached = self._osm_cache[place_clean]
            return QueryLocationResult(**cached)

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{place_clean}, India",
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "in",
        }
        headers = {"User-Agent": self._user_agent}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        item = data[0]
                        lat = float(item["lat"])
                        lon = float(item["lon"])
                        display_name = item.get("display_name", place_name.title())

                        # Offline classification to determine land/sea/coast
                        from app.services.location_resolver import location_resolver
                        geo_type, short_name, state_off, _ = location_resolver.classify_offline(lat, lon)

                        target_loc = LocationContext(
                            latitude=lat,
                            longitude=lon,
                            source="explicit_query",
                            accuracy_m=None,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            is_demo=False,
                            is_approximate=False,
                            label=display_name.split(",")[0] + (f", {state_off}" if state_off else ""),
                            geographic_type=geo_type,
                            resolved_place=short_name or place_name.title(),
                        )

                        res = QueryLocationResult(
                            query_entity_name=short_name or place_name.title(),
                            location_source="explicit_query",
                            entity_type="coastal_city" if geo_type == "coastal" else "inland_city",
                            is_explicit=True,
                            target_location=target_loc,
                            state_name=state_off,
                            coastline_length_km=None,
                            bordering_oceans=[],
                            notes="Dynamically resolved via OpenStreetMap geocoder.",
                        )
                        self._osm_cache[place_clean] = res.model_dump()
                        return res
        except Exception as exc:
            logger.info("forward_geocode_nominatim_failed", extra={"place": place_name, "error": str(exc)})

        return None

    def resolve_query_location_sync(
        self,
        query: str,
        client_location: LocationContext,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> QueryLocationResult:
        """Synchronous version of resolve_query_location."""
        coords = self._extract_explicit_coordinates(query)
        if coords:
            c_lat, c_lon = coords
            target_loc = LocationContext(
                latitude=c_lat,
                longitude=c_lon,
                source="explicit_query",
                accuracy_m=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
                is_demo=False,
                is_approximate=False,
                label=f"Target: {c_lat:.4f}°N, {c_lon:.4f}°E",
                geographic_type="marine" if c_lon > 80.2 else "coastal",
                resolved_place=f"{c_lat:.4f}°N, {c_lon:.4f}°E",
            )
            return QueryLocationResult(
                query_entity_name=f"{c_lat:.4f}°N, {c_lon:.4f}°E",
                location_source="explicit_query",
                entity_type="explicit_coordinates",
                is_explicit=True,
                target_location=target_loc,
                state_name=None,
                coastline_length_km=None,
                bordering_oceans=[],
                notes="Explicit numeric coordinates provided in query.",
            )

        entity_key = self.extract_explicit_entity(query)

        if entity_key and entity_key in INDIA_GAZETTEER:
            gdata = INDIA_GAZETTEER[entity_key]
            state_s = f", {gdata['state']}" if gdata.get("state") else ""
            label_s = f"{gdata['name']}{state_s}" if gdata["type"] != "marine_basin" else gdata["name"]

            target_loc = LocationContext(
                latitude=gdata["latitude"],
                longitude=gdata["longitude"],
                source="explicit_query",
                accuracy_m=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
                is_demo=False,
                is_approximate=bool(gdata.get("is_state", False)),
                label=label_s,
                geographic_type=gdata["geo_type"],
                resolved_place=gdata["name"],
            )

            return QueryLocationResult(
                query_entity_name=gdata["name"],
                location_source="explicit_query",
                entity_type=gdata["type"],
                is_explicit=True,
                target_location=target_loc,
                state_name=gdata.get("state"),
                coastline_length_km=gdata.get("coastline_km"),
                bordering_oceans=gdata.get("bordering_oceans", []),
                notes=gdata.get("description"),
            )

        if self.is_deictic_query(query):
            return QueryLocationResult(
                query_entity_name=client_location.resolved_place or "Current Location",
                location_source=client_location.source or "browser_gps",
                entity_type="device_gps",
                is_explicit=False,
                target_location=client_location,
                state_name=None,
                coastline_length_km=None,
                bordering_oceans=[],
                notes="Target resolved from device GPS coordinates.",
            )

        # 3. Check conversation history for previously referenced named entity
        if conversation_history:
            for turn in reversed(conversation_history[-6:]):
                hist_text = turn.get("content", "")
                h_entity = self.extract_explicit_entity(hist_text)
                if h_entity and h_entity in INDIA_GAZETTEER:
                    gdata = INDIA_GAZETTEER[h_entity]
                    state_s = f", {gdata['state']}" if gdata.get("state") else ""
                    target_loc = LocationContext(
                        latitude=gdata["latitude"],
                        longitude=gdata["longitude"],
                        source="conversation_context",
                        accuracy_m=None,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        is_demo=False,
                        is_approximate=bool(gdata.get("is_state", False)),
                        label=f"{gdata['name']}{state_s}",
                        geographic_type=gdata["geo_type"],
                        resolved_place=gdata["name"],
                    )
                    return QueryLocationResult(
                        query_entity_name=gdata["name"],
                        location_source="conversation_context",
                        entity_type=gdata["type"],
                        is_explicit=True,
                        target_location=target_loc,
                        state_name=gdata.get("state"),
                        coastline_length_km=gdata.get("coastline_km"),
                        bordering_oceans=gdata.get("bordering_oceans", []),
                        notes=f"Contextually retained from conversation turn: {gdata['name']}",
                    )

        return QueryLocationResult(
            query_entity_name=client_location.resolved_place,
            location_source=client_location.source or "browser_gps",
            entity_type="device_gps",
            is_explicit=False,
            target_location=client_location,
            state_name=None,
            coastline_length_km=None,
            bordering_oceans=[],
            notes="Defaulted to client device location.",
        )


# Global singleton instance
query_location_resolver = QueryLocationResolver()

# Backward-compatible alias
INDIAN_SPATIAL_GAZETTEER = INDIA_GAZETTEER


def resolve_query_location_sync(
    query: str,
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    client_location: Optional[LocationContext] = None,
) -> QueryLocationResult:
    """Convenience synchronous function accepting either user_lat/lon or LocationContext."""
    if client_location is None:
        client_location = LocationContext(
            latitude=user_lat or 26.52,
            longitude=user_lon or 80.26,
            source="browser_gps" if user_lat is not None else "unavailable",
            accuracy_m=10.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_demo=False,
            is_approximate=False,
            label="Current Position",
            geographic_type="inland",
            resolved_place=None,
        )
    return query_location_resolver.resolve_query_location_sync(query, client_location)


async def resolve_query_location(
    query: str,
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    client_location: Optional[LocationContext] = None,
) -> QueryLocationResult:
    """Convenience async function accepting either user_lat/lon or LocationContext."""
    if client_location is None:
        client_location = LocationContext(
            latitude=user_lat or 26.52,
            longitude=user_lon or 80.26,
            source="browser_gps" if user_lat is not None else "unavailable",
            accuracy_m=10.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_demo=False,
            is_approximate=False,
            label="Current Position",
            geographic_type="inland",
            resolved_place=None,
        )
    return await query_location_resolver.resolve_query_location(query, client_location)
