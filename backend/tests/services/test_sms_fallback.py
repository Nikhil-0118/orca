from datetime import datetime
from app.schemas.alerts import AlertItem, AlertSeverity, AlertType
from app.services.sms_fallback_service import SmsFallbackService


def test_sms_alert_formatting():
    service = SmsFallbackService()
    alert = AlertItem(
        id="TEST-001",
        type=AlertType.HIGH_WAVE,
        severity=AlertSeverity.WARNING,
        title="High Wave Warning off Tamil Nadu",
        description="Swell waves up to 3.8 meters expected during high tide. All artisanal crafts must dock.",
        issued_at=datetime.utcnow(),
        sms_compatible_text="ORCA: High wave warning 3.8m.",
    )
    sms_text = service.format_sms_alert(alert)
    assert len(sms_text) <= 160
    assert "ORCA ALERT" in sms_text
