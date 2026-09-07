"""
Schemas for the /api/query endpoint (Phase 8.3 Decision-First Engine).

Supports response modes: conversation | utility | marine | safety | location.
Separates decision, key conditions, actionable recommendations, best timing,
and reasoning summary from evidence and limitations.
"""
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


GeographicType = Literal["inland", "coastal", "marine", "unknown"]


class ResolvedLocation(BaseModel):
    """Structured reverse-geocoded and classified location."""
    latitude: Optional[float] = Field(None, description="Latitude in decimal degrees")
    longitude: Optional[float] = Field(None, description="Longitude in decimal degrees")
    place_name: Optional[str] = Field(None, description="Resolved city, town, village, or maritime area name")
    district: Optional[str] = Field(None, description="Administrative district or county")
    state: Optional[str] = Field(None, description="State, province, or union territory")
    country: Optional[str] = Field(None, description="Country name")
    geographic_type: GeographicType = Field("unknown", description="inland | coastal | marine | unknown")
    source: str = Field("reverse_geocoder", description="reverse_geocoder | offline_dataset | manual | demo | unavailable")
    is_approximate: bool = Field(False, description="True if resolution is approximate or regional centroid")
    resolved_at: Optional[str] = Field(None, description="ISO timestamp of resolution")
    bhuvan_location: Optional[Dict[str, Any]] = Field(None, description="Optional Bhuvan village reverse-geocoding enrichment")


