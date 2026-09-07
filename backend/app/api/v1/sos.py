"""
Safety-Critical Distress Signal Endpoints.
Dispatches emergency beacons directly to Coast Guard MRCC and satellite gateways.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.common import StandardApiResponse
from app.schemas.sos import SOSDispatchResponse, SOSTriggerRequest
from app.services.sos_service import SosService

router = APIRouter()


def get_sos_service() -> SosService:
    return SosService()


@router.post("/trigger", response_model=StandardApiResponse[SOSDispatchResponse], status_code=status.HTTP_201_CREATED)
async def trigger_emergency_sos(
    request: SOSTriggerRequest,
    service: SosService = Depends(get_sos_service),
) -> StandardApiResponse[SOSDispatchResponse]:
    """
    SAFETY-CRITICAL: Dispatches distress beacon immediately to Indian Coast Guard MRCC,
    NavIC/DAT-SG satellite transmitters, and local emergency SMS broadcasts.
    """
    try:
        response = await service.dispatch_distress_alert(request)
        return StandardApiResponse(
            success=True,
            message="Distress signal dispatched successfully across redundant emergency channels",
            data=response,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CRITICAL: Emergency SOS dispatch failure: {str(exc)}",
        ) from exc
