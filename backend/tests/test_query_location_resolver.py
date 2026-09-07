import pytest
from app.services.query_location_resolver import (
    resolve_query_location_sync,
    resolve_query_location,
    INDIAN_SPATIAL_GAZETTEER,
    INDIA_GAZETTEER,
)
from app.services.location_resolver import find_nearest_ocean, classify_location_type
from app.schemas.query import LocationContext, QueryRequest
from app.services.planner import orca_planner
from app.api.endpoints import query


class TestQueryLocationResolver:
    """Test resolution of geographic entities vs deictic GPS references across India."""

    @pytest.mark.parametrize("query_text", [
        "where is my location?",
        "what is my location",
        "nearest ocean near me",
        "where is the nearest ocean nearby me",
        "temperature here",
        "weather here",
        "current weather in my location",
    ])
    def test_deictic_queries_route_to_gps(self, query_text):
        res = resolve_query_location_sync(query_text, user_lat=26.52, user_lon=80.26)
        assert res.is_explicit is False, f"Expected non-explicit GPS target for: {query_text}"
        assert res.location_source in ("browser_gps", "gps_current")
        assert abs(res.target_location.latitude - 26.52) < 0.01
        assert abs(res.target_location.longitude - 80.26) < 0.01

    @pytest.mark.parametrize("query_text,expected_name,expected_type", [
        ("the nearest ocean to Gujarat", "Gujarat", "coastal_state"),
        ("nearest ocean to Mumbai", "Mumbai", "coastal_city"),
        ("nearest ocean to Chennai", "Chennai", "coastal_city"),
        ("ocean near Dwarka", "Dwarka", "coastal_city"),
        ("nearest ocean to Ahmedabad", "Ahmedabad", "inland_city"),
        ("nearest ocean to Surat", "Surat", "coastal_city"),
        ("weather in Gujarat", "Gujarat", "coastal_state"),
        ("temperature in Mumbai", "Mumbai", "coastal_city"),
        ("weather in Delhi", "Delhi", "inland_city"),
        ("ocean near Goa", "Goa", "coastal_state"),
        ("nearest ocean to Kolkata", "Kolkata", "coastal_city"),
        ("nearest ocean to Odisha", "Odisha", "coastal_state"),
        ("ocean near Visakhapatnam", "Visakhapatnam", "coastal_city"),
        ("nearest ocean to Kochi", "Kochi", "coastal_city"),
        ("nearest ocean to Kerala", "Kerala", "coastal_state"),
        ("nearest ocean to Andaman and Nicobar", "Andaman & Nicobar Islands", "island_territory"),
        ("ocean near Lakshadweep", "Lakshadweep", "island_territory"),
        ("water conditions in Bay of Bengal", "Bay of Bengal", "marine_basin"),
        ("waves in Arabian Sea", "Arabian Sea", "marine_basin"),
    ])
    def test_explicit_locations_across_india(self, query_text, expected_name, expected_type):
        res = resolve_query_location_sync(query_text, user_lat=26.52, user_lon=80.26)
        assert res.is_explicit is True, f"Expected explicit target for: {query_text}"
        assert res.location_source == "explicit_query"
        assert res.query_entity_name.lower() == expected_name.lower()
        assert res.entity_type == expected_type

    def test_mixed_query_kanpur_and_mumbai(self):
        """Test 'I am in Kanpur, what is the weather in Mumbai?' separates user vs query location."""
        query_text = "I am in Kanpur, what is the weather in Mumbai?"
        client_loc = LocationContext(
            latitude=26.52,
            longitude=80.26,
            source="browser_gps",
            label="Kanpur, Uttar Pradesh",
            geographic_type="inland",
            resolved_place="Kanpur"
        )
        res = resolve_query_location_sync(query_text, client_location=client_loc)
        assert res.is_explicit is True
        assert res.query_entity_name.lower() == "mumbai"
        assert res.target_location.resolved_place == "Mumbai"
        assert abs(client_loc.latitude - 26.52) < 0.01
        assert abs(client_loc.longitude - 80.26) < 0.01


