"""
Agentic Query Planner for ORCA (Phase 8.2).

Dynamically evaluates user intent, dialog context, and available tools/agents.
Selects the minimum necessary capability set rather than forcing fixed categories
or hardcoded responses.
"""
from dataclasses import dataclass, field
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.llm_provider import get_llm_provider

logger = logging.getLogger("orca.services.planner")

# ── Available Capability Registry ────────────────────────────────────────────
AVAILABLE_CAPABILITIES = {
    "ocean": "Retrieves ocean temperature, SST anomalies, waves, currents, and ocean conditions from INCOIS ERDDAP.",
    "weather": "Retrieves coastal weather, wind vectors, visibility, precipitation, and IMD advisories.",
    "satellite": "Retrieves Earth Observation metadata, cloud cover, and Oceansat-3 (EOS-06) observations.",
    "safety": "Calculates geodesic boundary proximity (IMBL), geofence alerts, and maritime restriction states.",
    "rag": "Queries maritime regulatory knowledge base, UNCLOS guidelines, and navigational advisories.",
    "clock": "Retrieves authoritative current time (Asia/Kolkata / IST).",
    "date": "Retrieves authoritative current date and day of week.",
    "location": "Retrieves current vessel coordinates, geographic region name, and operational positioning.",
    "conversation": "Handles general dialogue, greetings, capability overviews, and conversational inquiries.",
}

# ── Safety & Emergency Signals (Deterministic Guardrail Override) ─────────────
SAFETY_OVERRIDE_SIGNALS = {
    "risk", "risks", "risk level", "risk near", "safe", "safety", "danger", "dangerous",
    "emergency", "sos", "mayday", "help me", "drifting", "sinking", "capsize", "capsized",
    "distress", "hazard", "hazardous", "storm", "cyclone", "gale", "squall",
    "rough sea", "high wave", "tsunami", "boundary", "border", "imbl",
    "crossed", "violation", "restricted", "piracy", "collision",
    "can i sail", "can we sail", "can we cross", "can i depart",
    "should i depart", "is it safe", "is the sea safe", "am i in danger",
    "how far am i", "distance to border", "distance to boundary",
}

