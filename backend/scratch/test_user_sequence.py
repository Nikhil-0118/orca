import asyncio
from app.schemas.query import LocationContext, QueryRequest
from app.api.endpoints import query as query_endpoint
from app.services.query_location_resolver import query_location_resolver
from app.services.spatial_reasoner import spatial_reasoner, detect_spatial_intent

async def run_sequence():
    vessel_loc = LocationContext(
        latitude=13.0827,
        longitude=80.2707,
        label="Chennai Harbor",
        source="browser_gps"
    )

    queries = [
        "can i go fishing near chennai",
        "what is the safe spot for fishing in bay of bengal",
        "give me map",
        "give me a spot for fishing in mumbai",
        "give me map"
    ]

    history = []

    for idx, q in enumerate(queries, 1):
        print(f"\n--- STEP {idx}: {q} ---")
        
        # 1. Spatial intent detection
        is_sp, sp_type = detect_spatial_intent(q, conversation_history=history)
        print(f"detect_spatial_intent: is_spatial={is_sp}, type={sp_type}")
        
        # 2. Location resolution
        q_res = await query_location_resolver.resolve_query_location(q, vessel_loc, history)
        print(f"query_location_resolver: entity={q_res.query_entity_name}, is_explicit={q_res.is_explicit}, source={q_res.location_source}")
        print(f"target_location: {q_res.target_location.label} ({q_res.target_location.latitude}, {q_res.target_location.longitude})")
        
        # 3. Spatial reasoner payload
        payload = spatial_reasoner.build_spatial_payload(
            query=q,
            user_location=vessel_loc,
            target_location=q_res.target_location,
            query_location_entity={
                "name": q_res.query_entity_name,
                "source": q_res.location_source,
                "type": q_res.entity_type,
                "is_explicit": q_res.is_explicit,
                "state": q_res.state_name,
            },
            conversation_history=history,
        )
        
        if payload:
            print(f"SPATIAL PAYLOAD:")
            print(f"  Title: {payload.title}")
            print(f"  Target: {payload.target_location}")
            if payload.routes:
                r = payload.routes[0]
                print(f"  Route: {r.origin.get('label')} -> {r.destination.get('label')}")
                print(f"  Route dest coords: {r.destination.get('latitude')}, {r.destination.get('longitude')}")
        else:
            print("No spatial payload.")
            
        history.append({"role": "user", "content": q})
        # If payload was built, assistant message in a real chatbot might say something
        ans = f"Assistant answer for {q}"
        history.append({"role": "assistant", "content": ans})

if __name__ == "__main__":
    asyncio.run(run_sequence())
