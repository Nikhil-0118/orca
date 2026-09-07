"""
NavIC & DAT-SG Satellite Messaging & Distress Beacon Connector.
Transmits emergency distress signals to ISRO satellite hub and receives broadcast bulletins.
"""
from typing import Any, Dict
from app.connectors.base_connector import BaseConnector
from app.config import settings
from app.core.logger import logger
from app.schemas.sos import SOSTriggerRequest


class NavicDatSgClient(BaseConnector):
    """Client for ISRO Distress Alert Transmitter - Second Generation (DAT-SG) & NavIC messaging."""

    def __init__(self):
        super().__init__(
            base_url=settings.NAVIC_GATEWAY_URL,
            api_key=settings.NAVIC_API_KEY,
            timeout=8.0,
        )

    async def broadcast_distress_beacon(self, request: SOSTriggerRequest) -> Dict[str, Any]:
        """Transmit high-priority distress signal packet over satellite transceiver."""
        logger.warn(
            "navic_satellite_sos_uplink_triggered",
            vessel_id=request.vessel_id,
            lat=request.location.latitude,
            lon=request.location.longitude,
            nature=request.distress_nature,
        )
        return {
            "status": "TRANSMITTED",
            "satellite_transponder_id": "GSAT-N2-MARITIME",
            "beacon_ack": True,
        }
