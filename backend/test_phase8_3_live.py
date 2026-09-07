"""
Live End-to-End Test Suite for ORCA Phase 8.3 — Decision-First Maritime Engine.
Evaluates all 15 required query scenarios against the running FastAPI backend.
"""
import json
import sys
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ENDPOINT = "http://127.0.0.1:8000/api/query"

TEST_QUERIES = [
    # 1. Casual Greeting
    {
        "id": "Q01_greeting",
        "query": "hi",
        "expected_mode": "conversation",
        "check": lambda r: r["mode"] == "conversation" and len(r["answer"]) < 250 and not r.get("decision"),
    },
    # 2. Casual Social
    {
        "id": "Q02_social",
        "query": "how are you?",
        "expected_mode": "conversation",
        "check": lambda r: r["mode"] == "conversation" and len(r["answer"]) < 250,
    },
    # 3. Utility Clock
    {
        "id": "Q03_time",
        "query": "what time is it?",
        "expected_mode": "utility",
        "check": lambda r: r["mode"] == "utility" and ("IST" in r["answer"] or ":" in r["answer"]),
    },
    # 4. Utility Date
    {
        "id": "Q04_date",
        "query": "what is today's date?",
        "expected_mode": "utility",
        "check": lambda r: r["mode"] == "utility" and any(m in r["answer"] for m in ["2026", "September", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),
    },
    # 5. Location Query
    {
        "id": "Q05_location",
        "query": "what is my current location?",
        "expected_mode": "utility",
        "check": lambda r: ("chennai" in r["answer"].lower() or "13.08" in r["answer"] or "coast" in r["answer"].lower()) and "sst" not in r["answer"].lower(),
    },
    # 6. Weather Query
    {
        "id": "Q06_weather",
        "query": "what is the weather here?",
        "expected_mode": "marine",
        "check": lambda r: r["mode"] == "marine" and any(w in r["answer"].lower() for w in ["weather", "wind", "visibility", "condition", "moderate"]),
    },
    # 7. Ocean Query
    {
        "id": "Q07_ocean",
        "query": "what are the ocean conditions?",
        "expected_mode": "marine",
        "check": lambda r: r["mode"] == "marine" and any(w in r["answer"].lower() for w in ["ocean", "sea", "surface", "temperature", "sst", "wave"]),
    },
    # 8. Activity Feasibility: Fishing
    {
        "id": "Q08_fishing",
        "query": "can I go fishing?",
        "expected_mode": "marine",
        "check": lambda r: r.get("decision") is not None and "label" in r["decision"] and any(w in r["decision"]["label"].lower() for w in ["recommend", "caution", "avoid"]),
    },
    # 9. Timing Query (No Fake Precision)
    {
        "id": "Q09_best_time",
        "query": "what time is best for fishing?",
        "expected_mode": "marine",
        "check": lambda r: r.get("best_time") is not None and (
            r["best_time"]["available"] is False or "reliable" in str(r["best_time"].get("basis", "")).lower()
        ),
    },
    # 10. Navigational Safety
    {
        "id": "Q10_safety_travel",
        "query": "is it safe to travel?",
        "expected_mode": "safety",
        "check": lambda r: r["risk_level"] in ("low", "moderate", "high", "critical") and len(r["recommendations"]) > 0,
    },
    # 11. Location Risk
    {
        "id": "Q11_location_risk",
        "query": "what is the risk near my location?",
        "expected_mode": "safety",
        "check": lambda r: r["risk_level"] in ("low", "moderate", "high", "critical"),
    },
    # 12. Risk Percentage (No Fake Percentage)
    {
        "id": "Q12_risk_percentage",
        "query": "what is the risk percentage?",
        "expected_mode": "safety",
        "check": lambda r: "%" not in r["answer"] or "categorical" in r["answer"].lower() or "level" in r["answer"].lower(),
    },
    # 13. Complex Regional Query
    {
        "id": "Q13_sri_lanka_env",
        "query": "what is the environment near Sri Lankan side?",
        "expected_mode": "marine",
        "check": lambda r: r["mode"] in ("marine", "safety") and len(r["answer"]) > 20,
    },
    # 14. Contextual Follow-Up
    {
        "id": "Q14_follow_up",
        "query": "should I go fishing there?",
        "conversation_history": [
            {"role": "user", "content": "what is the environment near Sri Lankan side?"},
            {"role": "assistant", "content": "The region near the Sri Lanka maritime boundary requires high caution due to boundary restrictions."}
        ],
        "expected_mode": "marine",
        "check": lambda r: r["mode"] in ("marine", "safety") and r.get("decision") is not None,
    },
    # 15. User-Facing Reasoning Request
    {
        "id": "Q15_reasoning",
        "query": "give me the detailed reasoning",
        "conversation_history": [
            {"role": "user", "content": "can I go fishing?"},
            {"role": "assistant", "content": "Fishing is recommended with caution right now."}
        ],
        "expected_mode": "marine",
        "check": lambda r: len(r["answer"]) > 20 and ("prompt" not in r["answer"].lower()),
    },
]

def run_tests():
    passed = 0
    failed = 0
    results = []

    print(f"=== ORCA Phase 8.3 Live Matrix Evaluation ({len(TEST_QUERIES)} scenarios) ===")

    for item in TEST_QUERIES:
        payload = {
            "query": item["query"],
            "location": {"lat": 13.0827, "lon": 80.2707},
            "session_id": f"phase8-3-test-{item['id']}",
            "conversation_history": item.get("conversation_history"),
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=45.0) as resp:
                status_code = resp.getcode()
                resp_body = json.loads(resp.read().decode("utf-8"))

                is_ok = item["check"](resp_body)
                if is_ok:
                    passed += 1
                    status_str = "PASS"
                else:
                    failed += 1
                    status_str = "FAIL (Check predicate failed)"

                print(f"[{status_str}] {item['id']}: '{item['query']}'")
                print(f"       Mode: {resp_body.get('mode')} | Risk: {resp_body.get('risk_level')}")
                print(f"       Answer: {resp_body.get('answer')[:120]}...")
                if resp_body.get("decision"):
                    print(f"       Decision: {resp_body['decision'].get('label')} ({resp_body['decision'].get('confidence')})")
                if resp_body.get("key_conditions"):
                    print(f"       Key Conditions: {resp_body.get('key_conditions')[:2]}")
                if resp_body.get("best_time"):
                    print(f"       Best Time: avail={resp_body['best_time'].get('available')}, basis={str(resp_body['best_time'].get('basis'))[:60]}...")
                print()

                results.append({
                    "id": item["id"],
                    "query": item["query"],
                    "status": status_str,
                    "response": resp_body,
                })

        except Exception as e:
            failed += 1
            print(f"[FAIL (Exception)] {item['id']}: {e}")
            results.append({
                "id": item["id"],
                "query": item["query"],
                "status": f"FAIL: {type(e).__name__}: {e}",
            })

    print(f"=== SUMMARY: {passed}/{len(TEST_QUERIES)} PASSED ({failed} failed) ===")
    return passed, failed, results

if __name__ == "__main__":
    run_tests()
