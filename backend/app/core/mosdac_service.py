"""
Core MOSDAC Service re-export for architectural flexibility.
"""
from app.services.mosdac_service import MosdacService, mosdac_service, haversine_distance_km

__all__ = ["MosdacService", "mosdac_service", "haversine_distance_km"]
