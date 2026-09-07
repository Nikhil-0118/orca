import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_trigger_sos(client: AsyncClient):
    response = await client.post(
        "/api/v1/sos/trigger",
        json={
            "vessel_id": "IND-TN-02-MM-4412",
            "vessel_name": "Matsya Sagar II",
            "crew_count": 5,
            "location": {"latitude": 12.9500, "longitude": 80.3500},
            "distress_nature": "ENGINE_FAILURE",
            "notes": "Drifting rapidly toward rocky shoals.",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["mrcc_acknowledged"] is True
    assert "incident_id" in data["data"]
