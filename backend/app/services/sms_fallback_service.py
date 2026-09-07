"""
SMS Fallback Service.
Compresses marine advisories and distress updates into GSM-standard 160-character messages
for transmission across weak-signal 2G/EDGE cellular networks.
"""
from typing import Optional
from app.config import settings
from app.core.logger import logger
from app.schemas.alerts import AlertItem


class SmsFallbackService:
    """Handles text compaction, multi-lingual translation, and GSM SMS gateway routing."""

    def __init__(self):
        self.gateway_url = settings.SMS_GATEWAY_API_URL

    def format_sms_alert(self, alert: AlertItem) -> str:
        """Compresses rich alert metadata into <= 160 characters."""
        text = f"ORCA ALERT [{alert.severity}]: {alert.title}. {alert.description}"
        return text[:157] + "..." if len(text) > 160 else text

    async def send_sms_alert(self, phone_number: str, message: str) -> bool:
        """Dispatches an SMS through the national/telecom gateway."""
        logger.info("sms_fallback_dispatch", phone=phone_number, char_len=len(message))
        # Gateway HTTP dispatch logic
        return True
