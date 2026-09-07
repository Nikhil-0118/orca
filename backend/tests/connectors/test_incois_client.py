import pytest
from app.connectors.incois_client import IncoisClient
from app.schemas.common import Coordinates


@pytest.mark.asyncio
async def test_incois_client_data_fetch():
    client = IncoisClient()
    loc = Coordinates(latitude=13.0827, longitude=80.2707)
    weather = await client.get_weather_and_ocean_state(loc)
    assert weather.significant_wave_height_meters >= 0.0
    assert weather.source == "INCOIS-ERDDAP"

    pfz_list = await client.get_potential_fishing_zones(loc)
    assert isinstance(pfz_list, list)
    assert len(pfz_list) > 0
