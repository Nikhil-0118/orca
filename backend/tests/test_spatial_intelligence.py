"""
Unit & Integration Tests for Phase 18: Marine Map & Spatial Intelligence.

Tests:
1. Spatial Intent Detection:
   - Must trigger for spatial requests:
     * "Show my current location"
     * "Show route from Chennai to Pondicherry"
     * "Show dangerous areas"
     * "How far am I from the boundary?"
   - Must NOT trigger for non-spatial queries:
     * "What is the chlorophyll concentration near Chennai?"
     * "What is the weather near Chennai?"
     * "What is the SST near Chennai?"
     * "Can I go fishing near Chennai?"
     * "Will I get more fish near Chennai?"
2. Spatial Payload Validity:
   - Valid coordinates, markers, zones, route, distance, bearing, safety state
3. Marine Route Calculation:
   - Great-circle distance, nautical miles, bearing, waypoints, no road routing
4. Safety Consistency:
   - Verifies safety_state matches geofence_service output
"""
import pytest
from app.schemas.query import LocationContext, QueryRequest
from app.services.spatial_reasoner import (
    detect_spatial_intent,
    spatial_reasoner,
)
from app.services.geofence_service import geofence_service, haversine_distance_km, calculate_bearing


class TestSpatialIntentDetection:
    """Test suite for deterministic spatial intent classification."""

    @pytest.mark.parametrize(
        "query, expected_type",
        [
            ("Show my current location", "user_location"),
            ("Where am I?", "user_location"),
            ("Show my position", "user_location"),
            ("Where is my boat", "user_location"),
            ("Show a route from Chennai to Pondicherry", "marine_route"),
            ("Show me a route from Chennai to Pondicherry", "marine_route"),
            ("Show the route from my current location to Chennai", "marine_route"),
            ("route to Pondicherry", "marine_route"),
            ("How far am I from the boundary?", "boundary_safety"),
            ("Distance to boundary", "boundary_safety"),
            ("Show the safe zone", "boundary_safety"),
            ("Show safe zone near Chennai", "boundary_safety"),
            ("Show dangerous areas around my boat", "danger_areas"),
            ("Show danger areas", "danger_areas"),
            ("Show Chennai on the map", "target_location"),
            ("Display Pondicherry on map", "target_location"),
        ],
    )
    def test_spatial_queries_trigger(self, query: str, expected_type: str):
        is_spatial, detected_type = detect_spatial_intent(query)
        assert is_spatial is True, f"Query '{query}' was expected to trigger spatial intent"
        assert detected_type == expected_type, f"Expected {expected_type}, got {detected_type} for query '{query}'"

    @pytest.mark.parametrize(
        "query",
        [
            "What is the chlorophyll concentration near Chennai?",
            "What is the weather near Chennai?",
            "What is the SST near Chennai?",
            "Will I get more fish near Chennai?",
            "How is the sea near Chennai?",
            "What is the wave height near Chennai?",
            "Tell me about Kasimedu harbor",
            "What is the water temperature?",
            "Is it safe to go out to sea?",
        ],
    )
    def test_non_spatial_queries_never_trigger(self, query: str):
        is_spatial, detected_type = detect_spatial_intent(query)
        assert is_spatial is False, f"Non-spatial query '{query}' incorrectly triggered spatial intent: {detected_type}"
        assert detected_type is None


