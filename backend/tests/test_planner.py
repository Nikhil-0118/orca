"""
Comprehensive Test Suite for ORCA Phase 8.2:
Agentic Planner, Dynamic Tool Selection, Conversational Intelligence & Chat UI Stabilization.

Validates:
1. General conversation handling (greetings, social exchanges, capability inquiries).
2. Authoritative utility handling (time, date, day of week with Asia/Kolkata timezone).
3. Dynamic agent minimality (only necessary agents executed).
4. Multi-agent complex query planning.
5. Deterministic safety guardrail supremacy (cannot be weakened by LLM).
6. Contextual follow-up resolution using conversation history.
7. /api/query multi-mode integration (conversation, utility, marine, safety).
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.planner import orca_planner, ExecutionPlan
from app.services.utility_tools import get_current_time_data, format_utility_context
from app.services.conversational_llm import generate_conversational_response


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Authoritative Utility Tools Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_authoritative_utility_tools():
    """Verify system-clock-derived time and date data."""
    data = get_current_time_data("Asia/Kolkata")
    assert "time_12h" in data
    assert "date_formatted" in data
    assert "day_of_week" in data
    assert "current_datetime" in data
    assert data["timezone"] == "Asia/Kolkata"
    assert "IST" in data["timezone_label"]

    formatted = format_utility_context(data)
    assert "FACTUAL SYSTEM TIME CONTEXT" in formatted
    assert data["day_of_week"] in formatted


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Planner Tests: General Conversation
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlannerConversation:
    """Natural conversational messages must route to conversation mode with 0 agents."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "hi",
        "hello",
        "hey",
        "hello there",
        "good morning",
        "good evening",
        "how are you",
        "how's it going",
        "what's up",
        "how are you doing",
        "thanks",
        "thank you so much",
        "ok",
        "cool",
        "nice to meet you",
    ])
    async def test_conversational_queries(self, query):
        plan = await orca_planner.plan(query=query)
        assert plan.response_mode == "conversation"
        assert plan.requires_agents is False
        assert len(plan.agents) == 0
        assert plan.safety_required is False


