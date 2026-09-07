"""
Root API Router aggregating all v1 sub-routers.
"""
from fastapi import APIRouter
from app.api.v1 import alerts, chat, health, sos

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, prefix="/health", tags=["Health & Status"])
api_router.include_router(chat.router, prefix="/chat", tags=["Marine Intelligence Chat"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts & Push Notifications"])
api_router.include_router(sos.router, prefix="/sos", tags=["Safety & Coast Guard SOS"])
