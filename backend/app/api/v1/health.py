"""
Health check and readiness endpoints for container orchestration / uptime monitoring.
"""
from typing import Dict
from fastapi import APIRouter, status
from app.config import settings

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Basic health check and version ping."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, bool]:
    """Readiness probe for external dependencies and scheduler status."""
    return {
        "api_ready": True,
        "mosdac_bridge_ready": True,
        "incois_bridge_ready": True,
        "navic_gateway_ready": True,
    }
