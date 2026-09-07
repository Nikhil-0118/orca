"""
Unit and integration tests for ORCA Phase 5:
1. ChromaDB Vector Store (initialization, seeding, search, idempotent upsert).
2. RAG Node (query & agent-aware context building, evidence augmentation, graceful degradation).
3. Reasoner Node (programmatic risk maximization, conflict detection, provenance labeling).
4. Full LangGraph pipeline execution.
"""
import pytest

from app.core.vector_store import ORCAVectorStore, SEED_KNOWLEDGE_DOCUMENTS
from app.agents.rag_agent import rag_node, _construct_retrieval_query
from app.agents.reasoner_agent import (
    reasoner_node,
    _get_signal_risk_levels,
    _compute_enforced_risk,
    _detect_and_explain_conflicts,
)
from app.core.graph import orca_graph
from app.core.state import OrcaState


# ── 1. Vector Store Tests ──────────────────────────────────────────────────

def test_vector_store_initialization_and_seeding(tmp_path):
    """Verify vector store initializes, seeds default documents, and handles queries."""
    store = ORCAVectorStore(persist_directory=str(tmp_path / "test_chroma"))
    assert store._collection.count() == len(SEED_KNOWLEDGE_DOCUMENTS)

    # Test retrieval for INCOIS ocean knowledge
    results = store.search("What data does INCOIS provide for ocean state and SST?", top_k=2)
    assert len(results) > 0
    assert any("INCOIS" in r["document"] for r in results)

    # Test retrieval for IMD weather knowledge
    results_imd = store.search("IMD coastal weather bulletins and gale warnings", top_k=2)
    assert len(results_imd) > 0
    assert any("IMD" in r["document"] for r in results_imd)

    # Test repeated seeding is idempotent and does not create duplicate documents
    store.add_seed_documents()
    assert store._collection.count() == len(SEED_KNOWLEDGE_DOCUMENTS)


