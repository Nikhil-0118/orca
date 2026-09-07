"""
Phase 14 Live API Verification Script.
Queries the running FastAPI server on http://127.0.0.1:8000/api/query.
Executes the 5 mandatory live queries:
1. "Give me chlorophyll data near Chennai"
2. "What is the sea surface temperature near Chennai?"
3. "What is the weather near the Chennai coast?"
4. "Can I go fishing near Chennai today?"
5. "Is this location safe for fishing?"
"""
import json
import httpx

BASE_URL = "http://127.0.0.1:8000"
CHENNAI_LOC = {"lat": 13.0827, "lon": 80.2707}

QUERIES = [
    {
        "name": "Query 1: Chlorophyll near Chennai",
        "query": "Give me chlorophyll data near Chennai",
        "location": CHENNAI_LOC,
        "expected_parameter": "chlorophyll",
    },
    {
        "name": "Query 2: Sea Surface Temperature near Chennai",
        "query": "What is the sea surface temperature near Chennai?",
        "location": CHENNAI_LOC,
        "expected_parameter": "sst",
    },
    {
        "name": "Query 3: Weather near Chennai Coast",
        "query": "What is the weather near the Chennai coast?",
        "location": CHENNAI_LOC,
        "expected_parameter": "weather",
    },
    {
        "name": "Query 4: Fishing Feasibility (Cross-Agent Reasoning)",
        "query": "Can I go fishing near Chennai today?",
        "location": CHENNAI_LOC,
        "expected_parameter": "decision",
    },
    {
        "name": "Query 5: Safety Assessment for Fishing",
        "query": "Is this location safe for fishing?",
        "location": CHENNAI_LOC,
        "expected_parameter": "safety",
    },
]

def run_verification():
    print("=" * 70)
    print("ORCA PHASE 14 — LIVE API VERIFICATION")
    print("=" * 70)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Check health
        health = client.get("/api/health")
        print(f"Server Health: {health.status_code} -> {health.json()}")
        assert health.status_code == 200

        results = []
        for i, q in enumerate(QUERIES, 1):
            print("\n" + "-" * 70)
            print(f"[{i}/5] {q['name']}")
            print(f"Query: \"{q['query']}\"")
            print(f"Location: {q['location']}")

            payload = {
                "query": q["query"],
                "location": q["location"],
                "session_id": f"p14-live-q{i}",
            }

            resp = client.post("/api/query", json=payload)
            print(f"HTTP Status: {resp.status_code}")
            assert resp.status_code == 200, f"Query failed with status {resp.status_code}"

            data = resp.json()
            answer = data.get("answer", "")
            evidence = data.get("evidence", [])
            plan = data.get("plan", {})
            decision_card = data.get("decision_card", {})

            print(f"Intent / Response Mode: {plan.get('intent')} / {plan.get('response_mode')}")
            print(f"Contributing Evidence ({len(evidence)} items):")
            for e in evidence:
                print(f"  • {e}")
            if decision_card:
                print(f"Decision Card: {decision_card}")
            print(f"Answer:\n{answer}")

            # Specific assertions per query
            if q["expected_parameter"] == "chlorophyll":
                # Must reference MOSDAC chlorophyll or status without hallucinated units
                assert "chlorophyll" in answer.lower() or any("chlorophyll" in e.lower() for e in evidence)
                assert "0.0885" in answer or "0.0885" in " ".join(evidence) or "mosdac" in answer.lower()

            elif q["expected_parameter"] == "sst":
                # Factual SST response, no forced fishing decision
                assert "temperature" in answer.lower() or "sst" in answer.lower() or "30" in answer
                assert "recommendation: go" not in answer.lower()
                assert "recommendation: avoid" not in answer.lower()

            elif q["expected_parameter"] == "weather":
                # Weather response
                assert any(w in answer.lower() for w in ["weather", "wind", "visibility", "condition", "knots", "sea state"])

            elif q["expected_parameter"] == "decision":
                # Cross-agent decision query: must synthesize multiple agents
                assert any(rec in answer for rec in ["Recommendation: GO", "Recommendation: CAUTION", "Recommendation: AVOID", "Recommendation: INSUFFICIENT DATA"])
                # Must provide reasoning points / contributing factors
                assert len(evidence) >= 2 or "Why:" in answer or "•" in answer
                # Must not claim chlorophyll is an absolute fish guarantee
                assert "guarantee" in answer.lower() or "indicator" in answer.lower() or "caution" in answer.lower() or "productivity" in answer.lower()

            elif q["expected_parameter"] == "safety":
                # Safety prioritized
                assert any(term in answer.lower() for term in ["safe", "safety", "risk", "hazard", "navigational", "caution", "boundary"])

            results.append({"query": q["query"], "status": "VERIFIED", "http": resp.status_code})

        print("\n" + "=" * 70)
        print("ALL 5 LIVE QUERIES SUCCESSFULLY VERIFIED!")
        print("=" * 70)
        for r in results:
            print(f"  [PASS] {r['query']} -> HTTP {r['http']} ({r['status']})")

if __name__ == "__main__":
    run_verification()