class TestSpatialPayloadBuilder:
    """Test suite for spatial payload construction."""

    def test_user_location_payload(self):
        user_loc = LocationContext(
            latitude=13.0827,
            longitude=80.2707,
            source="browser_gps",
            is_demo=False,
            label="Chennai, Tamil Nadu",
            accuracy_m=12.0,
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="Show my current location",
            user_location=user_loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "user_location"
        assert len(payload.markers) >= 1
        vessel_marker = payload.markers[0]
        assert vessel_marker.marker_type == "vessel"
        assert vessel_marker.latitude == 13.0827
        assert vessel_marker.longitude == 80.2707

    def test_boundary_safety_payload_and_consistency(self):
        loc = LocationContext(
            latitude=13.0827,
            longitude=80.2707,
            source="browser_gps",
            is_demo=False,
            label="Chennai Coast",
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="How far am I from the boundary?",
            user_location=loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "boundary_safety"
        assert payload.boundary_distance_km is not None
        assert payload.boundary_bearing_deg is not None
        assert payload.safety_state in ["NORMAL", "APPROACHING", "WARNING", "BREACH"]

        # Consistency check against geofence_service
        expected_eval = geofence_service.evaluate_position(13.0827, 80.2707)
        assert abs(payload.boundary_distance_km - expected_eval.distance_to_boundary_km) < 0.2
        assert payload.safety_state == expected_eval.state.value

        # Verify boundary zones are populated from GeoJSON
        assert payload.zones is not None
        assert len(payload.zones) >= 1
        assert payload.zones[0].geometry_type == "LineString"

    def test_danger_areas_payload(self):
        loc = LocationContext(latitude=9.45, longitude=79.20, source="demo", is_demo=True)
        payload = spatial_reasoner.build_spatial_payload(
            query="Show dangerous areas around my boat",
            user_location=loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "danger_areas"
        assert len(payload.markers) >= 1
        assert len(payload.zones) >= 1
        assert payload.zones[0].zone_type == "restricted"

    def test_marine_route_calculation(self):
        user_loc = LocationContext(
            latitude=13.0827,
            longitude=80.2707,
            source="demo",
            is_demo=True,
            label="Chennai Coast",
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="Show a route from Chennai to Pondicherry",
            user_location=user_loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "marine_route"
        assert payload.routes is not None
        assert len(payload.routes) == 1

        route = payload.routes[0]
        # Great-circle distance between Chennai (13.0827, 80.2707) and Pondicherry (11.9416, 79.8083) is ~136 km
        assert 120.0 < route.distance_km < 155.0
        assert route.distance_nm == round(route.distance_km * 0.539957, 1)
        # Bearing from Chennai south-southwest to Pondicherry should be around 195°-215°
        assert 190.0 <= route.bearing_degrees <= 220.0
        assert len(route.waypoints) >= 2
        # Verify safety note contains disclaimer and does not claim guaranteed safe navigation
        assert "Marine Route" in route.safety_note or "Recommended Marine Route" in route.safety_note
        assert "guaranteed safe" not in route.safety_note.lower()

    def test_marine_route_no_fabricated_speed(self):
        user_loc = LocationContext(
            latitude=13.0827,
            longitude=80.2707,
            source="browser_gps",
            is_demo=False,
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="Show route from Chennai to Pondicherry",
            user_location=user_loc,
        )
        assert payload is not None
        route = payload.routes[0]
        # Speed was not provided; estimated_time_minutes must be None (never fabricated!)
        assert route.estimated_time_minutes is None

    def test_non_spatial_queries_return_none(self):
        user_loc = LocationContext(latitude=13.0827, longitude=80.2707, source="browser_gps")
        assert (
            spatial_reasoner.build_spatial_payload(
                query="What is the chlorophyll concentration near Chennai?",
                user_location=user_loc,
            )
            is None
        )
        assert (
            spatial_reasoner.build_spatial_payload(
                query="What is the weather near Chennai?",
                user_location=user_loc,
            )
            is None
        )
        assert (
            spatial_reasoner.build_spatial_payload(
                query="What is the SST near Chennai?",
                user_location=user_loc,
            )
            is None
        )

    # ─────────────────────────────────────────────────────────────
    # Phase: Fishing Destination Routing & Inland Safety (Tests A–E)
    # ─────────────────────────────────────────────────────────────

    def test_test_a_current_location_no_fishing_no_route(self):
        """Test A: 'What is my current location?' shows vessel location ONLY, no fishing destination, no route."""
        user_loc = LocationContext(
            latitude=26.5207,
            longitude=80.2564,
            source="browser_gps",
            label="Kanpur, Uttar Pradesh",
            geographic_type="inland",
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="What is my current location?",
            user_location=user_loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "user_location"
        # Only vessel marker, no fishing marker, no routes
        assert len(payload.markers) == 1
        assert payload.markers[0].marker_type == "vessel"
        assert payload.markers[0].latitude == 26.5207
        assert payload.markers[0].longitude == 80.2564
        assert payload.routes is None or len(payload.routes) == 0

    def test_test_b_chennai_safe_zone_no_fishing_route(self):
        """Test B: 'Show the safe zone near Chennai.' shows Chennai safe zone, vessel GPS unchanged, no fishing route."""
        user_loc = LocationContext(
            latitude=26.5207,
            longitude=80.2564,
            source="browser_gps",
            label="Kanpur, Uttar Pradesh",
            geographic_type="inland",
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="Show the safe zone near Chennai.",
            user_location=user_loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "boundary_safety"
        # Query location is Chennai (~13.08), not Kanpur
        assert abs(payload.center["latitude"] - 13.08) < 0.2
        # Safety zones present, but NO fishing route
        assert payload.zones is not None and len(payload.zones) > 0
        assert payload.routes is None or len(payload.routes) == 0

    def test_test_c_fishing_destination_chennai(self):
        """Test C: 'What is the best fishing spot near Chennai?' detects Chennai, generates fishing destination,
        creates distinct vessel and fishing markers, fits both points, and separates vessel from target."""
        # Vessel is at coastal location (e.g. Ennore Port: 13.25, 80.33)
        user_loc = LocationContext(
            latitude=13.25,
            longitude=80.33,
            source="browser_gps",
            label="Ennore, Tamil Nadu",
            geographic_type="coastal",
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="What is the best fishing spot near Chennai?",
            user_location=user_loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "fishing_destination"
        assert payload.target_location is not None
        # Target coordinate is Chennai offshore fishing ground (12.85, 80.35)
        assert payload.target_location["latitude"] == 12.85
        assert payload.target_location["longitude"] == 80.35
        # Vessel location is preserved and separate
        assert payload.vessel_location["latitude"] == 13.25
        assert payload.vessel_location["longitude"] == 80.33

        # Distinct markers: vessel AND fishing
        marker_types = [m.marker_type for m in payload.markers]
        assert "vessel" in marker_types
        assert "fishing" in marker_types

        # Pure recommendation query creates markers but NO automatic route
        assert payload.routes is None or len(payload.routes) == 0

        # Follow-up query asking for the route generates the route to active target
        target_loc_ctx = LocationContext(
            latitude=payload.target_location["latitude"],
            longitude=payload.target_location["longitude"],
            label=payload.target_location.get("label", "Chennai Fishing Ground"),
            source="conversation_context",
            geographic_type="marine",
        )
        history = [
            {"role": "user", "content": "What is the best fishing spot near Chennai?"},
            {"role": "assistant", "content": "Recommended area: Chennai Offshore Pelagic Ground"},
        ]
        route_payload = spatial_reasoner.build_spatial_payload(
            query="can you give me the route?",
            user_location=user_loc,
            target_location=target_loc_ctx,
            conversation_history=history,
        )
        assert route_payload is not None
        assert route_payload.routes is not None and len(route_payload.routes) == 1
        route = route_payload.routes[0]
        assert route.distance_km > 0
        assert route.bearing_degrees >= 0
        assert route.destination["latitude"] == 12.85
        assert route.destination["longitude"] == 80.35

    def test_test_d_explicit_coordinates_navigation(self):
        """Test D: 'Navigate to 12.85, 80.35' extracts coordinates as destination, creates destination marker and route."""
        user_loc = LocationContext(
            latitude=13.0827,
            longitude=80.2707,
            source="browser_gps",
            label="Chennai Coast",
            geographic_type="coastal",
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="Navigate to 12.85, 80.35",
            user_location=user_loc,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.target_location is not None
        assert abs(payload.target_location["latitude"] - 12.85) < 0.001
        assert abs(payload.target_location["longitude"] - 80.35) < 0.001
        assert payload.routes is not None and len(payload.routes) == 1
        assert abs(payload.routes[0].destination["latitude"] - 12.85) < 0.001

    def test_test_e_inland_vessel_kanpur_guardrail(self):
        """Test E: Inland vessel in Kanpur (~500+ km from coast) must NEVER claim a valid marine navigation route
        exists across land to Chennai. Must generate authoritative warning message."""
        kanpur_loc = LocationContext(
            latitude=26.5207,
            longitude=80.2564,
            source="browser_gps",
            label="Kanpur, Uttar Pradesh",
            geographic_type="inland",
        )
        payload = spatial_reasoner.build_spatial_payload(
            query="Take me to the recommended fishing spot near Chennai",
            user_location=kanpur_loc,
        )
        assert payload is not None
        assert payload.enabled is True
        # Must be flagged as not marine navigable
        assert payload.is_marine_navigable is False
        assert payload.navigation_warning is not None
        assert "⚠️ Marine navigation unavailable" in payload.navigation_warning
        assert "inland" in payload.navigation_warning.lower()
        assert "coastal/marine position" in payload.navigation_warning.lower()

        # Route is labeled approximate / inland warning
        assert payload.routes is not None and len(payload.routes) == 1
        assert payload.routes[0].is_approximate is True
        assert payload.routes[0].is_inland_warning is True

        # Target coordinate is still Chennai (12.85, 80.35), NOT Kanpur
        assert payload.target_location["latitude"] == 12.85
        assert payload.target_location["longitude"] == 80.35

    def test_test_f_eta_speed_provided_vs_unprovided(self):
        """Test F: ETA calculation policy:
        - If speed_knots is None: ETA is None (never fabricated).
        - If speed_knots is provided: ETA is calculated accurately."""
        # Unprovided speed
        loc_no_speed = LocationContext(
            latitude=13.0827,
            longitude=80.2707,
            speed_knots=None,
            geographic_type="coastal",
        )
        payload_no_speed = spatial_reasoner.build_spatial_payload(
            query="Navigate to 12.85, 80.35",
            user_location=loc_no_speed,
        )
        assert payload_no_speed.routes[0].estimated_time_minutes is None

        # Provided speed (15 knots)
        loc_with_speed = LocationContext(
            latitude=13.0827,
            longitude=80.2707,
            speed_knots=15.0,
            geographic_type="coastal",
        )
        payload_with_speed = spatial_reasoner.build_spatial_payload(
            query="Navigate to 12.85, 80.35",
            user_location=loc_with_speed,
        )
        assert payload_with_speed.routes[0].estimated_time_minutes is not None
        # Distance ~27 km (~14.7 NM) at 15 knots is ~59 minutes
        assert 30 <= payload_with_speed.routes[0].estimated_time_minutes <= 90


class TestGenericLocationIntelligence:
    """
    Test suite for dynamic, location-agnostic fishing destination and map context intelligence.
    Covers all 11 requirements from Section 11 of the specification:
    - Dynamic fishing intent detection for any location (Chennai, Mumbai, Kochi, Goa, Vizag, etc.)
    - Context follow-up ('Give me the map') reusing active target
    - Context updating ('What about Chennai?' -> 'Give me the map')
    - Combined safety + fishing queries producing both decisions and map payloads
    - Existing location and safe-zone queries without regression
    """

    @pytest.fixture
    def mock_gps_vessel(self):
        """Simulate vessel with live GPS in Kanpur (inland)."""
        return LocationContext(
            latitude=26.5207,
            longitude=80.2564,
            source="browser_gps",
            label="Kanpur, Uttar Pradesh",
            geographic_type="inland",
        )

    @pytest.fixture
    def mock_coastal_vessel(self):
        """Simulate vessel at a coastal harbor (e.g. Kasimedu / Chennai)."""
        return LocationContext(
            latitude=13.1189,
            longitude=80.2978,
            source="browser_gps",
            label="Kasimedu Harbor, Tamil Nadu",
            geographic_type="coastal",
        )

    def test_1_best_fishing_spot_near_chennai(self, mock_coastal_vessel):
        """Test 1: 'Best fishing spot near Chennai' -> fishing intent, Chennai target, fishing destination, map payload."""
        from app.services.query_location_resolver import query_location_resolver
        query = "Best fishing spot near Chennai"
        is_spatial, s_type = detect_spatial_intent(query)
        assert is_spatial is True
        assert s_type == "fishing_destination"

        loc_res = query_location_resolver.resolve_query_location_sync(query, mock_coastal_vessel)
        assert loc_res.is_explicit is True
        assert "Chennai" in (loc_res.query_entity_name or "")
        assert abs(loc_res.target_location.latitude - 13.0827) < 0.1

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "fishing_destination"
        assert payload.target_location is not None
        assert payload.target_location["latitude"] == 12.85
        assert payload.target_location["longitude"] == 80.35
        # Fishing recommendation query must NOT generate automatic route
        assert len(payload.routes) == 0

    def test_2_best_fishing_spot_near_mumbai(self, mock_coastal_vessel):
        """Test 2: 'Best fishing spot near Mumbai' -> fishing intent, Mumbai target, fishing destination, map payload."""
        from app.services.query_location_resolver import query_location_resolver
        query = "Best fishing spot near Mumbai"
        is_spatial, s_type = detect_spatial_intent(query)
        assert is_spatial is True
        assert s_type == "fishing_destination"

        loc_res = query_location_resolver.resolve_query_location_sync(query, mock_coastal_vessel)
        assert loc_res.is_explicit is True
        assert "Mumbai" in (loc_res.query_entity_name or "")
        assert abs(loc_res.target_location.latitude - 18.9220) < 0.1

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "fishing_destination"
        assert payload.target_location is not None
        assert payload.target_location["latitude"] == 18.92
        assert payload.target_location["longitude"] == 72.75
        # Fishing recommendation query must NOT generate automatic route
        assert len(payload.routes) == 0

    def test_3_best_fishing_spot_near_kochi(self, mock_coastal_vessel):
        """Test 3: 'Best fishing spot near Kochi' -> fishing intent, Kochi target, map payload."""
        from app.services.query_location_resolver import query_location_resolver
        query = "Best fishing spot near Kochi"
        is_spatial, s_type = detect_spatial_intent(query)
        assert is_spatial is True
        assert s_type == "fishing_destination"

        loc_res = query_location_resolver.resolve_query_location_sync(query, mock_coastal_vessel)
        assert loc_res.is_explicit is True
        assert "Kochi" in (loc_res.query_entity_name or "")
        assert abs(loc_res.target_location.latitude - 9.9312) < 0.1

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "fishing_destination"
        assert abs(payload.target_location["latitude"] - 9.93) < 0.05
        assert abs(payload.target_location["longitude"] - 76.20) < 0.05

    def test_4_best_fishing_spot_near_goa(self, mock_coastal_vessel):
        """Test 4: 'Best fishing spot near Goa' -> fishing intent, Goa target, map payload."""
        from app.services.query_location_resolver import query_location_resolver
        query = "Best fishing spot near Goa"
        is_spatial, s_type = detect_spatial_intent(query)
        assert is_spatial is True
        assert s_type == "fishing_destination"

        loc_res = query_location_resolver.resolve_query_location_sync(query, mock_coastal_vessel)
        assert loc_res.is_explicit is True
        assert "Goa" in (loc_res.query_entity_name or "")

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "fishing_destination"
        assert abs(payload.target_location["latitude"] - 15.48) < 0.3
        assert abs(payload.target_location["longitude"] - 73.75) < 0.5

    def test_5_best_fishing_spot_near_visakhapatnam(self, mock_coastal_vessel):
        """Test 5: 'Best fishing spot near Visakhapatnam' -> fishing intent, Visakhapatnam target."""
        from app.services.query_location_resolver import query_location_resolver
        query = "Best fishing spot near Visakhapatnam"
        is_spatial, s_type = detect_spatial_intent(query)
        assert is_spatial is True
        assert s_type == "fishing_destination"

        loc_res = query_location_resolver.resolve_query_location_sync(query, mock_coastal_vessel)
        assert loc_res.is_explicit is True
        assert "Visakhapatnam" in (loc_res.query_entity_name or "")

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "fishing_destination"
        assert abs(payload.target_location["latitude"] - 17.68) < 0.1
        assert abs(payload.target_location["longitude"] - 83.28) < 0.1

    def test_6_context_followup_mumbai(self, mock_coastal_vessel):
        """Test 6: User: 'Best fishing spot near Mumbai?' -> User: 'Give me the map' reuses Mumbai target."""
        from app.services.query_location_resolver import query_location_resolver
        history = [
            {"role": "user", "content": "What's the best fishing spot near Mumbai?"},
            {"role": "assistant", "content": "I recommend Bombay High Coastal Waters ~18 km off Mumbai coast."},
        ]
        followup_query = "Give me the map"
        is_spatial, s_type = detect_spatial_intent(followup_query, conversation_history=history)
        assert is_spatial is True
        assert s_type == "fishing_destination"

        # Resolver extracts Mumbai from conversation context
        loc_res = query_location_resolver.resolve_query_location_sync(
            followup_query, mock_coastal_vessel, conversation_history=history
        )
        assert loc_res.is_explicit is True
        assert "Mumbai" in (loc_res.query_entity_name or "")

        payload = spatial_reasoner.build_spatial_payload(
            query=followup_query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
            conversation_history=history,
        )
        assert payload is not None
        assert payload.type == "fishing_destination"
        assert payload.target_location["latitude"] == 18.92
        assert payload.target_location["longitude"] == 72.75

    def test_7_context_followup_kochi(self, mock_coastal_vessel):
        """Test 7: User: 'Best fishing spot near Kochi?' -> User: 'Give me the map' reuses Kochi target."""
        from app.services.query_location_resolver import query_location_resolver
        history = [
            {"role": "user", "content": "What's the best fishing spot near Kochi?"},
            {"role": "assistant", "content": "I recommend Kochi Offshore Pelagic Zone ~14 km off Malabar coast."},
        ]
        followup_query = "Give me the map"
        is_spatial, s_type = detect_spatial_intent(followup_query, conversation_history=history)
        assert is_spatial is True
        assert s_type == "fishing_destination"

        loc_res = query_location_resolver.resolve_query_location_sync(
            followup_query, mock_coastal_vessel, conversation_history=history
        )
        assert loc_res.is_explicit is True
        assert "Kochi" in (loc_res.query_entity_name or "")

        payload = spatial_reasoner.build_spatial_payload(
            query=followup_query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
            conversation_history=history,
        )
        assert payload is not None
        assert payload.type == "fishing_destination"
        assert abs(payload.target_location["latitude"] - 9.93) < 0.05
        assert abs(payload.target_location["longitude"] - 76.20) < 0.05

    def test_8_context_update_pivot(self, mock_coastal_vessel):
        """Test 8: User: Best fishing spot near Mumbai? -> User: What about Chennai? -> User: Give me the map.
        Expected: Final map target = Chennai."""
        from app.services.query_location_resolver import query_location_resolver
        history = [
            {"role": "user", "content": "Best fishing spot near Mumbai?"},
            {"role": "assistant", "content": "Recommended: Bombay High Coastal Waters off Mumbai."},
            {"role": "user", "content": "What about Chennai?"},
            {"role": "assistant", "content": "For Chennai, the recommended ground is Chennai Offshore Ground."},
        ]
        followup_query = "Give me the map"
        is_spatial, s_type = detect_spatial_intent(followup_query, conversation_history=history)
        assert is_spatial is True

        loc_res = query_location_resolver.resolve_query_location_sync(
            followup_query, mock_coastal_vessel, conversation_history=history
        )
        # Most recent turn references Chennai
        assert loc_res.is_explicit is True
        assert "Chennai" in (loc_res.query_entity_name or "")

        payload = spatial_reasoner.build_spatial_payload(
            query=followup_query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
            conversation_history=history,
        )
        assert payload is not None
        assert payload.target_location["latitude"] == 12.85
        assert payload.target_location["longitude"] == 80.35

    def test_9_combined_safety_and_fishing_query(self, mock_coastal_vessel):
        """Test 9: 'Can I go fishing near Mumbai and what's the best spot?'
        Expected: fishing intent, safety/weather info, fishing destination, target location, map payload."""
        from app.services.query_location_resolver import query_location_resolver
        query = "Can I go fishing near Mumbai and what's the best spot?"
        is_spatial, s_type = detect_spatial_intent(query)
        assert is_spatial is True
        assert s_type == "fishing_destination"

        loc_res = query_location_resolver.resolve_query_location_sync(query, mock_coastal_vessel)
        assert loc_res.is_explicit is True
        assert "Mumbai" in (loc_res.query_entity_name or "")

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
            query_location_entity={"name": loc_res.query_entity_name},
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "fishing_destination"
        assert payload.target_location["latitude"] == 18.92
        assert payload.target_location["longitude"] == 72.75
        # Fishing recommendation query must NOT generate automatic route
        assert len(payload.routes) == 0

    def test_10_existing_functionality_current_location(self, mock_gps_vessel):
        """Test 10: 'What is my current location?' -> live GPS still works, vessel location remains correct, NO fishing target."""
        query = "What is my current location?"
        is_spatial, s_type = detect_spatial_intent(query)
        assert is_spatial is True
        assert s_type == "user_location"

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mock_gps_vessel,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "user_location"
        assert len(payload.markers) == 1
        assert payload.markers[0].marker_type == "vessel"
        assert payload.markers[0].latitude == 26.5207
        assert payload.markers[0].longitude == 80.2564
        assert payload.target_location is None

    def test_11_safety_query_safe_zone_chennai(self, mock_coastal_vessel):
        """Test 11: 'Show the safe zone near Chennai' -> safety/boundary intent, Chennai target, NO accidental fishing intent."""
        from app.services.query_location_resolver import query_location_resolver
        query = "Show the safe zone near Chennai"
        is_spatial, s_type = detect_spatial_intent(query)
        assert is_spatial is True
        assert s_type == "boundary_safety"
        assert s_type != "fishing_destination"

        loc_res = query_location_resolver.resolve_query_location_sync(query, mock_coastal_vessel)
        assert loc_res.is_explicit is True
        assert "Chennai" in (loc_res.query_entity_name or "")

        payload = spatial_reasoner.build_spatial_payload(
            query=query,
            user_location=mock_coastal_vessel,
            target_location=loc_res.target_location,
        )
        assert payload is not None
        assert payload.enabled is True
        assert payload.type == "boundary_safety"
        # No fishing routes or markers
        assert payload.routes is None or len(payload.routes) == 0
        marker_types = [m.marker_type for m in payload.markers]
        assert "fishing" not in marker_types

    def test_12_stale_location_multi_turn_sequence(self, mock_coastal_vessel):
        """Test 12: Exact user 5-query sequence:
        1. 'can i go fishing near chennai' -> Chennai
        2. 'what is the safe spot for fishing in bay of bengal' -> Bay of Bengal
        3. 'give me map' -> Bay of Bengal
        4. 'give me a spot for fishing in mumbai' -> Mumbai
        5. 'give me map' -> Mumbai (MUST NOT be stale Chennai)
        """
        from app.services.query_location_resolver import query_location_resolver
        history = []

        # Step 1: can i go fishing near chennai
        q1 = "can i go fishing near chennai"
        is_sp1, t1 = detect_spatial_intent(q1, conversation_history=history)
        assert is_sp1 is True
        assert t1 == "fishing_destination"
        loc1 = query_location_resolver.resolve_query_location_sync(q1, mock_coastal_vessel, history)
        p1 = spatial_reasoner.build_spatial_payload(
            query=q1, user_location=mock_coastal_vessel, target_location=loc1.target_location,
            query_location_entity={"name": loc1.query_entity_name}, conversation_history=history
        )
        assert p1 is not None
        assert p1.target_location["latitude"] == 12.85
        assert p1.target_location["longitude"] == 80.35
        history.append({"role": "user", "content": q1})
        history.append({"role": "assistant", "content": "Chennai conditions are suitable."})

        # Step 2: what is the safe spot for fishing in bay of bengal
        q2 = "what is the safe spot for fishing in bay of bengal"
        is_sp2, t2 = detect_spatial_intent(q2, conversation_history=history)
        assert is_sp2 is True
        assert t2 == "fishing_destination"
        loc2 = query_location_resolver.resolve_query_location_sync(q2, mock_coastal_vessel, history)
        assert "Bay of Bengal" in (loc2.query_entity_name or "")
        p2 = spatial_reasoner.build_spatial_payload(
            query=q2, user_location=mock_coastal_vessel, target_location=loc2.target_location,
            query_location_entity={"name": loc2.query_entity_name}, conversation_history=history
        )
        assert p2 is not None
        assert p2.target_location["latitude"] == 16.0
        assert p2.target_location["longitude"] == 87.0
        assert "Bay of Bengal" in p2.title
        history.append({"role": "user", "content": q2})
        history.append({"role": "assistant", "content": "Operational caution in Bay of Bengal."})

        # Step 3: give me map
        q3 = "give me map"
        is_sp3, t3 = detect_spatial_intent(q3, conversation_history=history)
        assert is_sp3 is True
        loc3 = query_location_resolver.resolve_query_location_sync(q3, mock_coastal_vessel, history)
        assert "Bay of Bengal" in (loc3.query_entity_name or "")
        p3 = spatial_reasoner.build_spatial_payload(
            query=q3, user_location=mock_coastal_vessel, target_location=loc3.target_location,
            query_location_entity={"name": loc3.query_entity_name}, conversation_history=history
        )
        assert p3 is not None
        assert p3.target_location["latitude"] == 16.0
        assert p3.target_location["longitude"] == 87.0
        assert "Bay of Bengal" in p3.title
        history.append({"role": "user", "content": q3})
        history.append({"role": "assistant", "content": "Displaying Bay of Bengal map."})

        # Step 4: give me a spot for fishing in mumbai
        q4 = "give me a spot for fishing in mumbai"
        is_sp4, t4 = detect_spatial_intent(q4, conversation_history=history)
        assert is_sp4 is True
        assert t4 == "fishing_destination"
        loc4 = query_location_resolver.resolve_query_location_sync(q4, mock_coastal_vessel, history)
        assert "Mumbai" in (loc4.query_entity_name or "")
        p4 = spatial_reasoner.build_spatial_payload(
            query=q4, user_location=mock_coastal_vessel, target_location=loc4.target_location,
            query_location_entity={"name": loc4.query_entity_name}, conversation_history=history
        )
        assert p4 is not None
        assert p4.target_location["latitude"] == 18.92
        assert p4.target_location["longitude"] == 72.75
        assert "Bombay High" in p4.title or "Mumbai" in p4.title
        history.append({"role": "user", "content": q4})
        history.append({"role": "assistant", "content": "Mumbai conditions are suitable."})

        # Step 5: give me map -> MUST resolve to Mumbai, NOT stale Chennai!
        q5 = "give me map"
        is_sp5, t5 = detect_spatial_intent(q5, conversation_history=history)
        assert is_sp5 is True
        loc5 = query_location_resolver.resolve_query_location_sync(q5, mock_coastal_vessel, history)
        assert "Mumbai" in (loc5.query_entity_name or "")
        p5 = spatial_reasoner.build_spatial_payload(
            query=q5, user_location=mock_coastal_vessel, target_location=loc5.target_location,
            query_location_entity={"name": loc5.query_entity_name}, conversation_history=history
        )
        assert p5 is not None
        assert p5.target_location["latitude"] == 18.92
        assert p5.target_location["longitude"] == 72.75
        assert "Bombay High" in p5.title or "Mumbai" in p5.title
        assert p5.target_location["latitude"] != 12.85  # Explicitly NOT Chennai

