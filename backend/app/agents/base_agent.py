"""
Base abstract class for all ORCA specialist agents.
Standardizes prompt framing, reasoning traces, and input/output contracts.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.core.logger import logger
from app.schemas.chat import AgentType, ChatRequest, ReasoningStep


class BaseAgent(ABC):
    """Abstract base class defining interface and lifecycle for specialist agents."""

    def __init__(self, agent_type: AgentType, description: str):
        self.agent_type = agent_type
        self.description = description

    @abstractmethod
    async def analyze(
        self,
        request: ChatRequest,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute domain-specific reasoning on the user request.
        Must return a dict containing:
        - "reasoning_steps": List[ReasoningStep]
        - "summary": str
        - "structured_data": Dict[str, Any]
        - "confidence": float
        """
        pass

    def create_reasoning_step(
        self,
        action: str,
        rationale: str,
        data_sources: Optional[List[str]] = None,
    ) -> ReasoningStep:
        """Helper to create standardized traceable reasoning steps."""
        return ReasoningStep(
            agent=self.agent_type,
            action=action,
            rationale=rationale,
            data_sources_queried=data_sources or [],
        )
