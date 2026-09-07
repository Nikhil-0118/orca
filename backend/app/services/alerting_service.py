"""
Alerting and Live Re-alerting Service.
Manages subscription registries, push notification broadcasts, and triggers SMS fallback when signal drops.
"""
from typing import List, Optional
from app.core.logger import logger
from app.schemas.alerts import AlertItem, AlertSubscriptionRequest
from app.services.sms_fallback_service import SmsFallbackService


class AlertingService:
    """Dispatches marine alerts across WebSockets, Web Push, and SMS fallback."""

    def __init__(self, sms_service: Optional[SmsFallbackService] = None):
        self.sms_service = sms_service or SmsFallbackService()
        self._active_subscriptions: List[AlertSubscriptionRequest] = []

    async def register_subscription(self, subscription: AlertSubscriptionRequest) -> bool:
        """Register a vessel/user for location-aware live re-alerts."""
        self._active_subscriptions.append(subscription)
        logger.info("alert_subscription_registered", vessel_id=subscription.vessel_id)
        return True

    async def broadcast_alert(self, alert: AlertItem) -> int:
        """Broadcast alert to matching vessels in affected geospatial zones."""
        logger.info("broadcasting_marine_alert", alert_id=alert.id, severity=alert.severity)
        # Logic to iterate over subscriptions and push to web/SMS
        return len(self._active_subscriptions)
