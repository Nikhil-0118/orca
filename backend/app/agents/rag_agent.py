"""
RAG (Retrieval-Augmented Generation) Agent — LangGraph Node.

Responsibilities:
1. Synthesizes a concise retrieval query incorporating user intent and accumulated
   specialist signals (EO, Ocean, Weather, Safety).
2. Performs semantic similarity search against the ChromaDB vector store.
3. Compiles agent provenance and appends retrieved factual knowledge chunks to state['evidence'].
4. Preserves all upstream evidence and does NOT alter risk level or final answer.

Node contract:
  Input:  OrcaState (reads query, eo_result, ocean_result, weather_result, safety_result, evidence)
  Output: {"evidence": [...]}
"""
import logging
from typing import Any, Dict, List

from app.core.state import OrcaState
from app.core.vector_store import vector_store

logger = logging.getLogger("orca.agents.rag")


def _construct_retrieval_query(state: OrcaState) -> str:
    """
    Construct a concise contextual search string combining user query and key agent findings.
    Avoids dumping raw JSON.
    """
    query_text = state.get("query") or "marine intelligence overview"
    parts = [f"User query: {query_text}"]

    # 1. Safety cues
    safety = state.get("safety_result") or {}
    prox = safety.get("proximity") or {}
    if prox.get("status") == "near_boundary":
        dist = prox.get("distance_km")
        parts.append(f"Safety: Near demo boundary ({dist} km)")
    for f in safety.get("contributing_factors") or []:
        parts.append(f"Hazard factor: {f}")

    # 2. Weather cues
    weather = state.get("weather_result") or {}
    warnings = weather.get("warnings") or []
    if warnings:
        parts.append(f"Weather warnings: {', '.join(warnings)}")
    sea_cond = weather.get("sea_condition")
    if sea_cond and sea_cond.lower() != "smooth":
        parts.append(f"Sea condition: {sea_cond}")

    # 3. Ocean cues
    ocean = state.get("ocean_result") or {}
    wave_h = ocean.get("significant_wave_height_m")
    if wave_h is not None:
        parts.append(f"Wave height: {wave_h}m")

    # 4. EO cues
    eo = state.get("eo_result") or {}
    obs = eo.get("observations") or []
    if obs:
        platform = obs[0].get("platform")
        if platform:
            parts.append(f"EO satellite: {platform}")

    combined = " | ".join(parts)
    logger.debug("rag_retrieval_query_built", extra={"query": combined})
    return combined


async def rag_node(state: OrcaState) -> dict:
    """
    LangGraph node: compiles upstream agent evidence, retrieves domain knowledge
    from ChromaDB vector store, and appends [RAG KNOWLEDGE] entries to evidence.
    """
    existing_evidence: List[Any] = list(state.get("evidence") or [])

    # 1. Compile upstream agent provenance
    eo = state.get("eo_result") or {}
    ocean = state.get("ocean_result") or {}
    weather = state.get("weather_result") or {}
    safety = state.get("safety_result") or {}

    agent_evidences = []
    if ocean:
        src = ocean.get("source", "INCOIS ERDDAP")
        status = ocean.get("status", "mock")
        freshness = ocean.get("freshness", "historical")
        if status == "live":
            agent_evidences.append(f"Ocean state data: {src} (live, {freshness})")
        else:
            agent_evidences.append(f"Ocean state data: {src} (mock - fallback)")

    if eo:
        src = eo.get("source", "Bhoonidhi-mock")
        status = eo.get("status", "mock")
        if status in ("live", "success"):
            freshness = eo.get("freshness", "historical")
            if src == "MOSDAC":
                param = eo.get("parameter", "chlorophyll_a")
                val = eo.get("value")
                agent_evidences.append(f"EO satellite data: {src} ({param}, value: {val}, {freshness})")
            else:
                agent_evidences.append(f"EO satellite data: {src} (live, {freshness})")
        else:
            reason = eo.get("notes") or eo.get("reason", "token unconfigured")
            agent_evidences.append(f"EO satellite data: {src} (mock - {reason})")

    if weather:
        src = weather.get("source", "IMD-mock")
        status = weather.get("status", "mock")
        if status == "live":
            freshness = weather.get("freshness", "historical")
            agent_evidences.append(f"Weather data: {src} (live, {freshness})")
        else:
            reason = weather.get("reason", "API key unconfigured")
            agent_evidences.append(f"Weather data: {src} (mock - {reason})")

    if safety:
        score = safety.get("risk_score", 0)
        agent_evidences.append(
            f"Safety assessment: Multi-agent risk evaluation (score: {score}/100) using "
            f"[DEMO BOUNDARY] sample (approximate; not for navigation)"
        )

    for ae in agent_evidences:
        if ae not in existing_evidence:
            existing_evidence.append(ae)

    # 2. Retrieve knowledge from ChromaDB only if RAG/knowledge is selected
    selected = state.get("selected_agents")
    should_search = selected is None or any(a in selected for a in ("rag", "knowledge"))
    retrieval_query = _construct_retrieval_query(state) if should_search else ""
    hits = vector_store.search(query=retrieval_query, top_k=3) if should_search else []

    for hit in hits:
        doc = hit.get("document", "").strip()
        meta = hit.get("metadata") or {}
        src = meta.get("source", "ORCA_Knowledge_Base")
        cat = meta.get("category", "domain_guideline")

        formatted_rag_entry = f"[RAG KNOWLEDGE] ({src} - {cat}): {doc}"
        if formatted_rag_entry not in existing_evidence:
            existing_evidence.append(formatted_rag_entry)

    logger.info(
        "rag_node_completed",
        extra={
            "retrieved_chunks": len(hits),
            "total_evidence_count": len(existing_evidence),
        },
    )

    return {
        "evidence": existing_evidence,
    }
