"""
Tests for IntentRouter & Conversational LLM (Phase 8.1.3).

Validates:
1. Correct intent classification (no hardcoded answers in the router)
2. Safety priority overrides for mixed-intent queries
3. UTILITY classification for time/date queries
4. /api/query integration: casual queries bypass agents, domain queries execute pipeline
5. LLM-generated responses (not hardcoded)
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.intent_router import (
    classify_query_intent,
    QueryIntent,
    normalize_query,
)


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: Intent Classification (Router ONLY classifies, never answers)
# ═══════════════════════════════════════════════════════════════════════════════

def test_normalization():
    assert normalize_query("  Hello, World!!!  ") == "hello world"
    assert normalize_query("Hey... is it safe???") == "hey is it safe"
    assert normalize_query("how's it going?") == "hows it going"
    assert normalize_query("") == ""


class TestGeneralConversation:
    """Greetings and social exchanges must be GENERAL_CONVERSATION."""

    @pytest.mark.parametrize("query", [
        "hi", "hello", "hey", "hii", "hey there",
        "good morning", "Good Morning!", "HELLO", "  hi  ",
        "how are you?", "how's it going?", "what's up",
        "thanks", "thank you", "Thanks!", "much appreciated",
        "ok", "okay", "cool", "got it", "sure",
    ])
    def test_general_conversation(self, query):
        res = classify_query_intent(query)
        assert res.intent == QueryIntent.GENERAL_CONVERSATION, f"Failed for '{query}'"
        assert res.requires_orca_agents is False
        assert res.safety_priority is False


class TestUtility:
    """Time/date queries must be UTILITY."""

    @pytest.mark.parametrize("query", [
        "what time is it?",
        "what's the time right now?",
        "current time",
        "what day is it?",
        "what's the date today?",
    ])
    def test_utility(self, query):
        res = classify_query_intent(query)
        assert res.intent == QueryIntent.UTILITY, f"Failed for '{query}'"
        assert res.requires_orca_agents is False
        assert res.requires_utility is True


class TestOrcaCapability:
    """Questions about ORCA's capabilities must be ORCA_CAPABILITY."""

    @pytest.mark.parametrize("query", [
        "what can you do?",
        "what is ORCA?",
        "how does ORCA work?",
        "what data can you analyze?",
        "what information can you provide?",
    ])
    def test_capability(self, query):
        res = classify_query_intent(query)
        assert res.intent == QueryIntent.ORCA_CAPABILITY, f"Failed for '{query}'"
        assert res.requires_orca_agents is False


class TestMarine:
    """Marine domain queries must be MARINE."""

    @pytest.mark.parametrize("query", [
        "what are the ocean conditions?",
        "what is the weather?",
        "what is the sea state?",
        "show me satellite data",
        "what is the SST?",
        "wind speed near Chennai",
    ])
    def test_marine(self, query):
        res = classify_query_intent(query)
        assert res.intent == QueryIntent.MARINE, f"Failed for '{query}'"
        assert res.requires_orca_agents is True


class TestSafety:
    """Safety queries must be SAFETY with safety_priority=True."""

    @pytest.mark.parametrize("query", [
        "am I safe?",
        "is it safe to travel?",
        "I am in danger",
        "my boat is drifting",
        "emergency",
        "how far am I from the border?",
    ])
    def test_safety(self, query):
        res = classify_query_intent(query)
        assert res.intent == QueryIntent.SAFETY, f"Failed for '{query}'"
        assert res.requires_orca_agents is True
        assert res.safety_priority is True


class TestMixedIntent:
    """Mixed-intent queries must be classified by PRIMARY intent."""

    def test_hello_weather(self):
        res = classify_query_intent("hello, what is the weather?")
        assert res.intent == QueryIntent.MARINE

    def test_hey_sea_safe(self):
        res = classify_query_intent("hey, is the sea safe?")
        assert res.intent == QueryIntent.SAFETY
        assert res.safety_priority is True

    def test_hi_time(self):
        res = classify_query_intent("hi, what time is it?")
        assert res.intent == QueryIntent.UTILITY

    def test_hello_orca_capability(self):
        res = classify_query_intent("hello, what can ORCA do?")
        assert res.intent == QueryIntent.ORCA_CAPABILITY


class TestNoHardcodedAnswers:
    """The router must NOT contain hardcoded answer strings."""

    @pytest.mark.parametrize("query", [
        "hi", "hello", "thanks", "what can you do?", "what time is it?",
        "ok", "good morning", "how are you?",
    ])
    def test_no_direct_response_field(self, query):
        res = classify_query_intent(query)
        # IntentClassification should NOT have a direct_response attribute
        assert not hasattr(res, 'direct_response'), \
            f"Router still contains hardcoded 'direct_response' for '{query}'"


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS: /api/query endpoint behavior
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_greeting_bypasses_agents():
    """'hi' must bypass agents and return a dynamically generated response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/query",
            json={"query": "hi", "session_id": "test-greeting"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Must have an answer (dynamically generated by LLM or fallback)
        assert len(data["answer"]) > 5
        # No agents executed
        assert data["agents_used"] == []
        assert data["evidence"] == []
        assert data["structured_evidence"] == []
        # No domain risk
        assert data["risk_level"] == "none"


@pytest.mark.asyncio
async def test_api_time_query_bypasses_agents():
    """Time queries must bypass agents and use real system time."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/query",
            json={"query": "what time is it?", "session_id": "test-time"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["answer"]) > 5
        assert data["agents_used"] == []
        assert data["risk_level"] == "none"


@pytest.mark.asyncio
async def test_api_marine_query_executes_pipeline():
    """Marine queries must execute the full ORCA multi-agent pipeline."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/query",
            json={
                "query": "What are the ocean conditions?",
                "location": {"lat": 13.08, "lon": 80.27},
                "session_id": "test-marine",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["answer"]) > 30
        assert len(data["agents_used"]) > 0 or len(data["evidence"]) > 0
