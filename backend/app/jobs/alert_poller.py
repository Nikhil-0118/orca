"""
Periodic live poller for oceanographic alerts.
Periodically fetches updated cyclone tracks, severe sea state warnings,
and heatwave bulletins, triggering subscriber re-alerts.
"""
from datetime import datetime
from app.connectors.incois_client import IncoisClient
from app.connectors.mosdac_client import MosdacClient
from app.core.logger import logger
from app.schemas.alerts import AlertItem, AlertSeverity, AlertType
from app.schemas.common import Coordinates
from app.services.alerting_service import AlertingService


class MarineAlertPoller:
    """Worker task that continuously checks ISRO/INCOIS for new maritime danger flags."""

    def __init__(
        self,
        incois_client: IncoisClient,
        mosdac_client: MosdacClient,
        alerting_service: AlertingService,
    ):
        self.incois = incois_client
        self.mosdac = mosdac_client
        self.alerting = alerting_service

    async def poll_and_dispatch(self) -> None:
        """Periodic job execution tick."""
        logger.info("background_alert_poll_tick", timestamp=datetime.utcnow().isoformat())

        # Sample polling check: monitor key coastal sectors (e.g. Bay of Bengal, Arabian Sea)
        sample_loc = Coordinates(latitude=13.0827, longitude=80.2707)
        weather = await self.incois.get_weather_and_ocean_state(sample_loc)

        if weather.significant_wave_height_meters > 3.5 or weather.cyclone_warning_level != "NONE":
            alert = AlertItem(
                id=f"ALERT-AUTO-{int(datetime.utcnow().timestamp())}",
                type=AlertType.CYCLONE_STORM,
                severity=AlertSeverity.WARNING,
                title="High Wave & Storm Warning",
                description=f"Significant wave heights exceed {weather.significant_wave_height_meters}m in sector.",
                issued_at=datetime.utcnow(),
                sms_compatible_text=f"ORCA WARN: Rough sea waves {weather.significant_wave_height_meters}m. Return to shore.",
            )
            await self.alerting.broadcast_alert(alert)