class LocationContext(BaseModel):
    """
    Canonical location context for ORCA (Phase 8.4 & A.1).
    Every spatial agent consumes this single source of truth.
    """
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to +90)")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to +180)")
    source: str = Field(
        "unavailable",
        description="Location provenance: browser_gps | user_override | map_selection | demo | unavailable",
    )
    accuracy_m: Optional[float] = Field(None, ge=0.0, description="GPS accuracy in meters when available from device")
    speed_knots: Optional[float] = Field(None, ge=0.0, description="Vessel cruising speed in knots if provided")
    timestamp: Optional[str] = Field(None, description="ISO timestamp when coordinates were acquired")
    is_demo: bool = Field(False, description="True if coordinate is an explicit application demonstration position")
    is_approximate: bool = Field(False, description="True if coordinate is a regional centroid or approximate estimate")
    label: Optional[str] = Field(None, description="Human-readable regional descriptor e.g. 'Kanpur, Uttar Pradesh'")
    geographic_type: Optional[GeographicType] = Field(None, description="inland | coastal | marine | unknown")
    resolved_place: Optional[str] = Field(None, description="Normalized specific place/city name")
    bhuvan_location: Optional[Dict[str, Any]] = Field(None, description="Optional Bhuvan village reverse-geocoding enrichment")

    @field_validator("latitude", mode="before")
    @classmethod
    def validate_latitude(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        val = float(v)
        if val < -90.0 or val > 90.0:
            raise ValueError(f"Latitude {val} must be between -90.0 and +90.0 decimal degrees")
        return val

    @field_validator("longitude", mode="before")
    @classmethod
    def validate_longitude(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        val = float(v)
        if val < -180.0 or val > 180.0:
            raise ValueError(f"Longitude {val} must be between -180.0 and +180.0 decimal degrees")
        return val


class Location(BaseModel):
    """Legacy 2-parameter coordinates for backward compatibility."""
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Plain-language marine query")
    location: Optional[Union[LocationContext, Location, Dict[str, Any]]] = Field(
        None,
        description="Explicit client location context or legacy lat/lon coordinates",
    )
    session_id: str = Field(..., min_length=1, description="Client session identifier")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Recent conversation history turns for context resolution [{'role': 'user'|'assistant', 'content': '...'}]",
    )
    is_demo_mode: Optional[bool] = Field(
        False,
        description="Explicit flag for SIH demonstration mode; permits use of demo coordinates",
    )


class DecisionData(BaseModel):
    label: str = Field(
        ...,
        description="Actionable decision label: Recommended | Recommended with caution | Not recommended | Avoid | Operational caution | Clear | Unable to determine reliably",
    )
    summary: Optional[str] = Field(None, description="1-sentence plain-language decision summary")
    confidence: Optional[str] = Field("moderate", description="Human-readable decision confidence: high | moderate | low")


class BestTimeWindow(BaseModel):
    available: bool = Field(False, description="True ONLY if verified forecast supports timing window")
    window: Optional[str] = Field(None, description="Time window string e.g. '06:00 - 09:00 AM' if available")
    basis: Optional[str] = Field(None, description="Factual basis for window or reason why window cannot be determined")


class StructuredEvidenceItem(BaseModel):
    source: str = Field(..., description="Name of the reporting specialist agent or data feed")
    summary: str = Field(..., description="Concise human-readable summary of domain evidence")


class HumanConditions(BaseModel):
    wind: Optional[str] = Field(None, description="Plain-language wind condition")
    sea_state: Optional[str] = Field(None, description="Plain-language sea state and wave height")
    water_temperature: Optional[str] = Field(None, description="Plain-language water temperature")
    visibility: Optional[str] = Field(None, description="Plain-language visibility")
    safety: Optional[str] = Field(None, description="Plain-language boundary and navigational status")


class HumanFriendlyResponse(BaseModel):
    direct_answer: str = Field(..., description="Immediate direct answer to operational question (YES, CAUTION, NO, UNCERTAIN)")
    decision_code: Optional[str] = Field(None, description="YES | CAUTION | NO | UNCERTAIN | None")
    explanation: str = Field(..., description="1-3 clear, plain-language sentences explaining the reason")
    best_time: Optional[str] = Field(None, description="Supported time window or honest statement that timing cannot be predicted")
    conditions: Optional[HumanConditions] = Field(None, description="Clean, human-readable environmental conditions")
    safety_notice: Optional[str] = Field(None, description="Prominent safety precaution or emergency instruction")
    data_quality_note: Optional[str] = Field(None, description="Plain-language data freshness or simulation note")
    sources: List[str] = Field(default_factory=list, description="Human-readable data source names")


SpatialQueryType = Literal[
    "user_location",
    "target_location",
    "boundary_safety",
    "marine_route",
    "danger_areas",
    "fishing_destination",
]


class MapMarker(BaseModel):
    id: str = Field(..., description="Unique marker identifier")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Marker latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Marker longitude")
    label: str = Field(..., description="Human-readable label")
    marker_type: str = Field("target", description="vessel | target | fishing | boundary | hazard | waypoint")
    status: Optional[str] = Field("info", description="safe | caution | warning | danger | info")
    description: Optional[str] = Field(None, description="Detailed tooltip or subtitle")


class MapZone(BaseModel):
    id: str = Field(..., description="Unique zone/polygon identifier")
    title: str = Field(..., description="Zone name or hazard title")
    zone_type: str = Field("boundary_line", description="boundary_line | restricted | warning | caution")
    geometry_type: str = Field("LineString", description="LineString | Polygon")
    coordinates: List[Any] = Field(..., description="GeoJSON coordinates [lon, lat] pairs")
    stroke_color: Optional[str] = Field("#f59e0b", description="Hex or rgba stroke color")
    fill_color: Optional[str] = Field(None, description="Hex or rgba fill color")
    opacity: Optional[float] = Field(0.8, description="Opacity (0.0 to 1.0)")
    description: Optional[str] = Field(None, description="Zone description or warning note")


class MapRoute(BaseModel):
    origin: Dict[str, Any] = Field(..., description="Origin {latitude, longitude, label}")
    destination: Dict[str, Any] = Field(..., description="Destination {latitude, longitude, label}")
    waypoints: List[Dict[str, Any]] = Field(default_factory=list, description="List of waypoints {latitude, longitude, name}")
    distance_km: float = Field(..., description="Great-circle distance in kilometers")
    distance_nm: float = Field(..., description="Nautical miles (km * 0.539957)")
    bearing_degrees: float = Field(..., description="Initial compass bearing in degrees (0-360)")
    estimated_time_minutes: Optional[int] = Field(None, description="ETA in minutes only if vessel speed is provided")
    safety_clearance: str = Field("SAFE", description="SAFE | CAUTION | RESTRICTED")
    safety_note: Optional[str] = Field(None, description="Navigation guidance or advisory note")
    is_approximate: bool = Field(True, description="True if route is an approximate or non-certified track")
    is_inland_warning: bool = Field(False, description="True if origin vessel position is inland")


class SpatialPayload(BaseModel):
    enabled: bool = Field(True, description="True if spatial visualization is active")
    type: SpatialQueryType = Field(..., description="Spatial query type")
    title: str = Field(..., description="Short descriptive title for map card header")
    summary: str = Field(..., description="Concise plain-language spatial summary")
    center: Dict[str, float] = Field(..., description="Map center coordinate {'latitude': lat, 'longitude': lon}")
    zoom: int = Field(9, description="Recommended initial zoom level")
    markers: List[MapMarker] = Field(default_factory=list, description="Markers to render")
    zones: Optional[List[MapZone]] = Field(default_factory=list, description="Polylines or polygons (e.g. boundaries)")
    routes: Optional[List[MapRoute]] = Field(default_factory=list, description="Marine routes")
    boundary_distance_km: Optional[float] = Field(None, description="Distance to nearest boundary in km")
    boundary_bearing_deg: Optional[float] = Field(None, description="Bearing to nearest boundary")
    safety_state: Optional[str] = Field(None, description="NORMAL | APPROACHING | WARNING | BREACH")
    navigation_warning: Optional[str] = Field(None, description="Warning message when vessel is inland or marine routing is restricted")
    is_marine_navigable: Optional[bool] = Field(None, description="True if departure position allows marine navigation")
    target_location: Optional[Dict[str, Any]] = Field(None, description="Structured target/destination metadata")
    vessel_location: Optional[Dict[str, Any]] = Field(None, description="Structured vessel/origin metadata")


class QueryResponse(BaseModel):
    mode: str = Field(
        "marine",
        description="Response mode indicating execution branch: conversation | utility | marine | safety | location",
    )
    answer: str = Field(..., description="Direct 1-3 line plain-language answer addressing the user question first")
    location: Optional[LocationContext] = Field(
        None,
        description="Canonical target location context associated with this query response",
    )
    user_location: Optional[LocationContext] = Field(
        None,
        description="User client/device location context (e.g. live GPS), preserved separately from query target",
    )
    query_location: Optional[Dict[str, Any]] = Field(
        None,
        description="Explicit query location entity metadata and provenance",
    )
    decision: Optional[DecisionData] = Field(None, description="Actionable activity or operational decision")
    risk_level: str = Field(..., description="Enforced risk level: low | moderate | high | critical | none")
    risk_summary: Optional[str] = Field(None, description="1-sentence plain-language reason for risk level")
    key_conditions: List[str] = Field(default_factory=list, description="Top 2-4 key operational/environmental conditions")
    recommendations: List[str] = Field(default_factory=list, description="Actionable maritime precautions and guidelines")
    best_time: Optional[BestTimeWindow] = Field(None, description="Timing advice (never fabricated or hallucinated)")
    reasoning_summary: Optional[str] = Field(None, description="Short user-facing 'Why' explanation")
    evidence: List[str] = Field(default_factory=list, description="Legacy list of evidence strings")
    structured_evidence: List[StructuredEvidenceItem] = Field(default_factory=list, description="Structured agent evidence items")
    data_limitations: List[str] = Field(default_factory=list, description="Transparent data limitations or simulation notes")
    agents_used: List[str] = Field(default_factory=list, description="List of domain agents participating in the query")
    evidence_summary: Optional[Dict[str, Any]] = Field(None, description="Summary of evidence currency, freshness, and quality")
    source_reliability: Optional[Dict[str, Any]] = Field(None, description="Deterministic source reliability assessment")
    data_quality: Optional[Dict[str, Any]] = Field(None, description="Detailed data quality breakdown and parameters")
    conflicts: Optional[List[Dict[str, Any]]] = Field(None, description="Detected cross-agent signal conflicts")
    human_response: Optional[HumanFriendlyResponse] = Field(None, description="Phase 17 human-centered response structure")
    spatial: Optional[SpatialPayload] = Field(None, description="Optional spatial/map payload for spatial queries")

