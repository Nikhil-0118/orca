"""
Master Orchestrator Agent.
Parses natural language intent, determines which specialist agents to invoke,
executes agent analyses concurrently, and synthesizes one reasoned, explained response.
"""
import asyncio
from typing import Dict, List
from app.agents.fishing_zone_agent import FishingZoneAgent
from app.agents.ocean_temp_agent import OceanTempAgent
from app.agents.safety_boundary_agent import SafetyBoundaryAgent
from app.agents.weather_storm_agent import WeatherStormAgent
from app.core.logger import logger
from app.schemas.chat import AgentType, ChatRequest, ChatResponse, ReasoningStep


class MasterOrchestrator:
    """Central intelligent router and response synthesizer for ORCA."""

    def __init__(self):
        self.agents = {
            AgentType.WEATHER_STORM: WeatherStormAgent(),
            AgentType.FISHING_ZONE: FishingZoneAgent(),
            AgentType.OCEAN_TEMP: OceanTempAgent(),
            AgentType.SAFETY_BOUNDARY: SafetyBoundaryAgent(),
        }

    def route_query_intent(self, query: str) -> List[AgentType]:
        """Classify user intent to select relevant specialist agents."""
        q = query.lower()
        selected: List[AgentType] = []

        if any(w in q for w in ["weather", "storm", "cyclone", "wave", "wind", "rain", "safe"]):
            selected.append(AgentType.WEATHER_STORM)
        if any(w in q for w in ["fish", "pfz", "catch", "tuna", "zone"]):
            selected.append(AgentType.FISHING_ZONE)
        if any(w in q for w in ["temp", "temperature", "sst", "heatwave", "warm", "ocean"]):
            selected.append(AgentType.OCEAN_TEMP)
        if any(w in q for w in ["border", "boundary", "imbl", "sri lanka", "pakistan", "eez", "danger"]):
            selected.append(AgentType.SAFETY_BOUNDARY)

        # Default fallback: full safety & weather assessment
        if not selected:
            selected = [AgentType.WEATHER_STORM, AgentType.SAFETY_BOUNDARY]

        logger.info("orchestrator_routed_intent", query=query, agents=[a.value for a in selected])
        return selected

    async def process_query(self, request: ChatRequest) -> ChatResponse:
        """Coordinate multi-agent reasoning and synthesize unified response."""
        target_agents = self.route_query_intent(request.query)

        # Run selected specialist agents concurrently
        tasks = [self.agents[agent_type].analyze(request) for agent_type in target_agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_steps: List[ReasoningStep] = [
            ReasoningStep(
                agent=AgentType.ORCHESTRATOR,
                action="intent_classification_and_routing",
                rationale=f"Routed query '{request.query}' to {len(target_agents)} specialist domain agents.",
                data_sources=[],
            )
        ]
        summaries: List[str] = []
        structured_data: Dict = {}
        next_safe_window = None

        for agent_type, res in zip(target_agents, results):
            if isinstance(res, Exception):
                logger.error("agent_execution_failed", agent=agent_type.value, error=str(res))
                continue
            all_steps.extend(res.get("reasoning_steps", []))
            summaries.append(res.get("summary", ""))
            structured_data[agent_type.value] = res.get("structured_data", {})
            if res.get("next_safe_window"):
                next_safe_window = res["next_safe_window"]

        synthesized_answer = " ".join(summaries)
        suggested_actions = [
            "Check live radar overlay on map",
            "Monitor IMBL border distance",
            "View potential fishing zone coordinates",
        ]

        return ChatResponse(
            answer=synthesized_answer,
            reasoning_steps=all_steps,
            involved_agents=target_agents,
            suggested_actions=suggested_actions,
            next_safe_window=next_safe_window,
            structured_data=structured_data,
        )
