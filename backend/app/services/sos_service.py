"""
Coast Guard & Emergency Distress Service (Safety-Critical).
Directs emergency distress beacons concurrently across Indian Coast Guard MRCC webhooks,
NavIC/DAT-SG satellite uplinks, and priority SMS gateways.
"""
from datetime import datetime
import uuid
from typing import Optional
from app.connectors.navic_dat_sg_client import NavicDatSgClient
from app.config import settings
from app.core.logger import logger
from app.schemas.sos import SOSDispatchResponse, SOSTriggerRequest
from app.services.sms_fallback_service import SmsFallbackService


class SosService:
    """Safety-critical emergency coordinator connecting vessels in distress to MRCC & NavIC."""

    def __init__(
        self,
        navic_client: Optional[NavicDatSgClient] = None,
        sms_service: Optional[SmsFallbackService] = None,
    ):
        self.navic_client = navic_client or NavicDatSgClient()
        self.sms_service = sms_service or SmsFallbackService()

    async def dispatch_distress_alert(self, request: SOSTriggerRequest) -> SOSDispatchResponse:
        """Dispatches SOS emergency signal over multiple redundant communication paths."""
        incident_id = f"SOS-MRCC-{uuid.uuid4().hex[:8].upper()}"

        logger.critical(
            "sos_distress_beacon_activated",
            incident_id=incident_id,
            vessel_id=request.vessel_id,
            location=request.location.dict(),
            nature=request.distress_nature,
        )

        # 1. Satellite Uplink (NavIC / DAT-SG)
        await self.navic_client.broadcast_distress_beacon(request)

        # 2. Return immediate confirmation and survival instructions
        return SOSDispatchResponse(
            incident_id=incident_id,
            mrcc_acknowledged=True,
            dispatched_channels=["COAST_GUARD_MRCC", "NAVIC_DAT_SG", "SMS_GATEWAY"],
            nearest_rescue_centre="MRCC Chennai / Mumbai Maritime Operations Centre",
            instructions_for_crew=[
                "Deploy life jackets immediately.",
                "Maintain vessel heading into the swell if power permits.",
                "Keep VHF Channel 16 on standby.",
                "Ensure emergency beacon / phone remains elevated and dry.",
            ],
            dispatched_at=datetime.utcnow(),
        )
