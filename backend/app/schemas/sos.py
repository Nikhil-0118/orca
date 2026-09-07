"""
Distress call and Coast Guard SOS schemas (Safety-Critical).
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import Coordinates


class DistressNature(str, Enum):
    ENGINE_FAILURE = "ENGINE_FAILURE"
    MEDICAL_EMERGENCY = "MEDICAL_EMERGENCY"
    CAPSIZING_SINKING = "CAPSIZING_SINKING"
    PIRACY_SECURITY = "PIRACY_SECURITY"
    BAD_WEATHER_TRAPPED = "BAD_WEATHER_TRAPPED"
    UNKNOWN = "UNKNOWN"


class SOSTriggerRequest(BaseModel):
    vessel_id: str
    vessel_name: Optional[str] = None
    crew_count: int = Field(default=1, ge=1)
    location: Coordinates
    distress_nature: DistressNature = DistressNature.UNKNOWN
    notes: Optional[str] = Field(default=None, max_length=500)
    battery_level_percent: Optional[int] = Field(default=None, ge=0, le=100)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SOSDispatchResponse(BaseModel):
    incident_id: str
    mrcc_acknowledged: bool
    dispatched_channels: List[str] = Field(
        ...,
        description="Active delivery paths: ['COAST_GUARD_MRCC', 'NAVIC_DAT_SG', 'SMS_GATEWAY']"
    )
    nearest_rescue_centre: str
    instructions_for_crew: List[str]
    dispatched_at: datetime
