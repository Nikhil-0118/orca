"""
Schemas for the /api/safety-check endpoint.
"""
from typing import Optional
from pydantic import BaseModel, Field


class SafetyCheckRequest(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    prev_state: Optional[str] = Field(None, description="Previous safety state for hysteresis evaluation")


class SafetyCheckResponse(BaseModel):
    inside_boundary: bool
    distance_to_boundary_km: float
    alert_level: str
    state: str
    severity: str
    bearing_degrees: float
    nearest_boundary_name: str
    alert_title: str
    alert_message: str
    demo_only: bool = True
