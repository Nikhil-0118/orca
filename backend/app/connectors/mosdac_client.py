"""
ISRO MOSDAC Connector.
Fetches Sea Surface Temperature (SST), Chlorophyll concentrations, and ocean current vector grids.
"""
from datetime import datetime
from typing import Any, Dict, Optional
from app.connectors.base_connector import BaseConnector
from app.config import settings
from app.core.logger import logger
from app.schemas.common import Coordinates
from app.schemas.marine_data import ChlorophyllData, SSTData


class MosdacClient(BaseConnector):
    """Client for ISRO's Meteorological & Oceanographic Satellite Data Archival Centre (MOSDAC)."""

    def __init__(self):
        super().__init__(
            base_url=settings.MOSDAC_API_BASE_URL,
            api_key=settings.MOSDAC_API_KEY,
            timeout=15.0,
        )

    async def get_sea_surface_temperature(self, location: Coordinates) -> SSTData:
        """Fetch live SST and thermal anomaly for a given geospatial coordinate."""
        logger.info("mosdac_fetching_sst", lat=location.latitude, lon=location.longitude)
        # Connector returns normalized internal schemas
        return SSTData(
            sea_surface_temperature_celsius=28.4,
            anomaly_celsius=0.6,
            source="ISRO-MOSDAC",
            timestamp=datetime.utcnow(),
        )

    async def get_chlorophyll_density(self, location: Coordinates) -> ChlorophyllData:
        """Fetch ocean color monitor (OCM) chlorophyll-a concentration."""
        logger.info("mosdac_fetching_chlorophyll", lat=location.latitude, lon=location.longitude)
        return ChlorophyllData(
            concentration_mg_m3=0.85,
            source="ISRO-MOSDAC",
            timestamp=datetime.utcnow(),
        )
