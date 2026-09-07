"""
Standardized marine oceanographic data schemas (SST, chlorophyll, waves, PFZ).
Acts as the intermediate model separating external connectors from downstream agents.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import Coordinates, GeoJsonPolygon


class SSTData(BaseModel):
    sea_surface_temperature_celsius: float
    anomaly_celsius: Optional[float] = None
    source: str = "ISRO-MOSDAC"
    timestamp: datetime


class ChlorophyllData(BaseModel):
    concentration_mg_m3: float
    source: str = "ISRO-MOSDAC"
    timestamp: datetime


class WeatherData(BaseModel):
    wind_speed_knots: float
    wind_direction_degrees: float
    significant_wave_height_meters: float
    storm_surge_meters: Optional[float] = 0.0
    cyclone_warning_level: Optional[str] = "NONE"
    source: str = "INCOIS-ERDDAP"
    timestamp: datetime


class PFZData(BaseModel):
    zone_id: str
    boundary: GeoJsonPolygon
    bearing_degrees: float
    distance_km: float
    depth_meters: float
    validity_start: datetime
    validity_end: datetime
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class MarineStateData(BaseModel):
    location: Coordinates
    sst: Optional[SSTData] = None
    chlorophyll: Optional[ChlorophyllData] = None
    weather: Optional[WeatherData] = None
    active_pfz: List[PFZData] = []
    is_safe_for_navigation: bool = True
    next_safe_window_utc: Optional[datetime] = None
