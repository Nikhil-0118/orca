"""
Top-level /api endpoints: query, safety-check, health (Phase 8.2).
These are the primary endpoints consumed by the ORCA frontend.
"""
from fastapi import APIRouter, HTTPException, status
from app.core.graph import orca_graph
from app.schemas.query import Location, LocationContext, QueryRequest, QueryResponse
from app.schemas.safety import SafetyCheckRequest, SafetyCheckResponse
from app.services.planner import orca_planner
from app.services.conversational_llm import generate_conversational_response
from app.services.geofence_service import geofence_service, SafetyState
from app.agents.final_reasoning_agent import sanitize_svg_markers
from app.services.spatial_reasoner import spatial_reasoner

router = APIRouter(prefix="/api", tags=["ORCA Core API"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict:
    """Basic liveness probe."""
    return {"status": "ok"}


def _normalize_request_location(request: QueryRequest) -> LocationContext:
    """Normalize input location into a canonical LocationContext without hidden defaults."""
    req_loc = request.location
    if req_loc is None:
        if request.is_demo_mode:
            return LocationContext(
                latitude=13.0827,
                longitude=80.2707,
                source="demo",
                is_demo=True,
                label="Chennai Coastal Region (SIH Demo Mode)",
            )
        return LocationContext(
            latitude=None,
            longitude=None,
            source="unavailable",
            is_demo=False,
            label="Location unavailable",
        )

    if isinstance(req_loc, LocationContext):
        if req_loc.latitude is not None and (req_loc.latitude < -90.0 or req_loc.latitude > 90.0):
            raise HTTPException(status_code=400, detail=f"Latitude {req_loc.latitude} must be between -90 and 90 degrees.")
        if req_loc.longitude is not None and (req_loc.longitude < -180.0 or req_loc.longitude > 180.0):
            raise HTTPException(status_code=400, detail=f"Longitude {req_loc.longitude} must be between -180 and 180 degrees.")
        return req_loc

    if isinstance(req_loc, Location):
        if req_loc.lat < -90.0 or req_loc.lat > 90.0:
            raise HTTPException(status_code=400, detail=f"Latitude {req_loc.lat} must be between -90 and 90 degrees.")
        if req_loc.lon < -180.0 or req_loc.lon > 180.0:
            raise HTTPException(status_code=400, detail=f"Longitude {req_loc.lon} must be between -180 and 180 degrees.")
        return LocationContext(
            latitude=req_loc.lat,
            longitude=req_loc.lon,
            source="demo" if request.is_demo_mode else "browser_gps",
            is_demo=bool(request.is_demo_mode),
        )

    if isinstance(req_loc, dict):
        raw_lat = req_loc.get("latitude") if req_loc.get("latitude") is not None else req_loc.get("lat")
        raw_lon = req_loc.get("longitude") if req_loc.get("longitude") is not None else req_loc.get("lon")

        parsed_lat = None
        parsed_lon = None
        if raw_lat is not None:
            try:
                parsed_lat = float(raw_lat)
                if parsed_lat < -90.0 or parsed_lat > 90.0:
                    raise HTTPException(status_code=400, detail=f"Latitude {parsed_lat} must be between -90 and 90 degrees.")
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid latitude value: {raw_lat}")

        if raw_lon is not None:
            try:
                parsed_lon = float(raw_lon)
                if parsed_lon < -180.0 or parsed_lon > 180.0:
                    raise HTTPException(status_code=400, detail=f"Longitude {parsed_lon} must be between -180 and 180 degrees.")
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid longitude value: {raw_lon}")

        is_demo = bool(req_loc.get("is_demo", request.is_demo_mode or False))
        is_approximate = bool(req_loc.get("is_approximate", False))
        source = req_loc.get("source", "demo" if is_demo else ("browser_gps" if parsed_lat is not None else "unavailable"))
        accuracy_m = req_loc.get("accuracy_m")
        timestamp = req_loc.get("timestamp")
        label = req_loc.get("label")

        return LocationContext(
            latitude=parsed_lat,
            longitude=parsed_lon,
            source=source,
            accuracy_m=float(accuracy_m) if accuracy_m is not None else None,
            timestamp=str(timestamp) if timestamp else None,
            is_demo=is_demo,
            is_approximate=is_approximate,
            label=label,
        )

    return LocationContext(
        latitude=None,
        longitude=None,
        source="unavailable",
        is_demo=False,
    )


@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Accept a plain-language query. Dynamically planned by ORCAPlanner:
      - conversation: Conversational LLM generates dynamic response
      - utility: Real system clock/location data formatted by LLM
      - marine: Minimal specialist agent subset executed and synthesized
      - safety: Safety-aware pipeline with deterministic risk enforcement
    """
    loc_ctx = _normalize_request_location(request)
    if loc_ctx.latitude is not None and loc_ctx.longitude is not None:
        from app.services.location_resolver import location_resolver
        resolved = await location_resolver.resolve(
            loc_ctx.latitude, loc_ctx.longitude, source=loc_ctx.source, is_demo=loc_ctx.is_demo
        )
        if not loc_ctx.resolved_place and resolved.place_name:
            loc_ctx.resolved_place = resolved.place_name
        if not loc_ctx.geographic_type and resolved.geographic_type:
            loc_ctx.geographic_type = resolved.geographic_type
        if not loc_ctx.label and resolved.place_name:
            state_s = f", {resolved.state}" if resolved.state else ""
            loc_ctx.label = f"{resolved.place_name}{state_s}"
        if resolved.bhuvan_location:
            loc_ctx.bhuvan_location = resolved.bhuvan_location

    from app.services.query_location_resolver import query_location_resolver
    query_loc_res = await query_location_resolver.resolve_query_location(
        request.query, loc_ctx, request.conversation_history
    )
    target_loc_ctx = query_loc_res.target_location

    target_loc_dict = target_loc_ctx.model_dump()
    target_loc_dict["lat"] = target_loc_ctx.latitude
    target_loc_dict["lon"] = target_loc_ctx.longitude
    target_loc_dict["vessel_location"] = loc_ctx.model_dump()

    # ── 1. Dynamic Agentic Planning ──────────────────────────────────────────
    plan = await orca_planner.plan(
        query=request.query,
        conversation_history=request.conversation_history,
        location=target_loc_dict,
    )

    # ── 2. Conversation & Utility Branches (Bypass multi-agent graph) ─────────
    if plan.response_mode in ("conversation", "utility"):
        # Distinguish self-location inquiry from explicit query location
        is_self_location = plan.intent in ("LOCATION_CURRENT", "location") or (
            not query_loc_res.is_explicit and any(w in request.query.lower() for w in ["where am i", "my location", "my current location", "my position", "what is my location"])
        )

        if is_self_location:
            eval_loc_ctx = loc_ctx
        elif query_loc_res.is_explicit:
            eval_loc_ctx = target_loc_ctx
        else:
            eval_loc_ctx = loc_ctx

        llm_loc = eval_loc_ctx.model_dump()
        llm_loc["lat"] = eval_loc_ctx.latitude
        llm_loc["lon"] = eval_loc_ctx.longitude
        llm_loc["resolved_place"] = eval_loc_ctx.resolved_place
        llm_loc["geographic_type"] = eval_loc_ctx.geographic_type
        llm_loc["is_explicit"] = query_loc_res.is_explicit
        llm_loc["entity_type"] = query_loc_res.entity_type
        llm_loc["coastline_km"] = query_loc_res.coastline_length_km
        llm_loc["bordering_oceans"] = query_loc_res.bordering_oceans
        llm_loc["vessel_location"] = loc_ctx.model_dump()

        answer = await generate_conversational_response(
            intent=plan.intent,
            user_query=request.query,
            tools=plan.tools,
            conversation_history=request.conversation_history,
            location=llm_loc,
        )
        spatial_payload = spatial_reasoner.build_spatial_payload(
            query=request.query,
            user_location=loc_ctx,
            target_location=eval_loc_ctx,
            query_location_entity={
                "name": query_loc_res.query_entity_name,
                "source": query_loc_res.location_source,
                "type": query_loc_res.entity_type,
                "is_explicit": query_loc_res.is_explicit,
                "state": query_loc_res.state_name,
            },
            conversation_history=request.conversation_history,
        )
        return QueryResponse(
            mode=plan.response_mode,
            answer=sanitize_svg_markers(answer),
            location=eval_loc_ctx,
            user_location=loc_ctx,
            query_location={
                "name": query_loc_res.query_entity_name,
                "source": query_loc_res.location_source,
                "type": query_loc_res.entity_type,
                "is_explicit": query_loc_res.is_explicit,
                "state": query_loc_res.state_name,
                "coastline_km": query_loc_res.coastline_length_km,
                "bordering_oceans": query_loc_res.bordering_oceans,
            },
            decision=None,
            risk_level="none",
            recommendations=[],
            risk_summary=None,
            key_conditions=[],
            best_time=None,
            reasoning_summary=None,
            evidence=[],
            structured_evidence=[],
            data_limitations=[],
            agents_used=[],
            spatial=spatial_payload,
        )

    # ── 3. Marine / Safety Branch: Execute Selected Agents in LangGraph ───────
    initial_state = {
        "query": request.query,
        "location": target_loc_dict,
        "session_id": request.session_id,
        "selected_agents": plan.agents,
        "safety_required": plan.safety_required,
        "conversation_history": request.conversation_history,
        "eo_result": None,
        "ocean_result": None,
        "weather_result": None,
        "safety_result": None,
        "ecosystem_result": None,
        "evidence": [],
        "risk_level": "unknown",
        "final_answer": "",
        "recommendations": [],
    }

    result = await orca_graph.ainvoke(initial_state)

    final_answer = result.get("final_answer") or "No operational data available."
    evidence = result.get("evidence") or []
    risk_level = result.get("risk_level") or "low"
    recommendations = result.get("recommendations") or []
    risk_summary = result.get("risk_summary")
    structured_evidence = result.get("structured_evidence") or []
    data_limitations = result.get("data_limitations") or []
    agents_used = result.get("agents_used") or []
    decision = result.get("decision")
    key_conditions = result.get("key_conditions") or []
    best_time = result.get("best_time")
    reasoning_summary = result.get("reasoning_summary")

    resp_loc = target_loc_ctx if query_loc_res.is_explicit else loc_ctx
    spatial_payload = spatial_reasoner.build_spatial_payload(
        query=request.query,
        user_location=loc_ctx,
        target_location=resp_loc,
        query_location_entity={
            "name": query_loc_res.query_entity_name,
            "source": query_loc_res.location_source,
            "type": query_loc_res.entity_type,
            "is_explicit": query_loc_res.is_explicit,
            "state": query_loc_res.state_name,
        },
        safety_result=result.get("safety_result"),
        conversation_history=request.conversation_history,
    )
    return QueryResponse(
        mode=plan.response_mode,
        answer=sanitize_svg_markers(final_answer),
        location=resp_loc,
        user_location=loc_ctx,
        query_location={
            "name": query_loc_res.query_entity_name,
            "source": query_loc_res.location_source,
            "type": query_loc_res.entity_type,
            "is_explicit": query_loc_res.is_explicit,
            "state": query_loc_res.state_name,
            "coastline_km": query_loc_res.coastline_length_km,
            "bordering_oceans": query_loc_res.bordering_oceans,
        },
        decision=sanitize_svg_markers(decision),
        risk_level=risk_level,
        recommendations=sanitize_svg_markers(recommendations),
        risk_summary=sanitize_svg_markers(risk_summary),
        key_conditions=sanitize_svg_markers(key_conditions),
        best_time=sanitize_svg_markers(best_time),
        reasoning_summary=sanitize_svg_markers(reasoning_summary),
        evidence=sanitize_svg_markers(evidence),
        structured_evidence=sanitize_svg_markers(structured_evidence),
        data_limitations=sanitize_svg_markers(data_limitations),
        agents_used=agents_used,
        evidence_summary=result.get("evidence_summary"),
        source_reliability=result.get("source_reliability"),
        data_quality=result.get("data_quality"),
        conflicts=[c.model_dump() if hasattr(c, "model_dump") else c for c in (result.get("conflicts") or [])],
        human_response=result.get("human_response"),
        spatial=spatial_payload,
    )


@router.post("/safety-check", response_model=SafetyCheckResponse, status_code=status.HTTP_200_OK)
async def safety_check(request: SafetyCheckRequest) -> SafetyCheckResponse:
    """
    Fast, non-LLM boundary proximity check.
    Independent offline safety path (Phase 7).
    """
    prev = SafetyState(request.prev_state) if request.prev_state and request.prev_state in SafetyState.__members__ else None
    eval_res = geofence_service.evaluate_position(request.lat, request.lon, prev_state=prev)

    inside = eval_res.state != SafetyState.BREACH
    alert_level_str = (
        "critical" if eval_res.state == SafetyState.BREACH
        else "warning" if eval_res.state == SafetyState.WARNING
        else "caution" if eval_res.state == SafetyState.APPROACHING
        else "none"
    )

    return SafetyCheckResponse(
        inside_boundary=inside,
        distance_to_boundary_km=eval_res.distance_to_boundary_km,
        alert_level=alert_level_str,
        state=eval_res.state.value,
        severity=eval_res.severity.value,
        bearing_degrees=eval_res.bearing_degrees,
        nearest_boundary_name=eval_res.nearest_boundary_name,
        alert_title=eval_res.alert_title,
        alert_message=eval_res.alert_message,
        demo_only=True,
    )
