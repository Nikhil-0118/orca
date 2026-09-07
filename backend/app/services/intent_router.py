"""
Intelligent Query Intent Router for ORCA (Phase 8.1.3).

Classifies incoming queries into intent categories to determine the correct
execution path. The router ONLY classifies — it does NOT generate final answers.

Intent Categories:
  GENERAL_CONVERSATION — casual greetings, social exchanges, how-are-you
  UTILITY              — time, date, and factual system queries
  ORCA_CAPABILITY      — questions about what ORCA can do
  MARINE               — ocean, weather, satellite, coastal domain queries
  SAFETY               — safety, emergency, boundary, danger queries
  UNKNOWN              — low-confidence, ambiguous queries

Priority Hierarchy (highest first):
  1. SAFETY (never miss an emergency)
  2. MARINE (domain queries take precedence over greetings)
  3. UTILITY (time/date queries bypass agents)
  4. ORCA_CAPABILITY (meta questions about ORCA)
  5. GENERAL_CONVERSATION (casual chat)
  6. UNKNOWN (fallback)
"""
import enum
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("orca.intent_router")


class QueryIntent(str, enum.Enum):
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    UTILITY = "UTILITY"
    ORCA_CAPABILITY = "ORCA_CAPABILITY"
    MARINE = "MARINE"
    SAFETY = "SAFETY"
    UNKNOWN = "UNKNOWN"


@dataclass
class IntentClassification:
    intent: QueryIntent
    confidence: float
    requires_orca_agents: bool
    requires_utility: bool
    safety_priority: bool


# ── Precompiled Regex ────────────────────────────────────────────────────────
_APOSTROPHE_RE = re.compile(r"[''`]")
_PUNCT_RE = re.compile(r"[!?,.:;\"()\[\]{}\\/\-_]")
_WS_RE = re.compile(r"\s+")


# ── Safety & Emergency Signals (Highest Priority) ───────────────────────────
SAFETY_SIGNALS = {
    "safe", "safety", "danger", "dangerous", "emergency", "sos", "mayday",
    "help me", "drifting", "sinking", "capsize", "capsized", "distress",
    "hazard", "hazardous", "storm", "cyclone", "gale", "squall",
    "rough sea", "high wave", "tsunami", "boundary", "border", "imbl",
    "crossed", "violation", "restricted", "piracy", "collision",
    "can i sail", "can we sail", "can we cross", "can i depart",
    "should i depart", "is it safe", "is the sea safe", "am i in danger",
    "how far am i", "distance to border", "distance to boundary",
}

# ── Marine & Oceanographic Domain Signals ────────────────────────────────────
MARINE_SIGNALS = {
    "ocean", "marine", "sea", "weather", "forecast", "satellite",
    "sst", "temperature", "wave", "swell", "wind", "knots", "visibility",
    "tide", "tides", "ocean current", "currents", "chlorophyll",
    "incois", "imd", "isro", "bhoonidhi", "erddap",
    "coastal", "harbor", "harbour", "port",
    "chennai", "mumbai", "kochi", "visakhapatnam", "vizag", "tuticorin",
    "palk", "palk strait", "palk bay", "bay of bengal", "arabian sea",
    "indian ocean", "pfz", "potential fishing zone", "fishing zone",
    "tuna", "fish", "fishing", "catch", "boat", "vessel", "ship",
    "trawler", "depth", "bathymetry", "salinity",
}

# ── Utility / System Signals ────────────────────────────────────────────────
UTILITY_SIGNALS = {
    "what time", "whats the time", "current time", "time right now",
    "what day", "whats the date", "todays date", "current date",
    "what date", "time is it", "day is it", "date today",
}

# ── ORCA Capability Signals ─────────────────────────────────────────────────
CAPABILITY_SIGNALS = {
    "what can you do", "who are you", "what is orca", "what are you",
    "how do you work", "how does this work", "how does orca work",
    "what are your features", "what do you do", "tell me about yourself",
    "your capabilities", "what data", "what information",
    "what can orca", "how can you help",
}

# ── General Conversation Patterns ────────────────────────────────────────────
GREETING_PATTERNS = {
    "hi", "hello", "hey", "hii", "hiii", "heyy", "hey there",
    "hello there", "hi there", "good morning", "good afternoon",
    "good evening", "good day", "greetings", "namaste", "vanakkam",
    "hola", "yo",
}

SOCIAL_PATTERNS = {
    "how are you", "hows it going", "how is it going", "whats up",
    "how do you do", "nice to meet you", "howdy",
    "how have you been", "what are you doing", "whats going on",
}

THANKS_PATTERNS = {
    "thanks", "thank you", "thx", "thank u", "thanks a lot",
    "thank you so much", "much appreciated", "appreciate it", "many thanks",
}

