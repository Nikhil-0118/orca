import requests
import json

queries = [
    "Can I go fishing near Chennai?",
    "When should I go fishing near Chennai?",
    "What is the chlorophyll concentration near Chennai?",
    "Will I get more fish near Chennai?",
    "What is the weather near Chennai?",
    "Is it safe near Chennai?",
]

for q in queries:
    resp = requests.post("http://127.0.0.1:8000/api/query", json={
        "query": q,
        "location": {"lat": 13.0827, "lon": 80.2707},
        "session_id": "live-audit-sih"
    })
    data = resp.json()
    print("=" * 60)
    print(f"QUERY: {q}")
    print("DECISION:", data.get("decision"))
    hr = data.get("human_response") or {}
    print("HUMAN_RESPONSE DECISION_CODE:", hr.get("decision_code"))
    print("--- FULL FINAL ANSWER ---")
    print(data.get("answer"))
    print("=" * 60)
