"""
Background Scheduler configuration using AsyncIOScheduler.
Manages cron-like execution of data pollers without blocking FastAPI async event loops.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.connectors.incois_client import IncoisClient
from app.connectors.mosdac_client import MosdacClient
from app.config import settings
from app.core.logger import logger
from app.jobs.alert_poller import MarineAlertPoller
from app.services.alerting_service import AlertingService

scheduler = AsyncIOScheduler()


def start_background_jobs() -> None:
    """Register all recurring background pollers and start scheduler."""
    poller = MarineAlertPoller(
        incois_client=IncoisClient(),
        mosdac_client=MosdacClient(),
        alerting_service=AlertingService(),
    )

    scheduler.add_job(
        poller.poll_and_dispatch,
        "interval",
        seconds=settings.ALERT_POLL_INTERVAL_SECONDS,
        id="marine_live_alert_poller",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("background_scheduler_started", interval_sec=settings.ALERT_POLL_INTERVAL_SECONDS)


def stop_background_jobs() -> None:
    """Cleanly shut down scheduler during app termination."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("background_scheduler_stopped")
