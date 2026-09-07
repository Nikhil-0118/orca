"""
Final LLM & Multi-Agent Reasoner Node for ORCA.

Responsibilities:
1. Synthesizes converged evidence across all specialist agents (EO, Ocean, Weather, Safety, RAG).
2. Enforces strict Programmatic Risk Maximization:
   - Risk Ordering: unknown (0) < low (1) < moderate (2) < high (3) < critical (4)
   - Final risk level CANNOT be lowered below the highest risk reported by upstream agents.
3. Surfaces and explains cross-signal conflicts (e.g., calm weather vs boundary proximity).
4. Strictly respects data provenance (LIVE, SIMULATED/MOCK, HISTORICAL, DEMO BOUNDARY).
5. Produces authoritative final_answer, enforced risk_level, and actionable recommendations.

Node contract:
  Input:  OrcaState (reads query, eo_result, ocean_result, weather_result, safety_result, evidence)
  Output: {"final_answer": str, "risk_level": str, "recommendations": list}
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.state import OrcaState

logger = logging.getLogger("orca.agents.reasoner")

RISK_RANK: Dict[str, int] = {
    "unknown": 0,
    "low": 1,
    "moderate": 2,
    "high": 3,
    "critical": 4,
}

RANK_TO_RISK: Dict[int, str] = {
    0: "unknown",
    1: "low",
    2: "moderate",
    3: "high",
    4: "critical",
}


def _get_signal_risk_levels(state: OrcaState) -> Dict[str, str]:
    """Extract or infer individual risk levels reported by upstream specialist agents."""
    signals: Dict[str, str] = {}

    # Safety Agent risk
    safety = state.get("safety_result") or {}
    signals["safety"] = str(safety.get("risk_level", "low")).lower()

    # Ocean Agent risk
    ocean = state.get("ocean_result") or {}
    wave_h = ocean.get("significant_wave_height_m")
    ocean_wind = ((ocean.get("wind") or {}).get("speed") or {}).get("value")
    if (wave_h is not None and wave_h >= 3.0) or (ocean_wind is not None and ocean_wind >= 12.0):
        signals["ocean"] = "high"
    elif (wave_h is not None and wave_h >= 2.0) or (ocean_wind is not None and ocean_wind >= 8.0):
        signals["ocean"] = "moderate"
    else:
        signals["ocean"] = "low"

    # Weather Agent risk
    weather = state.get("weather_result") or {}
    warnings = weather.get("warnings") or []
    w_spd = (weather.get("wind") or {}).get("speed")
    if warnings or (w_spd is not None and w_spd >= 25.0):
        signals["weather"] = "high"
    elif w_spd is not None and w_spd >= 18.0:
        signals["weather"] = "moderate"
    else:
        signals["weather"] = "low"

    # EO Agent risk
    signals["eo"] = "low"

    return signals


def _compute_enforced_risk(signals: Dict[str, str]) -> Tuple[str, str]:
    """
    Enforce highest risk level across all upstream agents.
    Returns (enforced_max_risk, driver_agent_name).
    """
    max_rank = 0
    driver = "safety"

    for agent_name, risk_str in signals.items():
        rank = RISK_RANK.get(risk_str, 1)
        if rank > max_rank:
            max_rank = rank
            driver = agent_name

    enforced_level = RANK_TO_RISK.get(max_rank, "low")
    return enforced_level, driver


def _detect_and_explain_conflicts(signals: Dict[str, str], driver: str, enforced_risk: str) -> Optional[str]:
    """
    Identify if upstream agents disagree on risk and format an explicit explanatory note.
    """
    safety_r = signals.get("safety", "low")
    weather_r = signals.get("weather", "low")
    ocean_r = signals.get("ocean", "low")

    conflicts = []

    # Weather vs Safety conflict
    if safety_r in ("moderate", "high", "critical") and weather_r == "low":
        conflicts.append(
            f"Weather data indicates relatively calm conditions ({weather_r} risk), "
            f"while the safety assessment identifies elevated boundary-related risk ({safety_r} risk)."
        )
    elif weather_r in ("moderate", "high", "critical") and safety_r == "low":
        conflicts.append(
            f"Local boundary positioning indicates clear passage ({safety_r} risk), "
            f"while official weather advisories indicate severe marine conditions ({weather_r} risk)."
        )

    # Ocean vs Weather conflict
    if weather_r in ("high", "critical") and ocean_r == "low":
        conflicts.append(
            f"The ocean surface baseline shows moderate wave height ({ocean_r} risk), "
            f"while weather bulletins report active storm/gale warnings ({weather_r} risk)."
        )
    elif ocean_r in ("high", "critical") and weather_r == "low":
        conflicts.append(
            f"Weather wind is currently light ({weather_r} risk), "
            f"while ocean state records hazardous wave swell ({ocean_r} risk)."
        )

    if not conflicts:
        return None

    explanation = (
        f"Signal Conflict Analysis: {' '.join(conflicts)} "
        f"In accordance with maritime safety policy, these signals disagree, "
        f"so the higher-risk interpretation ({enforced_risk.upper()} driven by {driver.upper()} agent) is retained."
    )
    return explanation


from app.agents.final_reasoning_agent import (
    final_reasoning_agent,
    final_reasoning_node,
    FinalReasoningAgent,
    get_signal_risk_levels,
    compute_enforced_risk,
    detect_and_explain_conflicts,
    build_deterministic_fallback_answer,
    build_structured_llm_payload,
)


async def reasoner_node(state: OrcaState) -> dict:
    """
    LangGraph reasoner node: delegates to FinalReasoningAgent to synthesize
    multi-agent findings using LLM or deterministic fallback.
    """
    return await final_reasoning_agent.reason(state)