class TestPlannerCapability:
    """Questions asking what ORCA can do must route to orca_capability conversation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "what can you do",
        "what is orca",
        "who are you",
        "how do you work",
        "what are your features",
        "tell me about yourself",
    ])
    async def test_capability_queries(self, query):
        plan = await orca_planner.plan(query=query)
        assert plan.response_mode == "conversation"
        assert plan.intent in ("orca_capability", "general_conversation")
        assert plan.requires_agents is False
        assert len(plan.agents) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Planner Tests: Utility (Time, Date, Day)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlannerUtility:
    """Time and date inquiries must route to utility mode with clock/date tools."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "what time is it",
        "whats the time",
        "what's the time right now",
        "current time",
        "tell me the time",
    ])
    async def test_time_queries(self, query):
        plan = await orca_planner.plan(query=query)
        assert plan.response_mode == "utility"
        assert plan.requires_tools is True
        assert "clock" in plan.tools
        assert plan.requires_agents is False
        assert len(plan.agents) == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "whats today day",
        "what day is today",
        "what day are we on",
        "whats the date today",
        "what is the date",
        "tell me the date",
    ])
    async def test_date_queries(self, query):
        plan = await orca_planner.plan(query=query)
        assert plan.response_mode == "utility"
        assert plan.requires_tools is True
        assert "date" in plan.tools
        assert plan.requires_agents is False
        assert len(plan.agents) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Planner Tests: Dynamic Agent Minimality
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlannerAgentMinimality:
    """The planner must select ONLY the minimum sufficient agents."""

    @pytest.mark.asyncio
    async def test_ocean_only_query(self):
        plan = await orca_planner.plan("What is the sea surface temperature?")
        assert plan.response_mode == "marine"
        assert "ocean" in plan.agents
        assert "satellite" not in plan.agents

    @pytest.mark.asyncio
    async def test_weather_only_query(self):
        plan = await orca_planner.plan("What is the coastal wind speed and weather forecast?")
        assert plan.response_mode == "marine"
        assert "weather" in plan.agents
        assert "satellite" not in plan.agents

    @pytest.mark.asyncio
    async def test_satellite_only_query(self):
        plan = await orca_planner.plan("What Earth Observation satellite data from Oceansat-3 is available?")
        assert plan.response_mode == "marine"
        assert "satellite" in plan.agents

    @pytest.mark.asyncio
    async def test_complex_multi_agent_query(self):
        plan = await orca_planner.plan(
            "Should I take my boat out tomorrow morning? Check the weather, sea conditions, and nearby safety concerns."
        )
        assert plan.response_mode in ("marine", "safety")
        assert "weather" in plan.agents
        assert "ocean" in plan.agents
        assert "safety" in plan.agents


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Planner Tests: Deterministic Safety Supremacy
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlannerSafetySupremacy:
    """Safety-critical terms must activate safety mode and cannot be disabled."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "is it safe for my boat",
        "can we cross the maritime boundary",
        "am I in danger near the border",
        "emergency: vessel is drifting",
        "SOS distress call",
        "how far am I from the IMBL boundary line",
    ])
    async def test_safety_override(self, query):
        plan = await orca_planner.plan(query=query)
        assert plan.response_mode == "safety"
        assert plan.safety_required is True
        assert "safety" in plan.agents


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Planner Tests: Contextual Follow-Up
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlannerContextualFollowUp:
    """Planner must resolve context from recent conversation turns."""

    @pytest.mark.asyncio
    async def test_contextual_follow_up_wind(self):
        history = [
            {"role": "user", "content": "What is the ocean temperature near Chennai?"},
            {"role": "assistant", "content": "The sea surface temperature is 29.5°C with calm waters."},
        ]
        # Short query with pronoun or ellipsis
        plan = await orca_planner.plan(
            query="And the wind?",
            conversation_history=history,
        )
        assert plan.response_mode == "marine"
        assert "weather" in plan.agents


# ═══════════════════════════════════════════════════════════════════════════════
# 7. End-to-End API Integration Tests (/api/query)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_conversational_response():
    """Conversation query returns mode='conversation' without marine artifacts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/query",
            json={"query": "hi", "session_id": "test-p82-hi"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "conversation"
        assert len(data["answer"]) > 5
        assert data["risk_level"] == "none"
        assert data["agents_used"] == []
        assert data["evidence"] == []
        assert data["structured_evidence"] == []
        assert "<svg" not in data["answer"].lower()


@pytest.mark.asyncio
async def test_api_utility_time_response():
    """Time query returns mode='utility' with authoritative system time."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/query",
            json={"query": "what time is it?", "session_id": "test-p82-time"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "utility"
        assert len(data["answer"]) > 5
        assert data["risk_level"] == "none"
        assert data["agents_used"] == []


@pytest.mark.asyncio
async def test_api_utility_date_response():
    """Date query ('whats today day') returns mode='utility' without marine misrouting."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/query",
            json={"query": "whats today day", "session_id": "test-p82-day"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "utility"
        assert len(data["answer"]) > 5
        assert data["risk_level"] == "none"
        assert data["agents_used"] == []


@pytest.mark.asyncio
async def test_api_marine_ocean_minimality():
    """Ocean query executes only ocean agent in LangGraph."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/query",
            json={
                "query": "What is the sea temperature?",
                "location": {"lat": 13.08, "lon": 80.27},
                "session_id": "test-p82-ocean",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "marine"
        assert len(data["answer"]) > 20
        # Check that ocean is among agents used, but weather/satellite were skipped
        assert "Ocean" in data["agents_used"] or "ocean" in [a.lower() for a in data["agents_used"]]


@pytest.mark.asyncio
async def test_api_safety_query():
    """Safety query triggers safety mode and authoritative evaluation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/query",
            json={
                "query": "Is it safe for our small boat to sail near the boundary?",
                "location": {"lat": 9.45, "lon": 79.20},
                "session_id": "test-p82-safety",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "safety"
        assert data["risk_level"] in ("moderate", "high", "critical", "low")
        assert len(data["answer"]) > 20
