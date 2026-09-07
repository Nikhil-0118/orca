import httpx
import json
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def test_api():
    url = "http://127.0.0.1:8000/api/query"
    
    queries = [
        "can i go fishing near chennai",
        "what is the safe spot for fishing in bay of bengal",
        "give me map",
        "give me a spot for fishing in mumbai",
        "give me map"
    ]
    
    history = []
    
    for q in queries:
        print(f"\n==========================================")
        print(f"QUERY: {q}")
        print(f"==========================================")
        payload = {
            "query": q,
            "session_id": "test-session-stale-loc",
            "conversation_history": history,
            "location": {
                "latitude": 13.0827,
                "longitude": 80.2707,
                "label": "Chennai Harbor",
                "source": "browser_gps"
            }
        }
        resp = httpx.post(url, json=payload, timeout=30.0)
        data = resp.json()
        
        print("Status code:", resp.status_code)
        print("Mode:", data.get("mode"))
        print("Location:", data.get("location"))
        print("Query Location:", data.get("query_location"))
        ans_snippet = (data.get("answer") or "")[:200]
        print(f"Answer snippet: {ans_snippet}...")
        spatial = data.get("spatial")
        if spatial:
            print(">>> SPATIAL PAYLOAD:")
            print("  Type:", spatial.get("type"))
            print("  Title:", spatial.get("title"))
            print("  Target location:", spatial.get("target_location"))
            for m in spatial.get("markers", []):
                print(f"  Marker: {m.get('id')} -> {m.get('label')}: {m.get('description')}")
        else:
            print(">>> NO SPATIAL PAYLOAD")
            
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": data.get("answer") or ""})

if __name__ == "__main__":
    test_api()
