"""
External data connectors for ISRO (MOSDAC), INCOIS (ERDDAP), and NavIC/DAT-SG.

IMPORTANT ARCHITECTURAL RULE:
Modules in `app/agents/` must NOT import from `app/connectors/`.
Data flow is strictly one-way through `app/services/` or dependency injection.
"""
from app.connectors.incois_client import IncoisClient
from app.connectors.mosdac_client import MosdacClient
from app.connectors.navic_dat_sg_client import NavicDatSgClient

__all__ = ["MosdacClient", "IncoisClient", "NavicDatSgClient"]
