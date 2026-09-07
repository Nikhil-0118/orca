"""
Chat request, response, and agent reasoning step schemas.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import Coordinates


class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    WEATHER_STORM = "weather_storm_agent"
    FISHING_ZONE = "fishing_zone_agent"
    OCEAN_TEMP = "ocean_temp_agent"
    SAFETY_BOUNDARY = "safety_boundary_agent"


class ReasoningStep(BaseModel):
    agent: AgentType
    action: str
    rationale: str
    data_sources_queried: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Plain-language marine query")
    vessel_location: Optional[Coordinates] = None
    language_code: str = Field(default="en", description="Target response language (e.g. en, hi, ta, te, ml)")
    conversation_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    reasoning_steps: List[ReasoningStep] = []
    involved_agents: List[AgentType] = []
    suggested_actions: List[str] = []
    next_safe_window: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
