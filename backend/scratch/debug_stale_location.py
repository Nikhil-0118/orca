import asyncio
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.query_location_resolver import query_location_resolver
from app.schemas.query import LocationContext
from app.services.spatial_reasoner import spatial_reasoner

async def test():
    client_loc = LocationContext(latitude=13.0827, longitude=80.2707, label="Chennai Harbor", source="browser_gps")
    history = []
    
    queries = [
        "can i go fishing near chennai",
        "what is the safe spot for fishing in bay of bengal",
        "give me map",
        "give me a spot for fishing in mumbai",
        "give me map"
    ]
    
    for q in queries:
        print(f"=== QUERY: {q} ===")
        q_res = await query_location_resolver.resolve_query_location(q, client_loc, history)
        print(f"Resolved entity: {q_res.query_entity_name}, source: {q_res.location_source}, target_loc: {q_res.target_location.label}")
        payload = spatial_reasoner.build_spatial_payload(
            query=q,
            user_location=client_loc,
            target_location=q_res.target_location,
            query_location_entity={
                "name": q_res.query_entity_name,
                "source": q_res.location_source,
                "type": q_res.entity_type,
                "is_explicit": q_res.is_explicit,
                "state": q_res.state_name,
            },
            conversation_history=history
        )
        if payload:
            print("Spatial payload title:", payload.title)
            print("Target location:", payload.target_location)
        else:
            print("No spatial payload")
            
        history.append({"role": "user", "content": q})
        ans = f"Operational advice for {q_res.query_entity_name or q}."
        history.append({"role": "assistant", "content": ans})
        print()

if __name__ == "__main__":
    asyncio.run(test())
