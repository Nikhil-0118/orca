import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_query_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat",
        json={
            "query": "Is it safe to fish near Chennai coast today?",
            "vessel_location": {"latitude": 13.0827, "longitude": 80.2707},
            "language_code": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "answer" in data["data"]
    assert len(data["data"]["reasoning_steps"]) > 0
