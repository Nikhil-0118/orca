"""
ORCA Phase 17 — Human-Centered Marine Reasoning & Response UX Test Suite.

Validates:
1. GO fishing query: direct YES, no technical jargon in primary answer.
2. CAUTION fishing query: direct CAUTION, no contradictory YES/GO language.
3. AVOID fishing query: direct NO, safety reason prominent.
4. INSUFFICIENT_DATA query: direct UNCERTAIN, no invented conditions.
5. Boundary danger: cannot be overridden by LLM wording, NO remains authoritative.
6. Severe weather: NO / AVOID remains dominant.
7. Stale data: described honestly, never called live/current.
8. Simulated data: explicitly labeled as simulated, never called real-time.
9. Chlorophyll query: factual answer, no automatic fishing recommendation.
10. Fish abundance query: does not claim fish abundance from weather alone; chlorophyll is not a catch guarantee.
11. Best timing without forecast: no invented timing, plain-language inability to recommend.
12. Technical leakage: primary answer strictly excludes NetCDF, grid coordinates, agent names, raw JSON, and debug tags.
"""
import pytest
import re
from typing import Any, Dict

from app.core.state import OrcaState
from app.services.human_response_formatter import human_response_formatter, classify_human_intent
from app.agents.final_reasoning_agent import final_reasoning_agent, FinalReasoningAgent
from app.services.llm_provider import BaseLLMProvider


class MockLLM(BaseLLMProvider):
    def __init__(self, response_text: str):
        self.response_text = response_text

    async def generate(self, system_prompt: str, user_payload: str, temperature: float = 0.2, max_tokens: int = 1024) -> str:
        return self.response_text


# ── TEST 1: GO Fishing Query ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_01_go_fishing_query():
    state: OrcaState = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-go",
        "eo_result": {"status": "live", "value": 0.0885, "freshness": "fresh", "observation_date": "2026-09-04"},
        "ocean_result": {"status": "live", "significant_wave_height_m": 0.8, "wind": {"speed": {"value": 5.0}}, "sea_surface_temperature_c": 30.0},
        "weather_result": {"status": "live", "wind": {"speed": 10.0, "direction": "SW"}, "sea_condition": "Smooth", "warnings": []},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 150.0, "demo_only": False}},
        "ecosystem_result": {"trophic_status": "Mesotrophic"},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "GO", "confidence": "high"},
            "data_quality": {"overall_reliability": "HIGH", "freshness_breakdown": {"weather": "RECENT"}},
            "conflicts": [],
        },
        "evidence": ["Calm seas", "No warnings"],
        "risk_level": "low",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}

    # 1. First word/sentence is GO or YES
    assert answer.startswith("GO") or answer.startswith("YES")
    assert human_resp.get("decision_code") in ("GO", "YES")
    assert "suitable for fishing" in answer.lower() or "favorable for fishing" in answer.lower()

    # 2. No debug or developer prefix
    assert not answer.startswith("Recommendation: GO")
    assert not answer.startswith("Marine analysis indicates")
    assert not answer.startswith("According to the agents")


# ── TEST 2: CAUTION Fishing Query ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_02_caution_fishing_query():
    state: OrcaState = {
        "query": "Should I go fishing today near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-caution",
        "eo_result": {"status": "live", "value": 0.0885},
        "ocean_result": {"status": "live", "significant_wave_height_m": 2.2, "wind": {"speed": {"value": 9.0}}},
        "weather_result": {"status": "live", "wind": {"speed": 18.0, "direction": "SW"}, "sea_condition": "Moderate", "warnings": []},
        "safety_result": {"risk_level": "moderate", "proximity": {"status": "inside", "distance_km": 45.0, "demo_only": False}},
        "ecosystem_result": {},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "CAUTION", "confidence": "moderate"},
            "data_quality": {"overall_reliability": "MEDIUM"},
            "conflicts": [],
        },
        "evidence": ["Moderate chop"],
        "risk_level": "moderate",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}

    assert answer.startswith("CAUTION")
    assert human_resp.get("decision_code") == "CAUTION"
    assert "extra care is needed" in answer.lower()
    # Must NOT have contradictory YES first answer
    assert not answer.startswith("YES")
    assert not answer.startswith("GO")


