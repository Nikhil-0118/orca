import pytest
from app.connectors.mosdac_client import MosdacClient
from app.schemas.common import Coordinates


@pytest.mark.asyncio
async def test_mosdac_client_data_fetch():
    client = MosdacClient()
    loc = Coordinates(latitude=13.0827, longitude=80.2707)
    sst = await client.get_sea_surface_temperature(loc)
    assert sst.sea_surface_temperature_celsius > 0.0
    assert sst.source == "ISRO-MOSDAC"

    chl = await client.get_chlorophyll_density(loc)
    assert chl.concentration_mg_m3 >= 0.0