# ── Planner System Prompt ───────────────────────────────────────────────────
PLANNER_SYSTEM_PROMPT = """You are ORCA's Agentic Query Planner.

Your task is to understand the user's plain-language request and determine the MINIMUM information, tools, and specialized agents required to answer it accurately.

Available Capabilities:
1. "ocean": INCOIS Sea surface temperature, SST anomaly, waves, swell, ocean currents, surface conditions.
2. "weather": IMD Coastal weather, wind speed/direction, visibility, precipitation, storm warnings.
3. "satellite": ISRO Oceansat-3 (EOS-06) Earth Observation, cloud cover, satellite observations.
4. "safety": Maritime boundaries, IMBL, geofencing, restricted zones, collision/hazard proximity.
5. "ecosystem": ISRO MOSDAC OCM-3 Chlorophyll-a density, ocean color, phytoplankton activity, and marine trophic state.
6. "rag": Maritime regulations, safety guidelines, reference documentation.
7. "clock": Authoritative current time tool.
8. "date": Authoritative current date and day of week tool.
9. "location": Authoritative current vessel location and geographic region tool.
10. "conversation": General dialogue, greetings, social exchange, or questions about what ORCA is and can do.

Rules & Invariants:
- AGENT MINIMALITY: Select ONLY the capabilities strictly necessary.
  - "What is the sea temperature?" -> intent: "SEA_SURFACE_TEMPERATURE", response_mode: "marine", agents: ["ocean"]
  - "What is the temperature in my location?" -> intent: "AIR_TEMPERATURE", response_mode: "marine", agents: ["weather"]
  - "Temperature in Gujarat" -> intent: "AIR_TEMPERATURE", response_mode: "marine", agents: ["weather"]
  - "Weather in Mumbai" -> intent: "WEATHER", response_mode: "marine", agents: ["weather"]
  - "Wave conditions near Dwarka" -> intent: "MARINE_CONDITIONS", response_mode: "marine", agents: ["ocean"]
  - "Nearest ocean to Gujarat" -> intent: "NEAREST_OCEAN", response_mode: "utility", tools: ["location"]
  - "Nearest ocean near me" -> intent: "NEAREST_OCEAN", response_mode: "utility", tools: ["location"]
  - "Where is my location?" -> intent: "LOCATION_CURRENT", response_mode: "utility", tools: ["location"]
  - "Is it safe for a small fishing boat?" -> intent: "marine_safety", response_mode: "safety", agents: ["ocean", "weather", "safety"]
- TEMPERATURE ROUTING RULE:
  - Ordinary air temperature ("temperature in my location", "temperature here", "temperature in Mumbai", "temperature in Gujarat") MUST route to the Weather Agent ("weather"). Never allow the Ocean Agent to answer ordinary air temperature questions.
  - Sea surface temperature ("sea surface temperature", "sea temperature near Gujarat", "SST") MUST route to the Ocean Agent ("ocean").
- CONVERSATION: Casual greetings ("hi", "hello", "how are you", "what's up", "thanks") or meta questions ("what can you do", "who are you") DO NOT need marine agents. response_mode must be "conversation".
- UTILITY: Questions asking for the current time, date, or day ("what time is it", "whats today day", "what is the date") need "clock" or "date" tools, NEVER marine agents. response_mode must be "utility".
- LOCATION: Questions asking for current position or location ("what is my current location", "where am I", "what is my position") need "location" tool, response_mode must be "utility", intent must be "LOCATION_CURRENT". Do NOT trigger ocean or weather agents unless the user also asked about conditions.
- NEAREST OCEAN & COAST PROXIMITY: Questions asking for the nearest ocean, closest sea, nearest coast, distance to the ocean ("where is the nearest ocean", "nearest ocean to Gujarat", "which ocean is near Chennai", "ocean near Dwarka") need "location" tool, response_mode must be "utility", and intent must be "NEAREST_OCEAN". Do NOT trigger marine agents (ocean, weather, safety) unless the user specifically asks about wave, sea-state, or navigation clearance.
- OCEAN PROXIMITY: Questions asking if there is an ocean nearby ("is there an ocean nearby", "is there an ocean near me", "are there oceans nearby") need "location" tool, response_mode must be "utility", and intent must be "ocean_proximity".
- WATER BODY: Questions asking for the nearest water body ("what is the nearest water body", "nearest river") need "location" tool, response_mode must be "utility", and intent must be "nearest_water_body".
- FISHING INQUIRIES:
  - Questions asking where to find fish, fishing spots, or fishing suitability (e.g. "Where can I find the maximum fish near Mumbai?", "Can I go fishing?", "Give me a fishing spot near Kochi", "Best fishing spot near Mumbai") MUST route to marine analysis: intent: "marine_analysis", response_mode: "marine", agents: ["ocean", "weather", "safety", "ecosystem"]. NEVER route substantive fishing inquiries to conversation mode.
- MAP & ROUTE DISPLAY FOLLOW-UP:
  - Questions asking explicitly for a route, directions, or map navigation follow-up (e.g. "can u give me the route", "give me the route", "show me the route", "how do I get there", "how can I reach there", "navigate there", "give the map", "show the map", "where is it", "map it") need "location" tool, response_mode: "conversation", intent: "map_display" or "marine_route".
  - Do NOT trigger ocean, weather, or ecosystem agents for map/route display follow-ups unless the user specifically asks about weather or wave conditions along the route.
- CONTEXTUAL FOLLOW-UP: If conversation history is provided, resolve references. Example: If previous discussion was about ocean temperature and the user asks "And the wind?", route to "weather" agent.

Return ONLY a valid JSON object with this exact structure:
{
  "intent": "LOCATION_CURRENT | LOCATION_LOOKUP | NEAREST_OCEAN | NEAREST_COAST | WEATHER | AIR_TEMPERATURE | SEA_SURFACE_TEMPERATURE | MARINE_CONDITIONS | ocean_proximity | nearest_water_body | general_conversation | orca_capability | marine_analysis | marine_safety | map_display | marine_route | fishing_destination | clarification",
  "response_mode": "conversation | utility | marine | safety",
  "requires_tools": true | false,
  "tools": ["clock" | "date" | "location"],
  "requires_agents": true | false,
  "agents": ["ocean" | "weather" | "satellite" | "safety" | "rag" | "ecosystem"],
  "safety_required": true | false,
  "confidence": 0.0 to 1.0,
  "reasoning_summary": "1-sentence internal summary of plan"
}"""


