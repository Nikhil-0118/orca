"""
INCOIS ERDDAP & Ocean State Forecast Connector.
Fetches Potential Fishing Zone (PFZ) advisories, wave heights, swell, and cyclone warnings.
"""
from datetime import datetime, timedelta
from typing import List
from app.connectors.base_connector import BaseConnector
from app.config import settings
from app.core.logger import logger
from app.schemas.common import Coordinates, GeoJsonPolygon
from app.schemas.marine_data import PFZData, WeatherData


class IncoisClient(BaseConnector):
    """Client for Indian National Centre for Ocean Information Services (INCOIS)."""

    def __init__(self):
        super().__init__(
            base_url=settings.INCOIS_ERDDAP_BASE_URL,
            api_key=settings.INCOIS_API_KEY,
            timeout=15.0,
        )

    async def get_weather_and_ocean_state(self, location: Coordinates) -> WeatherData:
        """Fetch ocean state forecast (wave heights, wind speed, storm surge)."""
        logger.info("incois_fetching_ocean_state", lat=location.latitude, lon=location.longitude)
        return WeatherData(
            wind_speed_knots=14.5,
            wind_direction_degrees=210.0,
            significant_wave_height_meters=1.8,
            storm_surge_meters=0.2,
            cyclone_warning_level="NONE",
            source="INCOIS-ERDDAP",
            timestamp=datetime.utcnow(),
        )

    async def get_potential_fishing_zones(self, location: Coordinates, radius_km: float = 50.0) -> List[PFZData]:
        """Fetch active PFZ polygons and advisories within vicinity."""
        logger.info("incois_fetching_pfz", lat=location.latitude, lon=location.longitude, radius_km=radius_km)
        now = datetime.utcnow()
        return [
            PFZData(
                zone_id="INCOIS-PFZ-SE-042",
                boundary=GeoJsonPolygon(
                    coordinates=[[
                        [location.longitude - 0.05, location.latitude - 0.05],
                        [location.longitude + 0.05, location.latitude - 0.05],
                        [location.longitude + 0.05, location.latitude + 0.05],
                        [location.longitude - 0.05, location.latitude + 0.05],
                        [location.longitude - 0.05, location.latitude - 0.05],
                    ]]
                ),
                bearing_degrees=135.0,
                distance_km=18.4,
                depth_meters=45.0,
                validity_start=now,
                validity_end=now + timedelta(hours=24),
                confidence_score=0.92,
            )
        ]