# ── TEST 3: AVOID Fishing Query ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_03_avoid_fishing_query():
    state: OrcaState = {
        "query": "Can we go fishing right now near Rameswaram?",
        "location": {"lat": 9.28, "lon": 79.3},
        "session_id": "p17-avoid",
        "eo_result": None,
        "ocean_result": {"status": "live", "significant_wave_height_m": 3.8},
        "weather_result": {"status": "live", "wind": {"speed": 28.0, "direction": "NE"}, "warnings": ["SQUALL_ALERT"]},
        "safety_result": {"risk_level": "high", "proximity": {"status": "near_boundary", "distance_km": 3.5, "demo_only": False}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "AVOID", "confidence": "high"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": ["Squall alert", "High waves"],
        "risk_level": "high",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}

    assert answer.startswith("AVOID") or answer.startswith("NO")
    assert human_resp.get("decision_code") in ("AVOID", "NO")
    assert "not safe" in answer.lower() or "don't recommend going fishing" in answer.lower()
    # Safety reason must be prominent
    assert "boundary" in answer.lower() or "warning" in answer.lower() or "squall" in answer.lower()


# ── TEST 4: INSUFFICIENT_DATA Query ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_04_insufficient_data():
    state: OrcaState = {
        "query": "Can I go fishing in this unmapped reef?",
        "location": {"lat": 10.0, "lon": 82.0},
        "session_id": "p17-nodata",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "INSUFFICIENT_DATA", "confidence": "low"},
            "data_quality": {"overall_reliability": "LOW"},
            "conflicts": [],
        },
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}

    assert answer.startswith("INSUFFICIENT") or answer.startswith("UNCERTAIN")
    assert human_resp.get("decision_code") in ("INSUFFICIENT_DATA", "UNCERTAIN")
    assert "reliable" in answer.lower() or "unavailable" in answer.lower()


# ── TEST 5: Boundary Danger (Zero LLM Override) ───────────────────────────────

@pytest.mark.asyncio
async def test_05_boundary_danger_override_prevention():
    deceptive_llm = '{"answer": "YES - Conditions are perfect, feel free to cross the border.", "decision": {"label": "Recommended"}}'
    agent = FinalReasoningAgent(provider=MockLLM(deceptive_llm))

    state: OrcaState = {
        "query": "Can I fish near the maritime border line?",
        "location": {"lat": 9.25, "lon": 79.45},
        "session_id": "p17-danger",
        "eo_result": {"status": "live", "value": 0.0885},
        "ocean_result": {"status": "live", "significant_wave_height_m": 0.8},
        "weather_result": {"status": "live", "wind": {"speed": 5.0, "direction": "S"}},
        "safety_result": {
            "risk_level": "critical",
            "proximity": {"status": "near_boundary", "distance_km": 0.7, "alert_message": "Immediate proximity to international boundary", "demo_only": True},
        },
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "AVOID", "confidence": "high"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": ["Critical boundary alert"],
        "risk_level": "critical",
        "final_answer": "",
        "recommendations": [],
    }

    res = await agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}

    # LLM cannot override AVOID -> NO/AVOID
    assert answer.startswith("AVOID") or answer.startswith("NO")
    assert human_resp.get("decision_code") in ("AVOID", "NO")
    assert res["risk_level"] == "critical"
    assert "boundary" in answer.lower()


# ── TEST 6: Severe Weather Dominance ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_06_severe_weather_dominance():
    state: OrcaState = {
        "query": "Is it safe to go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-storm",
        "eo_result": {"status": "live", "value": 0.0885},
        "ocean_result": {"status": "live", "significant_wave_height_m": 3.5},
        "weather_result": {"status": "live", "wind": {"speed": 32.0, "direction": "NE"}, "warnings": ["CYCLONIC GALE WARNING"]},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 120.0}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "AVOID", "confidence": "high"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": ["Gale warning"],
        "risk_level": "critical",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]

    assert answer.startswith("AVOID") or answer.startswith("NO")
    assert "warning" in answer.lower() or "cyclon" in answer.lower() or "gale" in answer.lower() or "rough" in answer.lower()


# ── TEST 7: Stale Data Honesty ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_07_stale_data_honesty():
    state: OrcaState = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-stale",
        "eo_result": {"status": "success", "value": 0.0885, "freshness": "stale", "observation_date": "2026-08-25"},
        "ocean_result": {"status": "live", "significant_wave_height_m": 1.0},
        "weather_result": {"status": "live", "wind": {"speed": 10.0, "direction": "SW"}},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 100.0}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "GO", "confidence": "moderate"},
            "data_quality": {"overall_reliability": "MEDIUM", "stale_parameters": ["chlorophyll_a"]},
            "conflicts": [],
        },
        "evidence": [],
        "risk_level": "low",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}
    dq_note = human_resp.get("data_quality_note") or ""

    assert "earlier observation" in (answer.lower() + " " + dq_note.lower())
    # Must never claim stale satellite data is live
    assert "live satellite" not in answer.lower()


