"""
Conversational Marine Intelligence Chat Endpoints.
Routes plain-language queries through the MasterOrchestrator multi-agent pipeline.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.agents.orchestrator import MasterOrchestrator
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import StandardApiResponse

router = APIRouter()


def get_orchestrator() -> MasterOrchestrator:
    return MasterOrchestrator()


@router.post("", response_model=StandardApiResponse[ChatResponse], status_code=status.HTTP_200_OK)
async def query_marine_intelligence(
    request: ChatRequest,
    orchestrator: MasterOrchestrator = Depends(get_orchestrator),
) -> StandardApiResponse[ChatResponse]:
    """
    Submits a plain-language marine intelligence query to ORCA's multi-agent system.
    Returns reasoned response with traceable steps from specialist agents.
    """
    try:
        response = await orchestrator.process_query(request)
        return StandardApiResponse(
            success=True,
            message="Reasoned marine intelligence generated",
            data=response,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent orchestration failed: {str(exc)}",
        ) from exc
