"""
Marine alerts, danger zone notifications, and subscription contracts.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import Coordinates, GeoJsonPolygon


class AlertSeverity(str, Enum):
    INFO = "INFO"
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    DANGER = "DANGER"
    EMERGENCY = "EMERGENCY"


class AlertType(str, Enum):
    CYCLONE_STORM = "CYCLONE_STORM"
    HIGH_WAVE = "HIGH_WAVE"
    HEATWAVE_SST = "HEATWAVE_SST"
    IMBL_BOUNDARY = "IMBL_BOUNDARY"
    PFZ_OPPORTUNITY = "PFZ_OPPORTUNITY"


class AlertItem(BaseModel):
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    affected_polygon: Optional[GeoJsonPolygon] = None
    issued_at: datetime
    expires_at: Optional[datetime] = None
    sms_compatible_text: str = Field(..., max_length=160, description="Compressed 160-char SMS copy")


class AlertSubscriptionRequest(BaseModel):
    phone_number: Optional[str] = None
    device_token: Optional[str] = None
    vessel_id: str
    current_location: Coordinates
    alert_types: list[AlertType] = []
    enable_sms_fallback: bool = True