CONFIRMATION_PATTERNS = {
    "ok", "okay", "cool", "got it", "sure", "alright", "all right",
    "noted", "fine", "understood", "k", "kk", "great", "awesome",
    "perfect", "sounds good", "nice",
}


def normalize_query(text: str) -> str:
    """Normalize query: lowercase, strip apostrophes, strip punctuation, collapse whitespace."""
    if not text:
        return ""
    lowered = text.lower()
    # Remove apostrophes without space (so "how's" → "hows", not "how s")
    no_apos = _APOSTROPHE_RE.sub("", lowered)
    cleaned = _PUNCT_RE.sub(" ", no_apos)
    return _WS_RE.sub(" ", cleaned).strip()


def _has_signal(normalized: str, signal_set: set) -> Optional[str]:
    """Check if any signal keyword appears in the normalized query."""
    for kw in signal_set:
        if kw in normalized:
            return kw
    return None


def classify_query_intent(raw_query: str) -> IntentClassification:
    """
    Classify the user query into an intent category.

    Returns an IntentClassification with the detected intent and routing flags.
    The router NEVER generates the final answer — only classification metadata.
    """
    normalized = normalize_query(raw_query)

    if not normalized:
        return IntentClassification(
            intent=QueryIntent.GENERAL_CONVERSATION,
            confidence=0.95,
            requires_orca_agents=False,
            requires_utility=False,
            safety_priority=False,
        )

    # ── 1. SAFETY (highest priority — never miss an emergency) ───────────────
    safety_match = _has_signal(normalized, SAFETY_SIGNALS)
    if safety_match:
        logger.info("intent_classified", extra={"intent": "SAFETY", "match": safety_match, "query": raw_query[:60]})
        return IntentClassification(
            intent=QueryIntent.SAFETY,
            confidence=0.97,
            requires_orca_agents=True,
            requires_utility=False,
            safety_priority=True,
        )

    # ── 2. UTILITY (time/date bypass agents — checked before marine to avoid
    #    false positives on words like "current") ──────────────────────────────
    utility_match = _has_signal(normalized, UTILITY_SIGNALS)
    if utility_match:
        logger.info("intent_classified", extra={"intent": "UTILITY", "match": utility_match, "query": raw_query[:60]})
        return IntentClassification(
            intent=QueryIntent.UTILITY,
            confidence=0.94,
            requires_orca_agents=False,
            requires_utility=True,
            safety_priority=False,
        )

    # ── 3. MARINE (domain queries take precedence over greetings) ────────────
    marine_match = _has_signal(normalized, MARINE_SIGNALS)
    if marine_match:
        logger.info("intent_classified", extra={"intent": "MARINE", "match": marine_match, "query": raw_query[:60]})
        return IntentClassification(
            intent=QueryIntent.MARINE,
            confidence=0.95,
            requires_orca_agents=True,
            requires_utility=False,
            safety_priority=False,
        )

    # ── 4. ORCA_CAPABILITY (meta questions about ORCA) ───────────────────────
    capability_match = _has_signal(normalized, CAPABILITY_SIGNALS)
    if capability_match:
        logger.info("intent_classified", extra={"intent": "ORCA_CAPABILITY", "match": capability_match, "query": raw_query[:60]})
        return IntentClassification(
            intent=QueryIntent.ORCA_CAPABILITY,
            confidence=0.93,
            requires_orca_agents=False,
            requires_utility=False,
            safety_priority=False,
        )

    # ── 5. GENERAL_CONVERSATION (casual greetings & social) ──────────────────
    is_greeting = normalized in GREETING_PATTERNS or any(
        normalized.startswith(g + " ") for g in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
    )
    is_social = normalized in SOCIAL_PATTERNS or _has_signal(normalized, {"how are you", "hows it going", "whats up", "nice to meet"})
    is_thanks = normalized in THANKS_PATTERNS
    is_confirmation = normalized in CONFIRMATION_PATTERNS

    if is_greeting or is_social or is_thanks or is_confirmation:
        logger.info("intent_classified", extra={"intent": "GENERAL_CONVERSATION", "query": raw_query[:60]})
        return IntentClassification(
            intent=QueryIntent.GENERAL_CONVERSATION,
            confidence=0.92,
            requires_orca_agents=False,
            requires_utility=False,
            safety_priority=False,
        )

    # ── 6. UNKNOWN (fallback — route to conversational LLM for clarification) ─
    logger.info("intent_classified", extra={"intent": "UNKNOWN", "query": raw_query[:60]})
    return IntentClassification(
        intent=QueryIntent.UNKNOWN,
        confidence=0.5,
        requires_orca_agents=False,
        requires_utility=False,
        safety_priority=False,
    )
