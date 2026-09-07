"""
Dedicated Location Resolver for ORCA (Phase A.1).

Converts raw GPS coordinates into verified, structured geographic entities:
- city / town / village
- district
- state / union territory
- country
- geographic type: inland | coastal | marine | unknown

Authoritative Rules:
1. Coordinates are never altered; they remain the exact numeric ground-truth.
2. OpenStreetMap Nominatim is queried with proper User-Agent and spatial cache.
3. Offline GIS evaluation prevents inland coordinates (e.g. Kanpur 26.52, 80.26)
   from ever being labeled as coastal or marine.
4. Marine open-sea coordinates are classified as 'marine' and tagged with the proper basin.
5. Implemented with 100% pure Python geometric algorithms (zero external C-library dependencies).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.schemas.query import GeographicType, ResolvedLocation

logger = logging.getLogger("orca.services.location_resolver")


@dataclass
class NearestCoastResult:
    """Geospatial proximity intelligence for nearest ocean / coastline."""
    ocean: str                      # e.g. "Bay of Bengal"
    coastal_region: str             # e.g. "Balasore / Odisha Coast"
    distance_km: float              # Geodesic distance in kilometers
    bearing_deg: float              # Initial bearing in degrees (0-360)
    compass_direction: str          # 8-point compass direction (e.g. "Southeast")
    nearest_lat: float              # Latitude of nearest coastal sector point
    nearest_lon: float              # Longitude of nearest coastal sector point
    is_user_inland: bool            # True if evaluated position is classified as inland
    user_place: str                 # Human-readable place name of evaluated position
    summary_text: str               # Human-readable concise summary
    is_state: bool = False          # True if evaluated target is an entire state
    coastline_km: Optional[float] = None  # Approximate coastline length if state
    is_explicit: bool = False       # True if evaluating an explicit query target


# ── Indian Administrative State Classifications ──────────────────────────────
INLAND_STATES = {
    "uttar pradesh", "madhya pradesh", "bihar", "rajasthan", "punjab",
    "haryana", "delhi", "national capital territory of delhi", "telangana",
    "chhattisgarh", "jharkhand", "uttarakhand", "himachal pradesh",
    "assam", "manipur", "meghalaya", "mizoram", "nagaland", "tripura",
    "sikkim", "arunachal pradesh", "ladakh", "jammu and kashmir",
    "chandigarh",
}

COASTAL_STATES = {
    "tamil nadu", "kerala", "andhra pradesh", "odisha", "west bengal",
    "maharashtra", "gujarat", "goa", "karnataka", "puducherry",
    "andaman and nicobar islands", "lakshadweep", "dadra and nagar haveli and daman and diu",
}

# Peninsular coastline coordinate points for distance estimation (lat, lon)
PENINSULAR_COASTLINE_POINTS: List[Tuple[float, float]] = [
    (23.5, 68.5), (22.5, 69.0), (21.0, 70.0), (21.0, 72.0), (19.0, 72.8),
    (16.0, 73.5), (14.5, 74.0), (12.5, 75.0), (10.0, 76.2), (8.5, 77.0),
    (8.08, 77.55), # Kanyakumari
    (9.2, 78.5), (10.3, 79.2), (11.5, 79.8), (13.08, 80.27), # Chennai
    (15.5, 81.5), (17.7, 83.2), (19.5, 85.0), (21.5, 87.0), (21.6, 88.5),
]

# Polygon vertices (lon, lat) outlining the mainland Indian landmass for land vs sea checks
MAINLAND_INDIA_POLYGON: List[Tuple[float, float]] = [
    (68.0, 24.0), (71.0, 24.5), (74.0, 27.0), (74.0, 31.0), (76.0, 32.5),
    (78.0, 31.0), (80.5, 29.0), (88.0, 27.5), (90.0, 26.0), (92.0, 25.0),
    (92.0, 22.0), (89.0, 22.0), (88.5, 21.6), (87.0, 21.5), (85.0, 19.5),
    (83.2, 17.7), (80.27, 13.08), (79.2, 10.3), (77.55, 8.08), (76.2, 10.0),
    (74.0, 14.5), (72.8, 19.0), (70.0, 21.0), (68.5, 23.5), (68.0, 24.0)
]


def _point_in_polygon(x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
    """Pure-Python Ray casting algorithm for point-in-polygon."""
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodesic distance between two coordinates in km."""
    R = 6371.0088
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _min_distance_to_coast_km(lat: float, lon: float) -> float:
    """Estimate minimum geodesic distance from (lat, lon) to the peninsular coastline."""
    min_dist = float("inf")
    for clat, clon in PENINSULAR_COASTLINE_POINTS:
        d = _haversine_distance_km(lat, lon, clat, clon)
        if d < min_dist:
            min_dist = d
    return min_dist