class TestNearestOceanProximity:
    """Test geodesic calculation, coastal vs inland, and regional approximation."""

    def test_gujarat_state_nearest_ocean(self):
        """Gujarat is an extensive maritime state (~1,600 km coastline).

        It must return 0 km distance along coastline to Arabian Sea, with state context.
        """
        loc_res = INDIA_GAZETTEER["gujarat"]
        result = find_nearest_ocean(
            lat=loc_res["latitude"],
            lon=loc_res["longitude"],
            user_place="Gujarat",
            is_explicit_location=True,
            entity_type="coastal_state",
            coastline_km=loc_res.get("coastline_km"),
            bordering_oceans=loc_res.get("bordering_oceans")
        )
        assert result.distance_km == 0.0
        assert "Arabian Sea" in result.ocean
        assert result.is_state is True
        assert result.coastline_km == 1600.0
        assert result.is_user_inland is False

    def test_dwarka_coastal_city_nearest_ocean(self):
        """Dwarka is a coastal town in Gujarat. It must return ~0 km to Arabian Sea."""
        loc_res = INDIA_GAZETTEER["dwarka"]
        result = find_nearest_ocean(
            lat=loc_res["latitude"],
            lon=loc_res["longitude"],
            user_place="Dwarka",
            is_explicit_location=True,
            entity_type="coastal_city"
        )
        assert result.distance_km < 15.0  # Situated directly on the coast
        assert "Arabian Sea" in result.ocean
        assert result.is_user_inland is False

    def test_ahmedabad_inland_nearest_ocean(self):
        """Ahmedabad is inland, ~80-165 km from Gulf of Khambhat / Arabian Sea."""
        loc_res = INDIA_GAZETTEER["ahmedabad"]
        result = find_nearest_ocean(
            lat=loc_res["latitude"],
            lon=loc_res["longitude"],
            user_place="Ahmedabad",
            is_explicit_location=True,
            entity_type="inland_city"
        )
        assert 50.0 < result.distance_km < 180.0
        assert "Arabian Sea" in result.ocean

    def test_mumbai_and_chennai_coastal_nearest_ocean(self):
        """Mumbai (Arabian Sea) and Chennai (Bay of Bengal) are coastal."""
        res_mum = find_nearest_ocean(lat=19.0760, lon=72.8777, user_place="Mumbai", is_explicit_location=True, entity_type="coastal_city")
        assert res_mum.distance_km < 25.0
        assert "Arabian Sea" in res_mum.ocean

        res_che = find_nearest_ocean(lat=13.0827, lon=80.2707, user_place="Chennai", is_explicit_location=True, entity_type="coastal_city")
        assert res_che.distance_km < 25.0
        assert "Bay of Bengal" in res_che.ocean

    def test_negative_regression_kanpur_vs_gujarat(self):
        """CRITICAL: User GPS in Kanpur (26.52, 80.26) asking for Gujarat.

        Must NEVER return Kanpur coordinates or 883 km.
        """
        user_lat, user_lon = 26.52, 80.26  # Kanpur
        # Resolve target
        res = resolve_query_location_sync("nearest ocean to Gujarat", user_lat=user_lat, user_lon=user_lon)
        assert res.is_explicit is True
        assert res.query_entity_name.lower() == "gujarat"

        # Compute nearest ocean on resolved target
        guj_data = INDIA_GAZETTEER["gujarat"]
        ocean_res = find_nearest_ocean(
            lat=res.target_location.latitude,
            lon=res.target_location.longitude,
            user_place=res.query_entity_name,
            is_explicit_location=True,
            entity_type=res.entity_type,
            coastline_km=guj_data.get("coastline_km"),
            bordering_oceans=guj_data.get("bordering_oceans")
        )
        assert ocean_res.distance_km != 883.0
        assert ocean_res.distance_km < 10.0
        assert "Arabian Sea" in ocean_res.ocean
        assert "Kanpur" not in ocean_res.ocean


class TestIntentRoutingAndTemperatureSeparation:
    """Test intent classification and strict temperature routing."""

    @pytest.mark.asyncio
    async def test_air_temperature_goes_to_weather_agent(self):
        plan1 = await orca_planner.plan("what is the temperature in my location", location={"lat": 26.52, "lon": 80.26})
        assert "weather" in plan1.agents
        assert "ocean" not in plan1.agents
        assert plan1.intent.upper() in ("AIR_TEMPERATURE", "TEMPERATURE")

        plan2 = await orca_planner.plan("temperature in Gujarat", location={"lat": 26.52, "lon": 80.26})
        assert "weather" in plan2.agents
        assert "ocean" not in plan2.agents

        plan3 = await orca_planner.plan("temperature here", location={"lat": 26.52, "lon": 80.26})
        assert "weather" in plan3.agents
        assert "ocean" not in plan3.agents

    @pytest.mark.asyncio
    async def test_sea_surface_temperature_goes_to_ocean_agent(self):
        plan1 = await orca_planner.plan("sea surface temperature", location={"lat": 14.0, "lon": 84.0})
        assert "ocean" in plan1.agents

        plan2 = await orca_planner.plan("sea temperature near Gujarat", location={"lat": 22.5, "lon": 71.0})
        assert "ocean" in plan2.agents

        plan3 = await orca_planner.plan("SST near Mumbai", location={"lat": 19.0, "lon": 72.8})
        assert "ocean" in plan3.agents

    @pytest.mark.asyncio
    async def test_nearest_ocean_routes_to_utility_and_location(self):
        plan = await orca_planner.plan("the nearest ocean to Gujarat", location={"lat": 26.52, "lon": 80.26})
        assert plan.response_mode == "utility"
        assert "location" in plan.tools
        assert "ocean" not in plan.agents  # Do NOT invoke ocean agent wave analysis for ocean lookup


class TestEndToEndSeparationInApiEndpoint:
    """Test the /api/query endpoint preserves both user_location and query_location."""

    @pytest.mark.asyncio
    async def test_api_query_preserves_both_locations(self):
        req = QueryRequest(
            session_id="test_geo_routing",
            query="the nearest ocean to Gujarat",
            location=LocationContext(
                latitude=26.52,
                longitude=80.26,
                source="browser_gps"
            )
        )
        resp = await query(req)
        # Verify user_location is preserved as Kanpur
        assert resp.user_location is not None
        assert abs(resp.user_location.latitude - 26.52) < 0.01
        assert abs(resp.user_location.longitude - 80.26) < 0.01

        # Verify query_location is Gujarat
        assert resp.query_location is not None
        assert resp.query_location["name"].lower() == "gujarat"
        assert resp.query_location["source"] == "explicit_query"

        # Verify response text does NOT say Kanpur or 883 km
        ans = resp.answer.lower()
        assert "883" not in ans
        assert "arabian sea" in ans or "coastline" in ans
        assert "kanpur" not in ans or "user location" in ans or "reference" in ans
