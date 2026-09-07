"""
Alerts, Push Notifications, and Geofenced Marine Advisory Endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, status
from app.schemas.alerts import AlertItem, AlertSubscriptionRequest
from app.schemas.common import Coordinates, StandardApiResponse
from app.services.alerting_service import AlertingService

router = APIRouter()


def get_alerting_service() -> AlertingService:
    return AlertingService()


@router.get("/active", response_model=StandardApiResponse[List[AlertItem]], status_code=status.HTTP_200_OK)
async def get_active_alerts(
    lat: float,
    lon: float,
    radius_km: float = 50.0,
    service: AlertingService = Depends(get_alerting_service),
) -> StandardApiResponse[List[AlertItem]]:
    """Retrieve active weather, storm, and boundary alerts for given coordinates."""
    # Placeholder returning active alerts
    return StandardApiResponse(
        success=True,
        message="Active alerts retrieved",
        data=[],
    )


@router.post("/subscribe", response_model=StandardApiResponse[bool], status_code=status.HTTP_201_CREATED)
async def subscribe_to_alerts(
    subscription: AlertSubscriptionRequest,
    service: AlertingService = Depends(get_alerting_service),
) -> StandardApiResponse[bool]:
    """Register device / phone number for automated live re-alerts and SMS fallback."""
    result = await service.register_subscription(subscription)
    return StandardApiResponse(
        success=True,
        message="Subscription registered successfully",
        data=result,
    )
