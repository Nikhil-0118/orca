"""
ORCA Coordinator Node — LangGraph entry point.

Phase 3: Simple pass-through that forwards state to specialist nodes unchanged.
Future phases will add intent classification and routing logic here.

Node contract:
  Input:  OrcaState
  Output: {} (empty dict — no state modifications)
"""
from app.core.state import OrcaState


async def coordinator_node(state: OrcaState) -> dict:
    """
    LangGraph coordinator entry node.

    Currently a pass-through: does not modify state, call LLMs, classify intent,
    or contact external services.  Exists as the architectural anchor for future
    intent-based routing.
    """
    return {}