# ── 2. RAG Node Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rag_node_appends_evidence_and_preserves_existing():
    """Verify rag_node preserves existing evidence, compiles agent provenance, and adds RAG chunks."""
    state: OrcaState = {
        "query": "What are the wave conditions and cyclone warnings?",
        "location": {"lat": 15.0, "lon": 72.0},
        "session_id": "test-rag-session",
        "eo_result": {
            "source": "Bhoonidhi-mock",
            "status": "mock",
            "reason": "token unconfigured",
            "observations": [{"platform": "Oceansat-3"}],
        },
        "ocean_result": {
            "source": "INCOIS ERDDAP",
            "status": "live",
            "freshness": "historical",
            "significant_wave_height_m": 2.5,
        },
        "weather_result": {
            "source": "IMD-mock",
            "status": "mock",
            "reason": "API key unconfigured",
            "sea_condition": "Rough",
            "warnings": ["Squall warning"],
        },
        "safety_result": {
            "risk_score": 45,
            "risk_level": "moderate",
            "proximity": {"status": "near_boundary", "distance_km": 12.0, "demo_only": True},
            "contributing_factors": ["Near demo boundary (12.0 km)"],
        },
        "evidence": ["Initial user context evidence"],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    result = await rag_node(state)
    assert "evidence" in result
    evidence = result["evidence"]

    # Must preserve initial evidence
    assert "Initial user context evidence" in evidence

    # Must include agent provenance
    assert any("INCOIS ERDDAP" in e for e in evidence)
    assert any("IMD-mock" in e for e in evidence)
    assert any("Bhoonidhi-mock" in e for e in evidence)

    # Must include RAG knowledge chunks
    assert any("[RAG KNOWLEDGE]" in e for e in evidence)


@pytest.mark.asyncio
async def test_rag_node_empty_state_graceful():
    """Verify rag_node degrades safely when upstream results are empty/None."""
    state: OrcaState = {
        "query": "General marine search",
        "location": {"lat": 10.0, "lon": 80.0},
        "session_id": "test-empty-rag",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    result = await rag_node(state)
    assert "evidence" in result
    assert isinstance(result["evidence"], list)


# ── 3. Reasoner Node Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reasoner_case_1_risk_escalation():
    """
    Case 1: EO = low, Ocean = moderate, Weather = high, Safety = moderate
    Expected: final risk = high (enforced maximum).
    """
    state: OrcaState = {
        "query": "Operational forecast check",
        "location": {"lat": 18.0, "lon": 72.0},
        "session_id": "test-c1",
        "eo_result": {"status": "live", "source": "Bhoonidhi"},
        "ocean_result": {"status": "live", "source": "INCOIS", "significant_wave_height_m": 2.2},  # moderate
        "weather_result": {"status": "live", "source": "IMD", "warnings": ["Gale warning"]},      # high
        "safety_result": {"status": "online", "risk_level": "moderate", "risk_score": 35},        # moderate
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    res = await reasoner_node(state)
    assert res["risk_level"] == "high"
    assert isinstance(res["recommendations"], list)
    assert len(res["recommendations"]) > 0


@pytest.mark.asyncio
async def test_reasoner_case_2_critical_safety_escalation():
    """
    Case 2: EO = low, Ocean = low, Weather = low, Safety = critical
    Expected: final risk = critical (enforced maximum).
    """
    state: OrcaState = {
        "query": "Can we transit close to the border?",
        "location": {"lat": 9.28, "lon": 79.3},
        "session_id": "test-c2",
        "eo_result": {"status": "mock"},
        "ocean_result": {"status": "live", "significant_wave_height_m": 0.5},
        "weather_result": {"status": "mock", "wind": {"speed": 6.0, "unit": "knots"}},
        "safety_result": {
            "status": "online",
            "risk_level": "critical",
            "risk_score": 85,
            "proximity": {"status": "near_boundary", "distance_km": 2.5, "demo_only": True},
            "recommendations": ["Adjust course immediately away from demo boundary line."],
        },
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    res = await reasoner_node(state)
    assert res["risk_level"] == "critical"
    assert any("Adjust course" in r for r in res["recommendations"])
    assert "DEMO ONLY" in res["final_answer"] or "NOT FOR NAVIGATION" in res["final_answer"]


@pytest.mark.asyncio
async def test_reasoner_case_3_conflict_surfacing():
    """
    Case 3: Conflicting signals (Weather = low vs Safety = high/critical).
    Expected: final_answer explicitly discusses the disagreement and retains higher risk.
    """
    state: OrcaState = {
        "query": "Is it safe to proceed near boundary in calm weather?",
        "location": {"lat": 9.28, "lon": 79.3},
        "session_id": "test-c3",
        "eo_result": {"status": "mock"},
        "ocean_result": {"status": "live", "significant_wave_height_m": 0.6},
        "weather_result": {"status": "live", "wind": {"speed": 5.0, "unit": "knots"}, "sea_condition": "Smooth"},
        "safety_result": {
            "status": "online",
            "risk_level": "high",
            "risk_score": 60,
            "proximity": {"status": "near_boundary", "distance_km": 3.0, "demo_only": True},
            "recommendations": ["Exercise extreme caution near demo boundary."],
        },
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    res = await reasoner_node(state)
    assert res["risk_level"] == "high"
    # Final answer must explicitly surface conflict between calm weather and elevated boundary risk
    assert "Signal Conflict" in res["final_answer"] or "disagree" in res["final_answer"].lower()


# ── 4. Full LangGraph End-to-End Pipeline Test ─────────────────────────────

@pytest.mark.asyncio
async def test_full_phase5_graph_execution():
    """
    Verify complete LangGraph:
    START -> coordinator -> [eo, ocean, weather] -> safety -> rag -> reasoner -> END
    """
    state: OrcaState = {
        "query": "Comprehensive marine intelligence assessment near Gulf of Mannar",
        "location": {"lat": 9.28, "lon": 79.3},
        "session_id": "test-e2e-graph",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    result = await orca_graph.ainvoke(state)

    # All slots populated
    assert result["eo_result"] is not None
    assert result["ocean_result"] is not None
    assert result["weather_result"] is not None
    assert result["safety_result"] is not None
    assert len(result["evidence"]) > 0
    assert result["risk_level"] in ("low", "moderate", "high", "critical")
    assert len(result["final_answer"]) > 20
    assert isinstance(result["recommendations"], list)
