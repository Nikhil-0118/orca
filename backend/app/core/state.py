"""
Shared LangGraph state schema for the ORCA multi-agent coordinator (Phase 8.2).

Supports dynamic agent selection via selected_agents and safety_required.
Every agent node writes ONLY to its own dedicated key (eo_result, ocean_result, etc.)
to avoid needing LangGraph reducers. The synthesizer node reads all results and writes
the final_answer, evidence, risk_level, and recommendations.
"""
from typing import Optional, TypedDict


class OrcaState(TypedDict):
    # ── Input (set at invocation) ─────────────────────────────────────
    query: str
    location: dict          # {"lat": float, "lon": float}
    session_id: str
    selected_agents: Optional[list]   # e.g. ["ocean"] or ["ocean", "weather", "safety"]
    safety_required: Optional[bool]  # True if safety evaluation is mandatory
    conversation_history: Optional[list]  # Optional prior turns for contextual reasoning

    # ── Per-agent result slots (each node writes only its own key) ────
    eo_result: Optional[dict]
    ocean_result: Optional[dict]
    weather_result: Optional[dict]
    safety_result: Optional[dict]
    ecosystem_result: Optional[dict]

    # ── Cross-Agent Marine Analysis & Decision (Phase 14) ────────────
    marine_analysis_result: Optional[dict]
    marine_decision: Optional[dict]

    # ── Synthesized output (set by final synthesis step) ──────────────
    evidence: list
    risk_level: str
    final_answer: str
    recommendations: list
    risk_summary: Optional[str]
    structured_evidence: Optional[list]
    data_limitations: Optional[list]
    agents_used: Optional[list]
    decision: Optional[dict]
    key_conditions: Optional[list]
    best_time: Optional[dict]
    reasoning_summary: Optional[str]

    # ── Evidence Metadata & Reliability (Phase 16) ───────────────────
    evidence_summary: Optional[dict]
    source_reliability: Optional[dict]
    data_quality: Optional[dict]
    conflicts: Optional[list]

    # ── Human-Centered Response UX (Phase 17) ────────────────────────
    human_response: Optional[dict]
