import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_active_alerts(client: AsyncClient):
    response = await client.get("/api/v1/alerts/active?lat=13.0827&lon=80.2707")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
