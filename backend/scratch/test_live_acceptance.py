import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/query"
LOCATION = {"lat": 13.0827, "lon": 80.2707}

QUERIES = [
    "Can I go fishing near Chennai?",
    "When should I go fishing near Chennai?",
    "What is the chlorophyll concentration near Chennai?",
    "Will I get more fish near Chennai?",
    "What is the weather near Chennai?",
    "Is it safe near Chennai?",
]

print("=" * 80)
print("LIVE BACKEND ACCEPTANCE TESTING — 6 EXACT USER QUERIES")
print("=" * 80)

results = {}

for i, q in enumerate(QUERIES, 1):
    payload = {
        "query": q,
        "location": LOCATION,
        "session_id": f"acceptance-test-{i}",
    }
    print(f"\n[{i}/6] Testing: '{q}'")
    resp = requests.post(BASE_URL, json=payload, timeout=45)
    if resp.status_code != 200:
        print(f"FAILED with status {resp.status_code}: {resp.text}")
        continue
    data = resp.json()
    results[q] = data

    print(f"Backend Decision: {data.get('decision')}")
    print(f"Risk Level: {data.get('risk_level')}")
    
    hr = data.get("human_response") or {}
    print(f"Human Decision Code: {hr.get('decision_code')}")
    print(f"Direct Answer: {hr.get('direct_answer')}")
    print(f"Explanation: {hr.get('explanation')}")
    print(f"Best Time: {hr.get('best_time')}")
    print(f"Conditions: {hr.get('conditions')}")
    print(f"Safety: {hr.get('safety_notice')}")
    print(f"Data Quality: {hr.get('data_quality_note')}")
    print(f"Sources: {hr.get('sources')}")
    print("-" * 40)
    print("Full Primary Formatted Answer:")
    print(data.get("answer"))
    print("=" * 80)

# Save results for detailed inspection
with open("scratch/acceptance_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nAcceptance test queries completed successfully.")