# ── Comprehensive Coastal Sectors Dataset (Phase A.1.2) ─────────────────────
# Structured reference coordinates along Indian coastline (~7,500 km)
# Format: (latitude, longitude, ocean_basin_name, coastal_region_name)
COASTAL_SECTORS_DATASET: List[Tuple[float, float, str, str]] = [
    # ── West Bengal & Odisha (Bay of Bengal) ──
    (21.65, 88.30, "Bay of Bengal", "Sundarbans / West Bengal Coast"),
    (21.62, 87.52, "Bay of Bengal", "Digha / West Bengal Coast"),
    (21.50, 87.00, "Bay of Bengal", "Balasore / Odisha Coast"),
    (20.30, 86.70, "Bay of Bengal", "Paradip / Odisha Coast"),
    (19.80, 85.83, "Bay of Bengal", "Puri / Odisha Coast"),
    (19.30, 85.00, "Bay of Bengal", "Gopalpur / Odisha Coast"),

    # ── Andhra Pradesh (Bay of Bengal) ──
    (18.30, 84.00, "Bay of Bengal", "Srikakulam / North Andhra Coast"),
    (17.68, 83.22, "Bay of Bengal", "Visakhapatnam / Andhra Coast"),
    (16.98, 82.25, "Bay of Bengal", "Kakinada / Godavari Delta Coast"),
    (16.18, 81.14, "Bay of Bengal", "Machilipatnam / Krishna Delta Coast"),
    (15.50, 80.05, "Bay of Bengal", "Ongole / Andhra Coast"),
    (14.44, 80.00, "Bay of Bengal", "Nellore / Andhra Coast"),

    # ── Tamil Nadu & Puducherry (Bay of Bengal / Coromandel Coast) ──
    (13.40, 80.30, "Bay of Bengal", "Pulicat / North Tamil Nadu Coast"),
    (13.08, 80.28, "Bay of Bengal", "Chennai / Coromandel Coast"),
    (12.50, 80.15, "Bay of Bengal", "Mahabalipuram / Coromandel Coast"),
    (11.93, 79.83, "Bay of Bengal", "Puducherry Coast"),
    (11.75, 79.77, "Bay of Bengal", "Cuddalore / Tamil Nadu Coast"),
    (10.76, 79.84, "Bay of Bengal", "Nagapattinam / Tamil Nadu Coast"),
    (10.30, 79.20, "Bay of Bengal", "Point Calimere / Palk Strait Coast"),
    (9.28, 79.12, "Bay of Bengal", "Rameswaram / Palk Bay Coast"),

    # ── Gulf of Mannar & Southern Tip (Indian Ocean Confluence) ──
    (8.80, 78.15, "Indian Ocean", "Tuticorin / Gulf of Mannar Coast"),
    (8.48, 78.04, "Indian Ocean", "Tiruchendur / Gulf of Mannar Coast"),
    (8.08, 77.55, "Indian Ocean", "Kanyakumari / Indian Ocean Confluence"),
    (8.38, 76.98, "Arabian Sea", "Kovalam / South Kerala Coast"),
    (8.50, 76.95, "Arabian Sea", "Thiruvananthapuram / Kerala Coast"),

    # ── Kerala & Karnataka (Arabian Sea / Malabar Coast) ──
    (9.49, 76.33, "Arabian Sea", "Alappuzha / Kerala Coast"),
    (9.97, 76.22, "Arabian Sea", "Kochi / Malabar Coast"),
    (10.52, 76.02, "Arabian Sea", "Chavakkad / Kerala Coast"),
    (11.25, 75.77, "Arabian Sea", "Kozhikode / Malabar Coast"),
    (11.87, 75.36, "Arabian Sea", "Kannur / Malabar Coast"),
    (12.87, 74.84, "Arabian Sea", "Mangalore / Karnataka Coast"),
    (13.34, 74.74, "Arabian Sea", "Udupi / Malpe Coast"),
    (14.28, 74.44, "Arabian Sea", "Bhatkal / Karnataka Coast"),
    (14.81, 74.13, "Arabian Sea", "Karwar / Karnataka Coast"),

    # ── Goa & Maharashtra (Arabian Sea / Konkan Coast) ──
    (15.49, 73.82, "Arabian Sea", "Goa / Konkan Coast"),
    (15.88, 73.65, "Arabian Sea", "Vengurla / South Konkan Coast"),
    (16.99, 73.30, "Arabian Sea", "Ratnagiri / Konkan Coast"),
    (18.30, 72.90, "Arabian Sea", "Murud / Konkan Coast"),
    (18.92, 72.83, "Arabian Sea", "Mumbai / Konkan Coast"),
    (19.39, 72.82, "Arabian Sea", "Vasai / North Konkan Coast"),
    (19.98, 72.74, "Arabian Sea", "Dahanu / Maharashtra Coast"),

    # ── Gujarat (Arabian Sea) ──
    (20.42, 72.83, "Arabian Sea", "Daman Coast"),
    (21.17, 72.70, "Arabian Sea", "Surat / Gulf of Khambhat Coast"),
    (21.60, 72.15, "Arabian Sea", "Bhavnagar / Gulf of Khambhat Coast"),
    (20.71, 70.98, "Arabian Sea", "Diu Coast"),
    (20.90, 70.37, "Arabian Sea", "Veraval / Saurashtra Coast"),
    (21.63, 69.60, "Arabian Sea", "Porbandar / Saurashtra Coast"),
    (22.24, 68.96, "Arabian Sea", "Dwarka / Saurashtra Coast"),
    (22.80, 69.70, "Arabian Sea", "Kandla / Gulf of Kutch Coast"),
    (23.25, 68.56, "Arabian Sea", "Koteshwar / Kutch Coast"),

    # ── Island Territories ──
    (11.66, 92.74, "Bay of Bengal", "Port Blair / Andaman Sea Coast"),
    (10.57, 72.64, "Arabian Sea", "Kavaratti / Lakshadweep Coast"),
]


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate forward initial bearing from (lat1, lon1) to (lat2, lon2) in degrees [0, 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    theta = math.atan2(y, x)
    return round((math.degrees(theta) + 360.0) % 360.0, 1)


def bearing_to_compass(bearing: float) -> str:
    """Convert bearing in degrees to standard 8-point compass direction."""
    directions = ["North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"]
    idx = round(bearing / 45.0) % 8
    return directions[idx]


class LocationResolver:
    """
    Dedicated geographic resolver.
    Translates raw GPS coordinates to authoritative place names and land/sea classification.
    """

    def __init__(self, timeout_seconds: float = 3.0):
        self.timeout_seconds = timeout_seconds
        self._cache: Dict[str, ResolvedLocation] = {}
        self._user_agent = "ORCA-Marine-Platform/1.0 (sih-isro-prototype)"

    def _cache_key(self, lat: float, lon: float) -> str:
        """Bucket coordinates to ~1.1km resolution (2 decimal places) for spatial caching."""
        return f"{round(lat, 2):.2f},{round(lon, 2):.2f}"

    def classify_offline(self, lat: float, lon: float) -> Tuple[GeographicType, str, Optional[str], Optional[str]]:
        """
        Pure offline geographic classification based on coordinates and GIS reference.
        Guarantees that inland points are NEVER called coastal or marine.
        Returns: (geographic_type, place_name, state, country)
        """
        dist_to_coast = _min_distance_to_coast_km(lat, lon)
        is_on_mainland = _point_in_polygon(lon, lat, MAINLAND_INDIA_POLYGON)

        # 1. Deep inland Northern / Central India (e.g. Kanpur: 26.52, 80.26)
        if lat >= 23.5 and 73.0 <= lon <= 88.0:
            if 26.2 <= lat <= 26.8 and 80.0 <= lon <= 80.6:
                return "inland", "Kanpur Region (Uttar Pradesh)", "Uttar Pradesh", "India"
            elif 25.0 <= lat <= 28.5 and 78.0 <= lon <= 84.5:
                return "inland", "Inland Gangetic Plain (Uttar Pradesh region)", "Uttar Pradesh", "India"
            elif 21.5 <= lat <= 26.0 and 74.0 <= lon <= 82.5:
                return "inland", "Inland Central India (Madhya Pradesh region)", "Madhya Pradesh", "India"
            elif lat >= 28.0 and 76.0 <= lon <= 78.5:
                return "inland", "Inland National Capital Region (Delhi/NCR)", "Delhi", "India"
            elif 24.0 <= lat <= 27.5 and 83.5 <= lon <= 88.5:
                return "inland", "Inland Eastern India (Bihar region)", "Bihar", "India"
            return "inland", f"Inland Northern India ({lat:.2f}° N, {lon:.2f}° E)", None, "India"

        # 2. General peninsular land interior (> 55 km from coast)
        if is_on_mainland and dist_to_coast > 55.0:
            if 12.8 <= lat <= 13.2 and 77.4 <= lon <= 77.8:
                return "inland", "Bengaluru Region (Karnataka)", "Karnataka", "India"
            elif 17.2 <= lat <= 17.6 and 78.2 <= lon <= 78.7:
                return "inland", "Hyderabad Region (Telangana)", "Telangana", "India"
            return "inland", f"Inland Peninsular India ({lat:.2f}° N, {lon:.2f}° E)", None, "India"

        # 3. Coastal fringe (within 55 km of peninsular coast)
        if dist_to_coast <= 55.0 and (6.0 <= lat <= 24.0):
            if 12.5 <= lat <= 13.6 and 79.8 <= lon <= 80.5:
                return "coastal", "Chennai Coastal Region", "Tamil Nadu", "India"
            elif 9.5 <= lat <= 10.5 and 75.8 <= lon <= 76.6:
                return "coastal", "Kochi Coastal Region", "Kerala", "India"
            elif 18.5 <= lat <= 19.5 and 72.5 <= lon <= 73.2:
                return "coastal", "Mumbai Coastal Region", "Maharashtra", "India"
            elif 17.4 <= lat <= 18.2 and 83.0 <= lon <= 83.6:
                return "coastal", "Visakhapatnam Coastal Region", "Andhra Pradesh", "India"
            elif 20.0 <= lat <= 23.0 and 68.5 <= lon <= 72.0:
                return "coastal", "Gujarat Coastal Region", "Gujarat", "India"
            elif 19.5 <= lat <= 22.0 and 85.0 <= lon <= 88.5:
                return "coastal", "Odisha / Bengal Coastal Region", "Odisha", "India"
            elif 8.0 <= lat <= 9.0 and 77.0 <= lon <= 78.0:
                return "coastal", "Kanyakumari / Cape Comorin Coastal Waters", "Tamil Nadu", "India"
            return "coastal", f"Indian Coastal Sector ({lat:.2f}° N, {lon:.2f}° E)", None, "India"

        # 4. Marine Open Waters (Outside mainland landmass)
        if not is_on_mainland:
            # Palk Bay / Gulf of Mannar
            if 8.5 <= lat <= 10.3 and 78.6 <= lon <= 80.2:
                return "marine", "Palk Strait / Gulf of Mannar Waters", None, None
            # Arabian Sea (West of peninsular India)
            if 8.0 <= lat <= 25.0 and 60.0 <= lon < 77.0:
                return "marine", "Arabian Sea (Open Waters)", None, None
            # Bay of Bengal (East of peninsular India)
            if 8.0 <= lat <= 22.5 and 80.5 < lon <= 95.0:
                return "marine", "Bay of Bengal (Open Waters)", None, None
            # Andaman Sea
            if 6.0 <= lat <= 14.5 and 91.5 <= lon <= 96.0:
                return "marine", "Andaman Sea", None, None
            # Equatorial Indian Ocean
            if lat < 6.0:
                return "marine", "Equatorial Indian Ocean", None, None

        return "unknown", f"Position ({lat:.2f}° N, {lon:.2f}° E)", None, None

    def _parse_nominatim_data(
        self, data: dict, latitude: float, longitude: float, now_iso: str
    ) -> ResolvedLocation:
        """Parse raw Nominatim JSON response into structured ResolvedLocation."""
        if "error" in data:
            g_type, place_name, state_off, country_off = self.classify_offline(latitude, longitude)
            return ResolvedLocation(
                latitude=latitude,
                longitude=longitude,
                place_name=place_name,
                district=None,
                state=state_off,
                country=country_off,
                geographic_type=g_type,
                source="reverse_geocoder",
                is_approximate=True,
                resolved_at=now_iso,
            )

        address = data.get("address") or {}
        place_city = (
            address.get("city") or
            address.get("town") or
            address.get("village") or
            address.get("suburb") or
            address.get("county") or
            address.get("municipality")
        )
        district = address.get("state_district") or address.get("county")
        state = address.get("state")
        country = address.get("country")

        state_lower = (state or "").lower()
        dist_to_coast = _min_distance_to_coast_km(latitude, longitude)

        if state_lower in INLAND_STATES:
            geo_type: GeographicType = "inland"
        elif state_lower in COASTAL_STATES:
            geo_type = "coastal" if dist_to_coast <= 50.0 else "inland"
        elif dist_to_coast <= 35.0:
            geo_type = "coastal"
        else:
            geo_type = "inland"

        place_parts = [p for p in [place_city, district] if p]
        primary_place = ", ".join(dict.fromkeys(place_parts)) if place_parts else (data.get("name") or "Local Area")

        return ResolvedLocation(
            latitude=latitude,
            longitude=longitude,
            place_name=primary_place,
            district=district,
            state=state,
            country=country,
            geographic_type=geo_type,
            source="reverse_geocoder",
            is_approximate=False,
            resolved_at=now_iso,
        )

    async def _enrich_with_bhuvan(self, resolved: ResolvedLocation, lat: float, lon: float) -> ResolvedLocation:
        """
        Optional Bhuvan Village Reverse Geocoding enrichment.
        Safely attempts enrichment without overwriting authoritative place/state data or failing on error.
        """
        try:
            from app.services.bhuvan_client import bhuvan_client
            bhuvan_data = await bhuvan_client.reverse_geocode(lat, lon)
            if bhuvan_data:
                resolved.bhuvan_location = bhuvan_data
                if not resolved.district and bhuvan_data.get("district"):
                    resolved.district = bhuvan_data["district"]
                if not resolved.state and bhuvan_data.get("state"):
                    resolved.state = bhuvan_data["state"]
                # Only enrich place_name if it is missing or an uninformative generic coordinate descriptor
                if (not resolved.place_name or ("Sector (" in resolved.place_name or "Position (" in resolved.place_name)) and bhuvan_data.get("village"):
                    v_name = bhuvan_data["village"]
                    d_name = bhuvan_data.get("district")
                    resolved.place_name = f"{v_name}, {d_name}" if d_name else v_name
        except Exception as exc:
            logger.debug("bhuvan_enrichment_skipped", extra={"error": str(exc)})
        return resolved

    def _enrich_with_bhuvan_sync(self, resolved: ResolvedLocation, lat: float, lon: float) -> ResolvedLocation:
        """Synchronous helper for Bhuvan Village Reverse Geocoding enrichment."""
        try:
            from app.services.bhuvan_client import bhuvan_client
            bhuvan_data = bhuvan_client.reverse_geocode_sync(lat, lon)
            if bhuvan_data:
                resolved.bhuvan_location = bhuvan_data
                if not resolved.district and bhuvan_data.get("district"):
                    resolved.district = bhuvan_data["district"]
                if not resolved.state and bhuvan_data.get("state"):
                    resolved.state = bhuvan_data["state"]
                if (not resolved.place_name or ("Sector (" in resolved.place_name or "Position (" in resolved.place_name)) and bhuvan_data.get("village"):
                    v_name = bhuvan_data["village"]
                    d_name = bhuvan_data.get("district")
                    resolved.place_name = f"{v_name}, {d_name}" if d_name else v_name
        except Exception as exc:
            logger.debug("bhuvan_enrichment_sync_skipped", extra={"error": str(exc)})
        return resolved

    async def resolve(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        source: str = "browser_gps",
        is_demo: bool = False,
    ) -> ResolvedLocation:
        """
        Asynchronously resolve coordinates to human-readable place and geographic type.
        Leverages spatial caching, Nominatim reverse-geocoding, and strict offline fallback.
        Optionally enriches with ISRO Bhuvan Village Reverse Geocoding when token is configured.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # Handle missing coordinates
        if latitude is None or longitude is None:
            return ResolvedLocation(
                latitude=0.0,
                longitude=0.0,
                place_name=None,
                district=None,
                state=None,
                country=None,
                geographic_type="unknown",
                source="unavailable",
                is_approximate=False,
                resolved_at=now_iso,
            )

        # Handle out-of-bounds coordinates
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            return ResolvedLocation(
                latitude=latitude,
                longitude=longitude,
                place_name="Invalid Coordinates",
                district=None,
                state=None,
                country=None,
                geographic_type="unknown",
                source="invalid",
                is_approximate=False,
                resolved_at=now_iso,
            )

        # Check spatial cache
        cache_k = self._cache_key(latitude, longitude)
        if cache_k in self._cache:
            cached = self._cache[cache_k]
            return cached.model_copy(update={"resolved_at": now_iso})

        # Explicit demo mode handling
        if is_demo or source == "demo":
            resolved = ResolvedLocation(
                latitude=latitude,
                longitude=longitude,
                place_name="Chennai Coast (SIH Demo Region)",
                district="Chennai",
                state="Tamil Nadu",
                country="India",
                geographic_type="coastal",
                source="demo",
                is_approximate=True,
                resolved_at=now_iso,
            )
            self._cache[cache_k] = resolved
            return resolved

        # Query OpenStreetMap Nominatim reverse geocoder
        resolved = None
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "zoom": 14,
            }
            headers = {"User-Agent": self._user_agent}

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    resolved = self._parse_nominatim_data(data, latitude, longitude, now_iso)

        except Exception as exc:
            logger.info("reverse_geocode_offline_fallback", extra={"error": str(exc), "lat": latitude, "lon": longitude})

        if resolved is None:
            # Graceful offline fallback
            g_type, place_name, state_off, country_off = self.classify_offline(latitude, longitude)
            resolved = ResolvedLocation(
                latitude=latitude,
                longitude=longitude,
                place_name=place_name,
                district=None,
                state=state_off,
                country=country_off,
                geographic_type=g_type,
                source="offline_dataset",
                is_approximate=True,
                resolved_at=now_iso,
            )

        # Optional Bhuvan Village Reverse Geocoding enrichment
        resolved = await self._enrich_with_bhuvan(resolved, latitude, longitude)
        self._cache[cache_k] = resolved
        return resolved

    def resolve_sync(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        source: str = "browser_gps",
        is_demo: bool = False,
    ) -> ResolvedLocation:
        """Synchronous wrapper utilizing cache, reverse-geocoding, or offline classifier."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if latitude is None or longitude is None:
            return ResolvedLocation(
                latitude=0.0,
                longitude=0.0,
                place_name=None,
                district=None,
                state=None,
                country=None,
                geographic_type="unknown",
                source="unavailable",
                is_approximate=False,
                resolved_at=now_iso,
            )

        # Handle out-of-bounds coordinates
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            return ResolvedLocation(
                latitude=latitude,
                longitude=longitude,
                place_name="Invalid Coordinates",
                district=None,
                state=None,
                country=None,
                geographic_type="unknown",
                source="invalid",
                is_approximate=False,
                resolved_at=now_iso,
            )

        cache_k = self._cache_key(latitude, longitude)
        if cache_k in self._cache:
            return self._cache[cache_k].model_copy(update={"resolved_at": now_iso})

        # Explicit demo mode handling
        if is_demo or source == "demo":
            resolved = ResolvedLocation(
                latitude=latitude,
                longitude=longitude,
                place_name="Chennai Coast (SIH Demo Region)",
                district="Chennai",
                state="Tamil Nadu",
                country="India",
                geographic_type="coastal",
                source="demo",
                is_approximate=True,
                resolved_at=now_iso,
            )
            self._cache[cache_k] = resolved
            return resolved

        # Synchronous reverse-geocoding attempt
        resolved = None
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "zoom": 14,
            }
            headers = {"User-Agent": self._user_agent}
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    resolved = self._parse_nominatim_data(data, latitude, longitude, now_iso)
        except Exception:
            pass

        if resolved is None:
            # Use offline classifier synchronously
            g_type, place_name, state_off, country_off = self.classify_offline(latitude, longitude)
            resolved = ResolvedLocation(
                latitude=latitude,
                longitude=longitude,
                place_name=place_name,
                district=None,
                state=state_off,
                country=country_off,
                geographic_type=g_type,
                source="offline_dataset",
                is_approximate=True,
                resolved_at=now_iso,
            )

        # Optional Bhuvan Village Reverse Geocoding enrichment
        resolved = self._enrich_with_bhuvan_sync(resolved, latitude, longitude)
        self._cache[cache_k] = resolved
        return resolved

    def find_nearest_ocean(
        self,
        lat: float,
        lon: float,
        user_place: Optional[str] = None,
        geo_type: Optional[str] = None,
        is_explicit_location: bool = False,
        entity_type: Optional[str] = None,
        coastline_km: Optional[float] = None,
        bordering_oceans: Optional[List[str]] = None,
    ) -> NearestCoastResult:
        """
        Geospatial proximity calculation for nearest ocean/coastline (Phase A.1.2 & Global Fix).
        Calculates exact geodesic distance and forward bearing against the coastline dataset.
        Handles inland, coastal, and marine coordinates with distinction.
        Supports regional coastal states (e.g. Gujarat) as geometries with extensive coastlines,
        distinguishing regional state-level approximations from point/city queries.
        """
        if geo_type is None:
            geo_type, place_name, _, _ = self.classify_offline(lat, lon)
            if not user_place:
                user_place = place_name

        display_place = user_place or ("the queried location" if is_explicit_location else "your current location")
        norm_name = (user_place or "").lower().strip()

        # ── Special Handling for Coastal States (e.g. Gujarat, Maharashtra, Odisha, Kerala, etc.) ──
        is_coastal_st = (
            entity_type == "coastal_state"
            or (is_explicit_location and norm_name in COASTAL_STATES)
            or (is_explicit_location and any(st in norm_name for st in ["gujarat", "maharashtra", "kerala", "tamil nadu", "tamilnadu", "andhra pradesh", "odisha", "west bengal", "goa", "karnataka"]))
        )

        if is_coastal_st:
            # Determine primary ocean basin and coastline metrics for the state
            if "gujarat" in norm_name:
                ocean = "Arabian Sea"
                c_region = "Gujarat Saurashtra & Kutch Coast"
                c_km = coastline_km or 1600.0
                summary = (
                    f"📍 Resolved Location: Gujarat (Coastal State)\n\n"
                    f"🌊 Nearest Ocean / Sea: Arabian Sea (including the Gulf of Kutch and Gulf of Khambhat).\n\n"
                    f"📏 Distance: 0 km (Gujarat is an extensive maritime coastal state with approximately {int(c_km):,} km of coastline bordering the Arabian Sea).\n\n"
                    f"🧭 Regional Note: Because Gujarat is an extensive geographic region with India's longest coastline rather than a single point, this result represents the state's coastal interface. Approximate distance from Gujarat's interior centroid to the coast is ~70 km."
                )
            elif any(s in norm_name for s in ["tamil nadu", "tamilnadu", "andhra", "odisha", "orissa", "west bengal", "bengal"]):
                ocean = "Bay of Bengal"
                c_region = f"{display_place} Coast"
                c_km = coastline_km or (1076.0 if "tamil" in norm_name else (974.0 if "andhra" in norm_name else 480.0))
                summary = (
                    f"📍 Resolved Location: {display_place} (Coastal State)\n\n"
                    f"🌊 Nearest Ocean / Sea: Bay of Bengal.\n\n"
                    f"📏 Distance: 0 km ({display_place} is an extensive maritime coastal state bordering the Bay of Bengal with approximately {int(c_km):,} km of coastline).\n\n"
                    f"🧭 Regional Note: As an extensive coastal state, {display_place} directly borders the Bay of Bengal."
                )
            else:
                ocean = "Arabian Sea"
                c_region = f"{display_place} Coast"
                c_km = coastline_km or (720.0 if "maharashtra" in norm_name else 580.0)
                summary = (
                    f"📍 Resolved Location: {display_place} (Coastal State)\n\n"
                    f"🌊 Nearest Ocean / Sea: Arabian Sea.\n\n"
                    f"📏 Distance: 0 km ({display_place} is an extensive maritime coastal state bordering the Arabian Sea with approximately {int(c_km):,} km of coastline).\n\n"
                    f"🧭 Regional Note: As an extensive coastal state, {display_place} directly borders the Arabian Sea."
                )

            # Find representative point in COASTAL_SECTORS_DATASET
            best_pt = min(COASTAL_SECTORS_DATASET, key=lambda c: _haversine_distance_km(lat, lon, c[0], c[1]))
            return NearestCoastResult(
                ocean=ocean,
                coastal_region=c_region,
                distance_km=0.0,
                bearing_deg=0.0,
                compass_direction="Coastal State",
                nearest_lat=best_pt[0],
                nearest_lon=best_pt[1],
                is_user_inland=False,
                user_place=display_place,
                summary_text=summary,
                is_state=True,
                coastline_km=c_km,
                is_explicit=is_explicit_location,
            )

        # ── Case 1: Point is already in open marine waters ──
        if geo_type == "marine":
            ocean = "Bay of Bengal" if lon >= 79.5 else ("Arabian Sea" if lon <= 77.0 else "Indian Ocean")
            if is_explicit_location:
                summary = (
                    f"📍 Resolved Location: {display_place} ({lat:.2f}°N, {lon:.2f}°E)\n\n"
                    f"🌊 {display_place} is an open marine water body ({ocean}).\n\n"
                    f"📏 Distance to ocean: 0 km (marine open waters)."
                )
            else:
                summary = (
                    f"📍 You are currently positioned at {lat:.2f}°N, {lon:.2f}°E in the open waters of the {ocean}.\n\n"
                    f"🌊 You are already in the marine environment ({ocean}).\n\n"
                    f"📏 Distance to ocean: 0 km (currently at sea)."
                )
            return NearestCoastResult(
                ocean=ocean,
                coastal_region=f"Open waters of {ocean}",
                distance_km=0.0,
                bearing_deg=0.0,
                compass_direction="Current Position",
                nearest_lat=lat,
                nearest_lon=lon,
                is_user_inland=False,
                user_place=display_place,
                summary_text=summary,
                is_explicit=is_explicit_location,
            )

        # Find closest point in COASTAL_SECTORS_DATASET
        best_pt = min(COASTAL_SECTORS_DATASET, key=lambda c: _haversine_distance_km(lat, lon, c[0], c[1]))
        min_dist = _haversine_distance_km(lat, lon, best_pt[0], best_pt[1])
        bearing_deg = calculate_bearing(lat, lon, best_pt[0], best_pt[1])
        compass = bearing_to_compass(bearing_deg)

        # ── Case 2: Location is coastal (or within 25 km of coast, e.g. Dwarka, Mumbai, Chennai, Kochi) ──
        if geo_type == "coastal" or min_dist < 25.0:
            if is_explicit_location:
                dist_str = "0 km (directly situated on the coast)" if min_dist < 5.0 else f"~{round(min_dist)} km"
                summary = (
                    f"📍 Resolved Location: {display_place} (Coastal Location)\n\n"
                    f"🌊 Situated directly on the coast of the {best_pt[2]} ({best_pt[3]}).\n\n"
                    f"📏 Distance to coastline: {dist_str}.\n\n"
                    f"🧭 Direction: {compass} toward open waters."
                )
            else:
                summary = (
                    f"📍 You are currently in {display_place}, which is a coastal location.\n\n"
                    f"🌊 You are situated directly on the coast of the {best_pt[2]} ({best_pt[3]}).\n\n"
                    f"📏 Distance to coastline: ~{max(1, round(min_dist))} km.\n\n"
                    f"🧭 Direction: {compass} toward open waters."
                )
            return NearestCoastResult(
                ocean=best_pt[2],
                coastal_region=best_pt[3],
                distance_km=round(min_dist, 1),
                bearing_deg=bearing_deg,
                compass_direction=compass,
                nearest_lat=best_pt[0],
                nearest_lon=best_pt[1],
                is_user_inland=False,
                user_place=display_place,
                summary_text=summary,
                is_explicit=is_explicit_location,
            )

        # ── Case 3: Location is inland (e.g. Ahmedabad, Kanpur, Delhi) ──
        if is_explicit_location:
            summary = (
                f"📍 Resolved Location: {display_place} (Inland Location)\n\n"
                f"🌊 The nearest ocean/coast to {display_place} is the {best_pt[2]} ({best_pt[3]}).\n\n"
                f"📏 Approximate distance: ~{round(min_dist)} km.\n\n"
                f"🧭 Direction: {compass} (bearing ~{round(bearing_deg)}°)."
            )
        else:
            summary = (
                f"📍 You are currently in {display_place}, which is inland.\n\n"
                f"🌊 The nearest ocean/coast is the {best_pt[2]} ({best_pt[3]}).\n\n"
                f"📏 It is approximately {round(min_dist)} km away.\n\n"
                f"🧭 Direction: {compass} (bearing ~{round(bearing_deg)}°).\n\n"
                "You are not currently within a coastal or marine area."
            )
        return NearestCoastResult(
            ocean=best_pt[2],
            coastal_region=best_pt[3],
            distance_km=round(min_dist, 1),
            bearing_deg=bearing_deg,
            compass_direction=compass,
            nearest_lat=best_pt[0],
            nearest_lon=best_pt[1],
            is_user_inland=True,
            user_place=display_place,
            summary_text=summary,
            is_explicit=is_explicit_location,
        )

    def find_nearest_water_body(
        self,
        lat: float,
        lon: float,
        user_place: Optional[str] = None,
        geo_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Identify regional freshwater water body / river basin vs ocean (Phase A.1.2).
        Explicitly clarifies distinction between terrestrial rivers and oceans.
        """
        ocean_res = self.find_nearest_ocean(lat, lon, user_place, geo_type)
        display_place = user_place or "your current location"

        # Determine prominent regional river/hydrological basin based on geographic coordinates
        if 24.0 <= lat <= 31.0 and 77.0 <= lon <= 88.0:
            river_name = "Ganges (Ganga) River System"
            basin_desc = "Ganges-Yamuna inland river basin"
        elif 28.0 <= lat <= 34.0 and 73.0 <= lon <= 77.5:
            river_name = "Indus Basin (Sutlej / Yamuna)"
            basin_desc = "North-Western river basin"
        elif 21.0 <= lat <= 24.5 and 73.0 <= lon <= 82.0:
            river_name = "Narmada / Tapti River System"
            basin_desc = "Central Indian river basin"
        elif 15.0 <= lat <= 20.5 and 73.5 <= lon <= 84.0:
            river_name = "Godavari / Krishna River System"
            basin_desc = "Deccan plateau river basin"
        elif 10.0 <= lat <= 14.5 and 75.0 <= lon <= 80.0:
            river_name = "Kaveri (Cauvery) River System"
            basin_desc = "Southern peninsular river basin"
        elif 24.0 <= lat <= 28.5 and 89.0 <= lon <= 96.0:
            river_name = "Brahmaputra River System"
            basin_desc = "North-Eastern river basin"
        else:
            river_name = "Regional inland river system"
            basin_desc = "Inland hydrological drainage"

        if ocean_res.is_user_inland:
            summary = (
                f"📍 You are currently in {display_place}, which is situated within the {basin_desc}.\n\n"
                f"💧 Nearest major water body: {river_name} (inland freshwater).\n\n"
                f"🌊 Note: {river_name} is an inland freshwater river system, distinct from oceanic or coastal marine waters. "
                f"The nearest ocean is the {ocean_res.ocean} ({ocean_res.coastal_region}), located approximately {round(ocean_res.distance_km)} km to the {ocean_res.compass_direction}."
            )
        else:
            summary = ocean_res.summary_text

        return {
            "nearest_water_body": river_name if ocean_res.is_user_inland else ocean_res.ocean,
            "is_freshwater": ocean_res.is_user_inland,
            "nearest_ocean": ocean_res.ocean,
            "ocean_distance_km": ocean_res.distance_km,
            "ocean_direction": ocean_res.compass_direction,
            "summary_text": summary,
        }


# Global singleton instance
location_resolver = LocationResolver()

# Module-level aliases
find_nearest_ocean = location_resolver.find_nearest_ocean
classify_location_type = location_resolver.classify_offline

