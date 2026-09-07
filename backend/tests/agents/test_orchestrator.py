import pytest
from app.agents.orchestrator import MasterOrchestrator
from app.schemas.chat import AgentType, ChatRequest
from app.schemas.common import Coordinates


@pytest.mark.asyncio
async def test_orchestrator_routing():
    orchestrator = MasterOrchestrator()
    agents = orchestrator.route_query_intent("Where can I find high fish catch and what is the sea surface temp?")
    assert AgentType.FISHING_ZONE in agents
    assert AgentType.OCEAN_TEMP in agents


@pytest.mark.asyncio
async def test_orchestrator_process_query():
    orchestrator = MasterOrchestrator()
    req = ChatRequest(
        query="Is there any cyclone warning near Kanyakumari?",
        vessel_location=Coordinates(latitude=8.0883, longitude=77.5385),
    )
    res = await orchestrator.process_query(req)
    assert res.answer is not None
    assert len(res.reasoning_steps) > 0
