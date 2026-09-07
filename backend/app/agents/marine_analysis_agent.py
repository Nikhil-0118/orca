"""
Cross-Agent Marine Analysis LangGraph Node (Phase 14).

Sits between parallel specialist agent convergence and final answer synthesis.
Consumes converged specialist telemetry (EO, Ocean, Weather, Safety, Ecosystem)
and runs cross-agent correlation, conflict detection, freshness evaluation, and
the Marine Decision Engine.
"""
import logging
from app.core.state import OrcaState
from app.services.marine_analysis_service import marine_analysis_service

logger = logging.getLogger("orca.agents.marine_analysis")


async def marine_analysis_node(state: OrcaState) -> dict:
    """
    LangGraph Cross-Agent Marine Analysis Node.
    Produces structured marine_analysis_result and marine_decision without modifying
    raw upstream agent telemetry slots.
    """
    try:
        analysis_result = marine_analysis_service.run_analysis(state)
        decision_dict = analysis_result.decision.model_dump() if analysis_result.decision else None

        return {
            "marine_analysis_result": analysis_result.model_dump(),
            "marine_decision": decision_dict,
        }
    except Exception as exc:
        logger.error("marine_analysis_node_failed", extra={"error": str(exc)}, exc_info=True)
        # Resilient fallback: preserve state flow without crashing graph
        return {
            "marine_analysis_result": {
                "query_category": "general",
                "error": str(exc),
            },
            "marine_decision": None,
        }