@dataclass
class ExecutionPlan:
    intent: str
    response_mode: str  # "conversation" | "utility" | "marine" | "safety"
    requires_tools: bool = False
    tools: List[str] = field(default_factory=list)
    requires_agents: bool = False
    agents: List[str] = field(default_factory=list)
    safety_required: bool = False
    confidence: float = 0.9
    reasoning_summary: Optional[str] = None


class ORCAPlanner:
    """Agentic query planner for dynamic capability and agent selection."""

    def __init__(self):
        self.provider = get_llm_provider()

    async def plan(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        location: Optional[Dict[str, float]] = None,
    ) -> ExecutionPlan:
        """
        Produce a structured execution plan for the query.
        Uses LLM planning with context awareness and deterministic safety override.
        """
        # 1. Check deterministic safety override first (authoritative safety guardrail)
        normalized = self._normalize(query)
        safety_detected = any(sig in normalized for sig in SAFETY_OVERRIDE_SIGNALS)

        # 2. Attempt dynamic LLM planning if provider is available
        llm_plan = await self._plan_with_llm(query, conversation_history, location)
        if llm_plan is not None:
            # Enforce safety guardrail if safety signal detected
            if safety_detected:
                llm_plan.safety_required = True
                llm_plan.response_mode = "safety"
                llm_plan.requires_agents = True
                if "safety" not in llm_plan.agents:
                    llm_plan.agents.append("safety")
            else:
                # Check for follow-up map or routing intent to prevent misrouting to general marine analysis
                fallback_plan = self._plan_fallback(query, conversation_history, location, safety_detected)
                if fallback_plan.intent in ("fishing_destination", "marine_route", "map_display") and fallback_plan.response_mode == "conversation":
                    llm_plan = fallback_plan

            self._log_plan(llm_plan)
            return llm_plan

        # 3. Fallback to resilient semantic deterministic planner
        fallback_plan = self._plan_fallback(query, conversation_history, location, safety_detected)
        self._log_plan(fallback_plan, is_fallback=True)
        return fallback_plan

    async def _plan_with_llm(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]],
        location: Optional[Dict[str, float]],
    ) -> Optional[ExecutionPlan]:
        """Query the LLM for a structured JSON plan."""
        provider = get_llm_provider()
        if not provider:
            return None

        # Format context
        context_parts = []
        if history:
            recent = history[-4:]
            formatted_history = "\n".join(
                f"{turn.get('role', 'user')}: {turn.get('content', '')[:120]}" for turn in recent
            )
            context_parts.append(f"Recent Conversation History:\n{formatted_history}")

        if location:
            context_parts.append(f"Vessel Coordinates: lat={location.get('lat')}, lon={location.get('lon')}")

        context_str = "\n\n".join(context_parts)
        user_payload = f"USER QUERY: {query}\n\n{context_str}" if context_str else f"USER QUERY: {query}"

        try:
            raw_response = await provider.generate(
                system_prompt=PLANNER_SYSTEM_PROMPT,
                user_payload=user_payload,
                temperature=0.0,
                max_tokens=256,
            )

            if not raw_response:
                return None

            # Parse JSON out of response
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            parsed = json.loads(cleaned)
            return self._build_plan_from_dict(parsed)

        except Exception as e:
            logger.warning(f"LLM planner failed, falling back: {type(e).__name__}: {e}")
            return None

    def _build_plan_from_dict(self, data: Dict[str, Any]) -> ExecutionPlan:
        """Construct ExecutionPlan from parsed LLM dictionary with validation."""
        intent = str(data.get("intent", "marine_analysis"))
        mode = str(data.get("response_mode", "marine")).lower()
        if mode not in ("conversation", "utility", "marine", "safety"):
            mode = "marine"

        tools = [
            str(t).lower()
            for t in data.get("tools", [])
            if str(t).lower() in ("clock", "date", "datetime", "location")
        ]
        agents = [
            str(a).lower()
            for a in data.get("agents", [])
            if str(a).lower() in ("ocean", "weather", "satellite", "marine_ecosystem", "ecosystem", "eo")
        ]

        # ── Intent Normalization & Strict Guardrails ──
        norm_intent = intent.upper()
        if norm_intent in ("AIR_TEMPERATURE", "TEMPERATURE", "AIR_TEMP") or (
            any(w in intent.lower() for w in ["temperature", "temp"])
            and not any(w in intent.lower() for w in ["sea", "sst", "ocean", "water"])
        ):
            intent = "AIR_TEMPERATURE"
            mode = "marine"
            if "ocean" in agents:
                agents.remove("ocean")
            if "weather" not in agents:
                agents.append("weather")

        elif norm_intent in ("SEA_SURFACE_TEMPERATURE", "SST", "SEA_TEMPERATURE", "WATER_TEMPERATURE"):
            intent = "SEA_SURFACE_TEMPERATURE"
            mode = "marine"
            if "weather" in agents and len(agents) == 1:
                agents.remove("weather")
            if "ocean" not in agents:
                agents.append("ocean")

        elif norm_intent in ("NEAREST_OCEAN", "NEAREST_COAST"):
            intent = "nearest_ocean"
            mode = "utility"
            tools = ["location"]
            requires_tools = True
            requires_agents = False
            agents = []

        elif norm_intent in ("LOCATION_CURRENT", "LOCATION"):
            intent = "LOCATION_CURRENT"
            mode = "utility"
            tools = ["location"]
            requires_tools = True
            requires_agents = False
            agents = []

        elif norm_intent in ("MAP_DISPLAY", "MARINE_ROUTE", "ROUTE"):
            intent = "marine_route" if "route" in str(data.get("intent", "")).lower() else "map_display"
            mode = "conversation"
            tools = ["location"]
            requires_tools = True
            requires_agents = False
            agents = []

        elif norm_intent in ("FISHING_DESTINATION", "FISHING_RECOMMENDATION", "FISHING_SPOT", "FISHING"):
            intent = "marine_analysis"
            mode = "marine"
            for ag in ("ocean", "weather", "safety", "ecosystem", "satellite"):
                if ag not in agents:
                    agents.append(ag)

        elif norm_intent == "WEATHER":
            intent = "WEATHER"
            mode = "marine"
            if "weather" not in agents:
                agents.append("weather")

        elif norm_intent == "MARINE_CONDITIONS":
            intent = "MARINE_CONDITIONS"
            mode = "marine"
            if "ocean" not in agents:
                agents.append("ocean")

        requires_tools = bool(data.get("requires_tools", bool(tools)))
        requires_agents = bool(data.get("requires_agents", bool(agents)))
        safety_required = bool(data.get("safety_required", mode == "safety"))

        if mode == "safety":
            safety_required = True
            requires_agents = True
            if "safety" not in agents:
                agents.append("safety")

        return ExecutionPlan(
            intent=intent,
            response_mode=mode,
            requires_tools=requires_tools,
            tools=tools,
            requires_agents=requires_agents,
            agents=agents,
            safety_required=safety_required,
            confidence=float(data.get("confidence", 0.9)),
            reasoning_summary=data.get("reasoning_summary"),
        )

    def _plan_fallback(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]],
        location: Optional[Dict[str, float]],
        safety_detected: bool,
    ) -> ExecutionPlan:
        """
        Semantic rule-based fallback planner.
        Ensures high reliability without requiring hundreds of fixed phrases.
        """
        normalized = self._normalize(query)

        # 1. Safety always takes highest precedence
        if safety_detected:
            agents = ["safety"]
            # Check if weather or ocean should accompany safety
            if any(w in normalized for w in ["wind", "storm", "cyclone", "wave", "weather"]):
                agents.append("weather")
            if any(w in normalized for w in ["sea", "wave", "swell", "water", "temp", "ocean"]):
                agents.append("ocean")

            return ExecutionPlan(
                intent="marine_safety",
                response_mode="safety",
                requires_tools=False,
                tools=[],
                requires_agents=True,
                agents=list(dict.fromkeys(agents)),
                safety_required=True,
                confidence=0.95,
                reasoning_summary="Deterministic safety override activated based on navigational safety terms.",
            )

        # 2a. Nearest Ocean & Coastal Proximity Intelligence (Phase A.1.2)
        nearest_ocean_phrases = [
            "nearest ocean", "closest ocean", "nearest sea", "closest sea",
            "nearest coast", "closest coast", "nearest coastline", "closest coastline",
            "where is the nearest ocean", "where is the closest ocean",
            "which ocean is nearest", "which ocean is closest", "which sea is nearest",
            "which sea is closest", "how far is the ocean", "how far is the sea",
            "how far is the coast", "how far to the ocean", "how far to the coast",
            "distance to the ocean", "distance to ocean", "distance to sea",
            "distance to the sea", "distance to coast", "distance to the coast",
            "distance to coastline", "ocean from here", "sea from here", "coast from here",
            "which ocean is near", "which sea is near",
            "which ocean is closest to", "ocean closest to",
        ]
        is_explicit_ocean_target = bool(re.search(r"\b(?:ocean|sea)\s+(?:near|to)\s+[a-z]", normalized))
        is_nearest_ocean = (any(p in normalized for p in nearest_ocean_phrases) or is_explicit_ocean_target)

        # Proximity boolean question ("is there an ocean nearby")
        ocean_proximity_phrases = [
            "is there an ocean nearby", "is there an ocean near me", "is there an ocean near here",
            "is there any ocean nearby", "are there any oceans nearby", "are there oceans nearby",
            "is there a sea nearby", "is there sea nearby", "ocean nearby me", "oceans nearby me",
            "sea nearby me", "any ocean nearby",
        ]
        is_ocean_proximity = any(p in normalized for p in ocean_proximity_phrases) and not any(w in normalized for w in ["nearest", "closest", "where", "how far", "which ocean"])

        # Water body question ("what is the nearest water body")
        water_body_phrases = [
            "nearest water body", "closest water body", "nearest waterbody", "closest waterbody",
            "nearest river", "closest river", "what is the nearest water body", "which water body is nearest",
        ]
        is_water_body = any(p in normalized for p in water_body_phrases)

        if is_nearest_ocean and not any(w in normalized for w in ["wave", "forecast", "safe", "danger", "risk", "border"]):
            return ExecutionPlan(
                intent="nearest_ocean",
                response_mode="utility",
                requires_tools=True,
                tools=["location"],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.98,
                reasoning_summary="Geospatial nearest ocean and coastal proximity inquiry requested.",
            )

        if is_ocean_proximity and not any(w in normalized for w in ["wave", "forecast", "safe", "danger", "risk", "border"]):
            return ExecutionPlan(
                intent="ocean_proximity",
                response_mode="utility",
                requires_tools=True,
                tools=["location"],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.96,
                reasoning_summary="Ocean proximity presence inquiry requested.",
            )

        if is_water_body and not any(w in normalized for w in ["wave", "forecast", "safe", "danger", "risk", "border"]):
            return ExecutionPlan(
                intent="nearest_water_body",
                response_mode="utility",
                requires_tools=True,
                tools=["location"],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.95,
                reasoning_summary="Nearest water body inquiry requested.",
            )

        # 2b. Map & Marine Route Display Follow-Up ("can u give me the route", "give me the route", "show the route", "how do I get there", "give the map", etc.)
        map_and_route_signals = [
            "give the route", "give me the route", "can you give me the route", "can u give me the route",
            "show the route", "show me the route", "how do i get there", "how can i get there",
            "how do i reach there", "how can i reach there", "navigate there", "take me there",
            "route to it", "give me directions", "give directions", "show directions",
            "show me directions", "directions to it", "directions there",
            "how do i reach that fishing spot", "how can i reach that fishing spot",
            "how do i reach the fishing spot", "how to get there", "how to reach there",
            "give the map", "give me the map", "give me map", "give map",
            "show the map", "show me the map", "show me map", "show map",
            "open the map", "open map", "map it", "where is it", "show me there",
            "show location", "show me that location", "show the fishing spot", "show me the fishing spot",
            "display the map", "display map", "view the map", "view map",
        ]
        is_route_or_map = any(sig in normalized for sig in map_and_route_signals) or any(
            re.search(pat, normalized) for pat in [
                r"(?:can\s+(?:you|u)\s+)?(?:give|show)\s+(?:me\s+)?(?:the\s+|a\s+)?route\b",
                r"\bhow\s+(?:do|can)\s+i\s+(?:get|reach)\s+there\b",
                r"\bhow\s+(?:do|can)\s+i\s+reach\s+(?:that|the)\s+(?:fishing\s+)?(?:spot|location|ground|place)\b",
                r"\bnavigate\s+there\b",
                r"\btake\s+me\s+there\b",
                r"\broute\s+to\s+it\b",
                r"\b(?:give|show)\s+(?:me\s+)?directions\b",
            ]
        )
        if is_route_or_map and not any(w in normalized for w in ["wave", "forecast", "safe", "danger", "risk", "border", "imbl"]):
            is_fishing_thread = False
            if history:
                for turn in reversed(history[-6:]):
                    c = turn.get("content", "").lower()
                    if any(w in c for w in ["fish", "fishing", "fisherman", "pfz", "spot", "ground"]):
                        is_fishing_thread = True
                        break
            if any(w in normalized for w in ["fish", "fishing", "spot"]):
                is_fishing_thread = True

            is_routing = any(w in normalized for w in ["route", "direction", "navigate", "reach", "get there"])
            if is_fishing_thread:
                followup_intent = "fishing_destination"
            elif is_routing:
                followup_intent = "marine_route"
            else:
                followup_intent = "map_display"

            return ExecutionPlan(
                intent=followup_intent,
                response_mode="conversation",
                requires_tools=True,
                tools=["location"],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.98,
                reasoning_summary="Interactive map and marine route follow-up requested.",
            )

        # 2c. Location Utility
        location_signals = [
            "my location", "current location", "where am i", "my position",
            "current position", "what is my location", "area near me", "what location", "where is my location",
        ]
        is_location = any(sig in normalized for sig in location_signals)

        if is_location and not any(w in normalized for w in ["risk", "safe", "safety", "danger", "hazard", "border", "boundary", "fish", "fishing", "weather", "wind", "sea", "wave", "temp", "temperature", "ocean"]):
            return ExecutionPlan(
                intent="location",
                response_mode="utility",
                requires_tools=True,
                tools=["location"],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.96,
                reasoning_summary="Current vessel location inquiry requested.",
            )

        # ── 2c. Domain Specific Intent Routing: Temperature, Weather, Marine Conditions ──
        # A. Sea Surface Temperature (SST) -> Ocean Agent
        sst_signals = [
            "sea surface temperature", "sea surface temp", "sea surface temperatures",
            "sea temperature", "sea temperatures", "sea temp", "water temperature",
            "ocean temperature", "ocean temp", "sst",
        ]
        is_sst = any(re.search(r"\b" + re.escape(sig) + r"\b", normalized) for sig in sst_signals)

        # B. Air Temperature -> Weather Agent (Ocean Agent must NEVER answer ordinary air temperature)
        air_temp_signals = ["air temperature", "temperature", "temp", "how hot", "how cold"]
        has_air_temp_word = any(re.search(r"\b" + re.escape(sig) + r"\b", normalized) for sig in air_temp_signals)
        is_air_temp = has_air_temp_word and not is_sst and not any(w in normalized for w in ["sea", "ocean", "water", "sst", "marine surface"])

        # C. Marine Conditions -> Ocean Agent
        marine_cond_signals = [
            "wave conditions", "wave condition", "sea state", "wave", "waves", "swell",
            "ocean current", "ocean currents", "wave height", "wave heights", "marine conditions",
        ]
        is_marine_cond = any(sig in normalized for sig in marine_cond_signals) and not any(w in normalized for w in ["rain", "storm", "cyclone"])

        # D. Coastal Weather -> Weather Agent
        weather_signals = ["weather", "wind", "winds", "forecast", "visibility", "rain", "precipitation", "storm", "cyclone", "squall"]
        is_weather = any(w in normalized for w in weather_signals) and not is_sst and not is_air_temp and not is_marine_cond

        if is_sst:
            return ExecutionPlan(
                intent="SEA_SURFACE_TEMPERATURE",
                response_mode="marine",
                requires_tools=False,
                tools=[],
                requires_agents=True,
                agents=["ocean"],
                safety_required=False,
                confidence=0.98,
                reasoning_summary="Sea Surface Temperature (SST) inquiry routed to Ocean Agent.",
            )

        if is_air_temp:
            return ExecutionPlan(
                intent="AIR_TEMPERATURE",
                response_mode="marine",
                requires_tools=False,
                tools=[],
                requires_agents=True,
                agents=["weather"],
                safety_required=False,
                confidence=0.98,
                reasoning_summary="Air temperature inquiry routed strictly to Weather Agent.",
            )

        if is_marine_cond:
            marine_agents = ["ocean", "weather"] if any(w in normalized for w in ["marine conditions", "marine condition"]) else ["ocean"]
            return ExecutionPlan(
                intent="MARINE_CONDITIONS",
                response_mode="marine",
                requires_tools=False,
                tools=[],
                requires_agents=True,
                agents=marine_agents,
                safety_required=False,
                confidence=0.96,
                reasoning_summary="Marine conditions inquiry routed to Ocean and Weather Agents.",
            )

        if is_weather:
            return ExecutionPlan(
                intent="WEATHER",
                response_mode="marine",
                requires_tools=False,
                tools=[],
                requires_agents=True,
                agents=["weather"],
                safety_required=False,
                confidence=0.96,
                reasoning_summary="Coastal weather inquiry routed to Weather Agent.",
            )

        # 3. Time / Date Utility (excluding activity timing like "what time is best for fishing")
        time_signals = ["what time is it", "whats the time", "current time", "time right now", "tell me the time"]
        date_signals = [
            "what day", "whats today day", "whats the date", "what is the date", "what date",
            "day is today", "date today", "what day are we on", "todays date", "tell me the date",
            "tell me today", "the date",
        ]

        is_activity_timing = any(w in normalized for w in ["fish", "fishing", "sail", "sailing", "depart", "departure", "trip", "travel", "sea", "boat", "best time"])
        is_time = (any(sig in normalized for sig in time_signals) or (normalized.strip() in ("time", "what time", "the time"))) and not is_activity_timing
        is_date = any(sig in normalized for sig in date_signals)

        if is_time and is_date:
            return ExecutionPlan(
                intent="utility",
                response_mode="utility",
                requires_tools=True,
                tools=["clock", "date"],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.96,
                reasoning_summary="Combined current time and date utility requested.",
            )
        elif is_time:
            return ExecutionPlan(
                intent="utility",
                response_mode="utility",
                requires_tools=True,
                tools=["clock"],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.96,
                reasoning_summary="Current time utility requested.",
            )
        elif is_date:
            return ExecutionPlan(
                intent="utility",
                response_mode="utility",
                requires_tools=True,
                tools=["date"],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.96,
                reasoning_summary="Current date/day utility requested.",
            )

        # 4. Conversational inquiries & Greetings
        greeting_words = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings", "namaste", "vanakkam"]
        social_phrases = ["how are you", "hows it going", "whats up", "how do you do", "nice to meet you", "how are things", "whats happening"]
        thanks_words = ["thanks", "thank you", "thx", "thank u", "much appreciated"]
        confirm_words = ["ok", "okay", "cool", "got it", "sure", "alright", "perfect", "sounds good"]
        capability_phrases = ["what can you do", "who are you", "what is orca", "how do you work", "what are your capabilities", "tell me about yourself", "how can you help"]

        # Check if conversation only
        is_greeting = any(normalized == g or normalized.startswith(g + " ") for g in greeting_words)
        is_social = any(s in normalized for s in social_phrases)
        is_thanks = any(normalized == t for t in thanks_words)
        is_confirm = any(normalized == c for c in confirm_words)
        is_capability = any(c in normalized for c in capability_phrases)

        # Check if marine terms are present to distinguish "hello, what is the weather?"
        ocean_terms = ["sst", "sea surface", "currents", "ocean current", "wave", "waves", "swell"]
        weather_terms = ["weather", "wind", "winds", "knots", "forecast", "visibility", "rain", "precipitation", "storm", "temperature", "temp", "air temperature"]
        satellite_terms = ["satellite", "oceansat", "eos-06", "eos06", "earth observation", "cloud cover", "bhoonidhi", "imagery"]
        ecosystem_terms = ["chlorophyll", "phytoplankton", "plankton", "algae", "algal", "ecosystem", "trophic", "productivity", "pfz", "potential fishing zone"]
        marine_context_terms = [
            "ocean", "marine", "sea", "coastal", "harbor", "port", "fish", "fishing",
            "vessel", "boat", "sail", "chennai", "palk", "bay of bengal", "arabian sea",
            "environment", "sri lanka", "sri lankan", "channel", "strait", "gulf",
        ]

        has_ocean = any(w in normalized for w in ocean_terms)
        has_weather = any(w in normalized for w in weather_terms)
        has_satellite = any(w in normalized for w in satellite_terms)
        has_ecosystem = any(w in normalized for w in ecosystem_terms)
        has_marine_general = any(w in normalized for w in marine_context_terms) or is_activity_timing

        # Conversational / Capability (no marine query attached)
        if (is_greeting or is_social or is_thanks or is_confirm or is_capability) and not (has_ocean or has_weather or has_satellite or has_ecosystem or has_marine_general):
            intent = "orca_capability" if is_capability else "general_conversation"
            return ExecutionPlan(
                intent=intent,
                response_mode="conversation",
                requires_tools=False,
                tools=[],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.92,
                reasoning_summary="Conversational exchange; no external agents or tools required.",
            )

        # 5. Contextual Follow-Up
        # e.g., User: "And the wind?" or "What about Chennai?" after previous marine query
        has_context_fishing = False
        if history and len(normalized.split()) <= 6 and not (has_ocean or has_weather or has_satellite or has_ecosystem):
            recent_text = " ".join(t.get("content", "").lower() for t in history[-4:])
            if any(t in recent_text for t in ["fish", "fishing", "fisherman", "pfz", "spot", "ground"]):
                has_context_fishing = True
                has_marine_general = True
            elif any(t in recent_text for t in ["ocean", "weather", "sea", "wave", "temp", "sri lanka", "chlorophyll"]):
                if "wind" in normalized:
                    has_weather = True
                elif "chlorophyll" in normalized or "plankton" in normalized:
                    has_ecosystem = True
                elif "fish" in normalized or "fishing" in normalized:
                    has_marine_general = True
                else:
                    has_ocean = True

        # 6. Dynamic Agent Selection (Minimality)
        selected_agents = []
        if has_ocean:
            selected_agents.append("ocean")
        if has_weather:
            selected_agents.append("weather")
        if has_satellite:
            selected_agents.append("satellite")
        if has_ecosystem:
            if "satellite" not in selected_agents:
                selected_agents.append("satellite")
            selected_agents.append("ecosystem")

        if any(w in normalized for w in ["fish", "fishes", "fishing", "pfz"]) or has_context_fishing:
            if "ocean" not in selected_agents:
                selected_agents.append("ocean")
            if "weather" not in selected_agents:
                selected_agents.append("weather")
            if "safety" not in selected_agents:
                selected_agents.append("safety")
            if "ecosystem" not in selected_agents:
                selected_agents.append("ecosystem")
            if "satellite" not in selected_agents:
                selected_agents.append("satellite")

        if any(w in normalized for w in ["sri lanka", "sri lankan", "palk"]):
            if "safety" not in selected_agents:
                selected_agents.append("safety")
            if "ocean" not in selected_agents:
                selected_agents.append("ocean")

        if not selected_agents and has_marine_general:
            selected_agents.append("ocean")
            selected_agents.append("weather")

        if not selected_agents:
            # Ambiguous / General query fallback
            return ExecutionPlan(
                intent="general_conversation",
                response_mode="conversation",
                requires_tools=False,
                tools=[],
                requires_agents=False,
                agents=[],
                safety_required=False,
                confidence=0.7,
                reasoning_summary="No specific domain agents detected; routed to conversational path.",
            )

        return ExecutionPlan(
            intent="marine_analysis",
            response_mode="marine",
            requires_tools=False,
            tools=[],
            requires_agents=True,
            agents=selected_agents,
            safety_required=False,
            confidence=0.92,
            reasoning_summary=f"Selected minimal agent capabilities: {selected_agents}",
        )

    def _normalize(self, text: str) -> str:
        """Normalize query text: lowercase, remove apostrophes, strip punctuation."""
        if not text:
            return ""
        lowered = text.lower()
        no_apos = re.sub(r"[''`]", "", lowered)
        cleaned = re.sub(r"[!?,.:;\"()\[\]{}\\/\-_]", " ", no_apos)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _log_plan(self, plan: ExecutionPlan, is_fallback: bool = False) -> None:
        """Developer/server log for observability."""
        src = "Fallback Planner" if is_fallback else "LLM Planner"
        logger.info(
            f"[{src}] Intent: {plan.intent} | Mode: {plan.response_mode} | "
            f"Tools: {plan.tools} | Agents: {plan.agents} | Safety: {plan.safety_required}"
        )


# Global singleton instance
orca_planner = ORCAPlanner()