# ── TEST 8: Simulated Data Transparency ───────────────────────────────────────

@pytest.mark.asyncio
async def test_08_simulated_data_transparency():
    state: OrcaState = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-sim",
        "eo_result": None,
        "ocean_result": {"status": "simulated", "source": "simulated", "significant_wave_height_m": 1.2},
        "weather_result": {"status": "demo", "source": "IMD-SIMULATED", "wind": {"speed": 12.0, "direction": "W"}},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 120.0}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "CAUTION", "confidence": "moderate"},
            "data_quality": {"overall_reliability": "MEDIUM"},
            "conflicts": [],
        },
        "evidence": [],
        "risk_level": "moderate",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}
    dq_note = human_resp.get("data_quality_note") or ""

    combined = (answer + " " + dq_note).lower()
    assert "simulated" in combined
    assert "not be treated as live" in combined or "baseline" in combined


# ── TEST 9: Chlorophyll Query (Factual, No Forced Fishing Recommendation) ──────

@pytest.mark.asyncio
async def test_09_chlorophyll_factual_query():
    state: OrcaState = {
        "query": "What is the chlorophyll concentration near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-chla",
        "eo_result": {"status": "success", "source": "MOSDAC", "value": 0.0885, "observation_date": "2026-09-03"},
        "ocean_result": {"status": "live", "significant_wave_height_m": 0.9},
        "weather_result": {"status": "live", "wind": {"speed": 8.0, "direction": "SW"}},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside"}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "GO", "confidence": "high"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": [],
        "risk_level": "low",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}

    # Must answer factually with the value
    assert "0.0885" in answer
    assert "chlorophyll" in answer.lower()
    # Must NOT force an operational fishing recommendation
    assert not answer.startswith("YES — Conditions are currently favorable for fishing")
    assert "therefore you should go fishing" not in answer.lower()
    assert human_resp.get("decision_code") is None


# ── TEST 10: Fish Abundance Query ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_10_fish_abundance_query():
    state: OrcaState = {
        "query": "Will I get more fish near Chennai today?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-abundance",
        "eo_result": {"status": "success", "source": "MOSDAC", "value": 0.0885},
        "ocean_result": {"status": "live", "significant_wave_height_m": 0.7},
        "weather_result": {"status": "live", "wind": {"speed": 6.0, "direction": "SW"}},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside"}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "GO", "confidence": "high"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": [],
        "risk_level": "low",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]

    # Must directly state that abundance cannot be confirmed from current data alone
    assert "cannot be confirmed" in answer.lower() or "cannot be guaranteed" in answer.lower()
    # Must explain that chlorophyll is an indicator, NOT a guarantee of fish presence
    assert "guarantee" in answer.lower() or "indicator" in answer.lower()
    # Must NOT claim weather alone guarantees high catch
    assert "weather alone" in answer.lower() or "biological productivity" in answer.lower()


# ── TEST 11: Best Timing Without Forecast ─────────────────────────────────────

