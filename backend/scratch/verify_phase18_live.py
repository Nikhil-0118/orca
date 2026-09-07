"""
Live Acceptance Verification Script for Phase 18: Marine Map & Spatial Intelligence.
Executes all 8 exact acceptance queries against http://127.0.0.1:8000/api/query
"""
import json
import httpx

QUERIES = [
    "What is the chlorophyll concentration near Chennai?",
    "What is the weather near Chennai?",
    "Can I go fishing near Chennai?",
    "Show my current location",
    "Show the safe zone near Chennai",
    "How far am I from the boundary?",
    "Show me a route from Chennai to Pondicherry",
    "Show dangerous areas around my boat",
]

BASE_URL = "http://127.0.0.1:8000/api/query"
CHENNAI_LOC = {
    "latitude": 13.0827,
    "longitude": 80.2707,
    "source": "browser_gps",
    "accuracy_m": 15,
    "label": "Chennai Coast, Tamil Nadu",
}

def run_tests():
    results = {}
    client = httpx.Client(timeout=60.0)

    for q in QUERIES:
        print(f"\n--- Testing: '{q}' ---")
        payload = {
            "query": q,
            "location": CHENNAI_LOC,
            "session_id": f"phase18-verify-{abs(hash(q))}",
        }
        res = client.post(BASE_URL, json=payload)
        assert res.status_code == 200, f"Query failed with code {res.status_code}: {res.text}"
        data = res.json()

        spatial = data.get("spatial")
        human_resp = data.get("human_response")
        answer = data.get("answer", "")

        results[q] = {
            "status_code": res.status_code,
            "has_spatial": spatial is not None and spatial.get("enabled") is True,
            "spatial_type": spatial.get("type") if spatial else None,
            "spatial_title": spatial.get("title") if spatial else None,
            "markers_count": len(spatial.get("markers", [])) if spatial else 0,
            "zones_count": len(spatial.get("zones", [])) if spatial else 0,
            "routes_count": len(spatial.get("routes", [])) if spatial else 0,
            "route_distance_km": spatial.get("routes", [{}])[0].get("distance_km") if spatial and spatial.get("routes") else None,
            "route_bearing_deg": spatial.get("routes", [{}])[0].get("bearing_degrees") if spatial and spatial.get("routes") else None,
            "boundary_distance_km": spatial.get("boundary_distance_km") if spatial else None,
            "boundary_bearing_deg": spatial.get("boundary_bearing_deg") if spatial else None,
            "safety_state": spatial.get("safety_state") if spatial else None,
            "decision": data.get("decision"),
            "human_decision_code": human_resp.get("decision_code") if human_resp else None,
            "answer_preview": answer[:150] + "...",
        }
        print(f"  -> has_spatial: {results[q]['has_spatial']}, type: {results[q]['spatial_type']}")

    out_path = "scratch/phase18_acceptance_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nVerification results written to {out_path}")

if __name__ == "__main__":
    run_tests()
