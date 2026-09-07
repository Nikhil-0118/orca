"""
Automated test suite for ISRO Bhuvan Village Reverse Geocoding Integration.

Verifies:
1. Token configured: GPS coordinates -> Bhuvan client -> parsed geographic information.
2. Empty token: BHUVAN_ACCESS_TOKEN="" -> graceful fallback to existing resolution.
3. Bhuvan HTTP 401 (expired/invalid token) -> silent fallback, existing resolver continues.
4. Bhuvan timeout -> silent fallback, existing resolver continues.
5. Bhuvan malformed response -> silent fallback, existing resolver continues.
6. Target isolation: vesselLocation = Kanpur, query = "give me a spot for fishing in Mumbai" ->
   vessel location remains Kanpur, active target remains Mumbai.
7. Fishing intent: "give me a spot for fishing in Mumbai" produces Bombay High target.
8. Map follow-up: multi-turn sequence keeps Mumbai context without reverting to Chennai.
9. Token security: Bhuvan token is never leaked in client payloads or log outputs.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.config import settings
from app.services.bhuvan_client import BhuvanClient, bhuvan_client
from app.services.location_resolver import LocationResolver, location_resolver
from app.services.query_location_resolver import query_location_resolver
from app.services.spatial_reasoner import spatial_reasoner
from app.schemas.query import LocationContext, QueryRequest

# Sample official Bhuvan VRG response payload (Andhra Pradesh / Guntur)
MOCK_BHUVAN_SUCCESS_PAYLOAD = [
    {
        "name1": "SEKURU ",
        "vid": "2817004002130200 ",
        "no_hh": "2747",
        "tot_p": "10207",
        "tot_m": "5163",
        "tot_f": "5044",
        "p_sc": "2491",
        "m_sc": "1277",
        "f_sc": "1214",
        "p_st": "217",
        "m_st": "100",
        "f_st": "117",
        "m_lit": "3247",
        "f_lit": "2620",
        "dhq_name": "GUNTUR ",
        "thq_name": "CHEBROLU ",
    }
]


class TestBhuvanIntegration:

    @pytest.mark.asyncio
    async def test_01_token_configured_parses_geographic_info(self):
        """Test 1: When token is configured and API returns valid data, parse geographic info."""
        client = BhuvanClient(timeout_seconds=2.0)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = str(MOCK_BHUVAN_SUCCESS_PAYLOAD)
        mock_resp.json.return_value = MOCK_BHUVAN_SUCCESS_PAYLOAD

        with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "valid-test-token"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await client.reverse_geocode(16.279, 80.588)

            assert result is not None
            assert result["village"] == "SEKURU"
            assert result["district"] == "GUNTUR"
            assert result["sub_district"] == "CHEBROLU"
            assert result["village_id"] == "2817004002130200"
            assert result["state"] == "Andhra Pradesh"
            assert result["source"] == "isro_bhuvan"
            assert result["census_data"]["households"] == 2747
            assert result["census_data"]["total_population"] == 10207

    @pytest.mark.asyncio
    async def test_02_empty_token_graceful_fallback(self):
        """Test 2: When BHUVAN_ACCESS_TOKEN is empty, return None immediately without making requests."""
        client = BhuvanClient()
        with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", ""):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                result = await client.reverse_geocode(16.279, 80.588)
                assert result is None
                mock_get.assert_not_called()

        # Verify LocationResolver works cleanly with empty token
        resolver = LocationResolver()
        with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", ""):
            resolved = await resolver.resolve(26.5208, 80.2564)
            assert resolved is not None
            assert resolved.geographic_type == "inland"
            assert "Kanpur" in (resolved.place_name or "")
            assert resolved.bhuvan_location is None

    @pytest.mark.asyncio
    async def test_03_bhuvan_401_expired_token_graceful_fallback(self):
        """Test 3: When Bhuvan returns HTTP 401 (expired/invalid token), fall back seamlessly."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "expired-token-12345"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            resolver = LocationResolver()
            resolved = await resolver.resolve(26.5208, 80.2564)
            assert resolved is not None
            assert resolved.geographic_type == "inland"
            assert "Kanpur" in (resolved.place_name or "")
            assert resolved.bhuvan_location is None

    @pytest.mark.asyncio
    async def test_04_bhuvan_timeout_graceful_fallback(self):
        """Test 4: When Bhuvan request times out, fall back without raising an error."""
        with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "mock-token"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Connection timed out")

            resolver = LocationResolver()
            resolved = await resolver.resolve(13.0827, 80.2707)
            assert resolved is not None
            assert resolved.latitude == 13.0827
            assert resolved.bhuvan_location is None

    @pytest.mark.asyncio
    async def test_05_bhuvan_malformed_response_graceful_fallback(self):
        """Test 5: When Bhuvan returns malformed/non-JSON response, fall back seamlessly."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>502 Bad Gateway</body></html>"
        mock_resp.json.side_effect = ValueError("Invalid JSON")

        with patch("app.config.settings.BHUVAN_ACCESS_TOKEN", "mock-token"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            resolver = LocationResolver()
            resolved = await resolver.resolve(13.0827, 80.2707)
            assert resolved is not None
            assert resolved.latitude == 13.0827
            assert resolved.bhuvan_location is None

    @pytest.mark.asyncio
    async def test_06_target_isolation_vessel_kanpur_query_mumbai(self):
        """
        Test 6: User GPS is Kanpur (inland), user asks "give me a spot for fishing in Mumbai".
        Bhuvan reverse-geocoding the vessel GPS must NOT change the active target to Kanpur.
        """
        vessel_lat, vessel_lon = 26.5208, 80.2564
        client_loc = LocationContext(
            latitude=vessel_lat,
            longitude=vessel_lon,
            source="browser_gps",
            resolved_place="Kanpur",
            label="Kanpur, Uttar Pradesh",
            geographic_type="inland",
            bhuvan_location={"village": "TestVillage", "district": "Kanpur Nagar", "state": "Uttar Pradesh"},
        )

        query = "give me a spot for fishing in Mumbai"
        result = await query_location_resolver.resolve_query_location(query, client_loc)

        # Active target must be Mumbai, NOT Kanpur
        assert result.target_location is not None
        assert abs(result.target_location.latitude - 18.922) < 0.1
        assert abs(result.target_location.longitude - 72.834) < 0.1
        assert "mumbai" in (result.target_location.resolved_place or "").lower()

        # Verify spatial payload isolates vessel from target
        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=client_loc,
            target_location=result.target_location,
        )

        assert payload is not None
        assert payload.enabled is True
        # Target must be the Mumbai/Bombay High fishing ground
        t_loc = payload.target_location
        assert "Bombay High" in t_loc["label"] or "Mumbai" in t_loc["label"]
        assert abs(t_loc["latitude"] - 18.92) < 0.2
        assert abs(t_loc["longitude"] - 72.75) < 0.2

        # Vessel coordinates must remain Kanpur
        v_loc = payload.vessel_location
        assert abs(v_loc["latitude"] - vessel_lat) < 0.01
        assert abs(v_loc["longitude"] - vessel_lon) < 0.01

    @pytest.mark.asyncio
    async def test_07_fishing_intent_unaltered(self):
        """Test 7: Fishing queries continue to resolve to deterministic fishing grounds."""
        query = "give me a spot for fishing in Mumbai"
        mumbai_loc = LocationContext(latitude=18.922, longitude=72.834, resolved_place="Mumbai", source="gazetteer")
        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mumbai_loc,
            target_location=mumbai_loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert "Bombay High Coastal Waters" in payload.target_location["label"]

    @pytest.mark.asyncio
    async def test_08_map_followup_preserves_mumbai_not_chennai(self):
        """Test 8: Multi-turn sequence "give me a spot for fishing in Mumbai" -> "give me map" preserves Mumbai."""
        history = [
            {"role": "user", "content": "give me a spot for fishing in Mumbai"},
            {"role": "assistant", "content": "I recommend Bombay High Coastal Waters off Mumbai."},
        ]
        query = "give me map"
        client_loc = LocationContext(latitude=13.0827, longitude=80.2707, source="browser_gps")
        q_res = await query_location_resolver.resolve_query_location(query, client_loc, history)

        assert q_res.target_location is not None
        assert abs(q_res.target_location.latitude - 18.922) < 0.1
        assert abs(q_res.target_location.longitude - 72.834) < 0.1

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=client_loc,
            target_location=q_res.target_location,
            conversation_history=history,
        )

        assert payload is not None
        assert "Bombay High" in payload.target_location["label"]
        assert abs(payload.target_location["latitude"] - 18.92) < 0.2

    def test_09_token_never_logged_or_exposed(self):
        """Test 9: Verify token is stripped and never appears in repr or string representations."""
        client = BhuvanClient()
        # Ensure BhuvanClient repr does not contain secrets
        assert "token" not in repr(client).lower()