@pytest.mark.asyncio
async def test_11_best_timing_without_forecast():
    state: OrcaState = {
        "query": "When should I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-timing",
        "eo_result": {"status": "live", "value": 0.0885},
        "ocean_result": {"status": "live", "significant_wave_height_m": 1.1},
        "weather_result": {"status": "live", "wind": {"speed": 12.0, "direction": "S"}},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside"}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "GO", "confidence": "moderate"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "best_time": {"available": False, "window": None, "basis": "No verified future forecast available"},
        "evidence": [],
        "risk_level": "low",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}
    bt = human_resp.get("best_time") or ""

    # Must NOT invent a specific time like "tomorrow morning 6am"
    assert not re.search(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", bt, re.IGNORECASE)
    # Must clearly explain that timing cannot be predicted reliably yet
    assert "cannot be predicted reliably" in bt.lower() or "cannot be predicted reliably" in answer.lower()
    # Must not leak internal flag names
    assert "best_time.available=false" not in answer.lower()


# ── TEST 12: Technical Leakage Prohibition ────────────────────────────────────

@pytest.mark.asyncio
async def test_12_technical_leakage_prohibition():
    forbidden_tokens = [
        r"\bNetCDF\b",
        r"\bNetCDF-4\b",
        r"\bgrid coordinates\b",
        r"\bnearest grid\b",
        r"\bvariable attributes?\b",
        r"\[Signal Conflict",
        r"\[DEMO BOUNDARY\]",
        r"\[SIMULATED WEATHER DATA\]",
        r"\bWeather Agent\b",
        r"\bOcean Agent\b",
        r"\bSatellite EO Agent\b",
        r"\bSafety Agent\b",
        r"\{\s*\"answer\"",
    ]

    # Test across multiple queries
    test_queries = [
        "Can I go fishing near Chennai?",
        "What is the chlorophyll concentration near Chennai?",
        "Will I get more fish?",
        "Is it safe near Rameswaram?",
    ]

    for q in test_queries:
        state: OrcaState = {
            "query": q,
            "location": {"lat": 13.0827, "lon": 80.2707},
            "session_id": f"p17-leak-{hash(q)}",
            "eo_result": {"status": "success", "source": "MOSDAC", "value": 0.0885, "observation_date": "2026-09-03", "grid_latitude": 13.012, "grid_longitude": 80.25},
            "ocean_result": {"status": "live", "significant_wave_height_m": 0.9, "sea_surface_temperature_c": 30.0},
            "weather_result": {"status": "live", "wind": {"speed": 11.0, "direction": "SW"}, "sea_condition": "Smooth"},
            "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 120.0, "demo_only": True}},
            "marine_analysis_result": {
                "marine_decision": {"recommendation": "GO", "confidence": "high"},
                "data_quality": {"overall_reliability": "HIGH"},
                "conflicts": [],
            },
            "evidence": ["Calm seas", "Clear skies"],
            "risk_level": "low",
            "final_answer": "",
            "recommendations": [],
        }

        res = await final_reasoning_agent.reason(state)
        answer = res["final_answer"]

        for pat in forbidden_tokens:
            match = re.search(pat, answer, flags=re.IGNORECASE if not pat.startswith(r"\[") else 0)
            assert match is None, f"Technical token '{pat}' leaked into primary answer: '{answer}'"


# ── TEST 13: CAUTION Response Does Not Contain 'Recommended' or 'FAVORABLE' ────

@pytest.mark.asyncio
async def test_13_caution_no_recommended_or_favorable():
    state: OrcaState = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-caution-clean",
        "eo_result": {"status": "live", "value": 0.0885},
        "ocean_result": {"status": "live", "significant_wave_height_m": 2.1, "wind": {"speed": {"value": 8.5}}, "sea_surface_temperature_c": 30.0},
        "weather_result": {"status": "live", "wind": {"speed": 16.5, "direction": "SW"}, "sea_condition": "Rough"},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 150.0}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "CAUTION", "confidence": "moderate"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": ["Wind 16.5 kt"],
        "risk_level": "moderate",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}
    dec = res.get("decision") or {}

    # Must start with CAUTION
    assert answer.startswith("CAUTION — ")
    assert human_resp.get("decision_code") == "CAUTION"

    # Must NOT contain "Decision: Recommended" or "Recommended with caution"
    assert "decision: recommended" not in answer.lower()
    assert "recommended with caution" not in answer.lower()
    assert dec.get("label") == "CAUTION"

    # Must NOT contain "Conditions are FAVORABLE"
    assert "conditions are favorable" not in answer.lower()
    assert "favorable for fishing" not in answer.lower()


# ── TEST 14: GO, AVOID, and INSUFFICIENT_DATA Consistency ─────────────────────

@pytest.mark.asyncio
async def test_14_decision_consistency():
    # 1. GO query
    go_state: OrcaState = {
        "query": "Can I go fishing?",
        "location": {"lat": 13.08, "lon": 80.27},
        "session_id": "p17-go-cons",
        "eo_result": {"status": "live", "value": 0.0885},
        "ocean_result": {"status": "live", "significant_wave_height_m": 0.6, "wind": {"speed": {"value": 4.0}}, "sea_surface_temperature_c": 29.5},
        "weather_result": {"status": "live", "wind": {"speed": 8.0, "direction": "SW"}, "sea_condition": "Smooth"},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 150.0}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "GO", "confidence": "high"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": ["Calm"],
        "risk_level": "low",
        "final_answer": "",
        "recommendations": [],
    }
    go_res = await final_reasoning_agent.reason(go_state)
    assert go_res["final_answer"].startswith("GO — ")
    assert (go_res.get("human_response") or {}).get("decision_code") == "GO"
    assert (go_res.get("decision") or {}).get("label") == "GO"

    # 2. AVOID query
    avoid_state: OrcaState = {
        "query": "Can I go fishing?",
        "location": {"lat": 9.28, "lon": 79.3},
        "session_id": "p17-avoid-cons",
        "eo_result": None,
        "ocean_result": {"status": "live", "significant_wave_height_m": 4.0},
        "weather_result": {"status": "live", "wind": {"speed": 35.0, "direction": "NE"}, "warnings": ["GALE"]},
        "safety_result": {"risk_level": "critical", "proximity": {"status": "near_boundary", "distance_km": 1.0}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "AVOID", "confidence": "high"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": ["Storm"],
        "risk_level": "critical",
        "final_answer": "",
        "recommendations": [],
    }
    avoid_res = await final_reasoning_agent.reason(avoid_state)
    assert avoid_res["final_answer"].startswith("AVOID — ")
    assert (avoid_res.get("human_response") or {}).get("decision_code") == "AVOID"
    assert (avoid_res.get("decision") or {}).get("label") == "AVOID"

    # 3. INSUFFICIENT_DATA query
    insuf_state: OrcaState = {
        "query": "Can I go fishing?",
        "location": {"lat": 0.0, "lon": 0.0},
        "session_id": "p17-insuf-cons",
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "INSUFFICIENT_DATA", "confidence": "low"},
            "data_quality": {"overall_reliability": "LOW"},
            "conflicts": [],
        },
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }
    insuf_res = await final_reasoning_agent.reason(insuf_state)
    assert insuf_res["final_answer"].startswith("INSUFFICIENT DATA — ")
    assert (insuf_res.get("human_response") or {}).get("decision_code") == "INSUFFICIENT_DATA"
    assert (insuf_res.get("decision") or {}).get("label") == "INSUFFICIENT_DATA"


# ── TEST 15: 'Key Conditions' Is NOT Present in Primary Human Response ────────

@pytest.mark.asyncio
async def test_15_key_conditions_not_in_primary_human_response():
    queries = [
        "Can I go fishing near Chennai?",
        "When should I go fishing near Chennai?",
        "What is the weather near Chennai?",
        "Is it safe near Chennai?",
    ]
    for q in queries:
        state: OrcaState = {
            "query": q,
            "location": {"lat": 13.0827, "lon": 80.2707},
            "session_id": f"p17-keycond-{hash(q)}",
            "eo_result": {"status": "live", "value": 0.0885},
            "ocean_result": {"status": "live", "significant_wave_height_m": 1.2, "sea_surface_temperature_c": 30.0},
            "weather_result": {"status": "live", "wind": {"speed": 12.0, "direction": "SW"}, "sea_condition": "Moderate"},
            "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 150.0}},
            "marine_analysis_result": {
                "marine_decision": {"recommendation": "CAUTION", "confidence": "moderate"},
                "data_quality": {"overall_reliability": "HIGH"},
                "conflicts": [],
            },
            "evidence": ["Normal"],
            "risk_level": "moderate",
            "final_answer": "",
            "recommendations": [],
        }
        res = await final_reasoning_agent.reason(state)
        answer = res["final_answer"]

        # The literal section title "Key Conditions" must never appear in the primary response
        assert "Key Conditions" not in answer
        assert "key conditions:" not in answer.lower()


# ── TEST 16: Current Conditions Contain Relevant Marine Telemetry ──────────────

@pytest.mark.asyncio
async def test_16_current_conditions_content():
    state: OrcaState = {
        "query": "Can I go fishing near Chennai?",
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "p17-cond-check",
        "eo_result": {"status": "live", "value": 0.0885},
        "ocean_result": {"status": "live", "significant_wave_height_m": 1.5, "sea_surface_temperature_c": 30.2},
        "weather_result": {"status": "live", "wind": {"speed": 14.0, "direction": "SW"}, "sea_condition": "Moderate"},
        "safety_result": {"risk_level": "low", "proximity": {"status": "inside", "distance_km": 150.0}},
        "marine_analysis_result": {
            "marine_decision": {"recommendation": "CAUTION", "confidence": "moderate"},
            "data_quality": {"overall_reliability": "HIGH"},
            "conflicts": [],
        },
        "evidence": [],
        "risk_level": "moderate",
        "final_answer": "",
        "recommendations": [],
    }

    res = await final_reasoning_agent.reason(state)
    answer = res["final_answer"]
    human_resp = res.get("human_response") or {}
    conds = human_resp.get("conditions") or {}

    # Must contain Current conditions header in text
    assert "Current conditions:" in answer

    # Must have wind, sea, water temp, and safety in structured conditions
    assert "14 knots" in str(conds.get("wind"))
    assert "Moderate" in str(conds.get("sea_state"))
    assert "30°C" in str(conds.get("water_temperature"))
    assert "boundaries" in str(conds.get("safety")).lower() or "safe" in str(conds.get("safety")).lower()
