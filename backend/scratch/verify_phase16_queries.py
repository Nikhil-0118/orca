"""
Real Integration Verification Script for Phase 16: Cross-Agent Data Freshness & Source Reliability.
Executes the 4 required real queries against the ORCA engine:
1. What is the current chlorophyll concentration near Chennai?
2. What is the SST near Chennai?
3. What is the weather near Chennai?
4. Can I go fishing near Chennai today?
"""
import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

QUERIES = [
    ("Query 1 (Chlorophyll)", "What is the current chlorophyll concentration near Chennai?"),
    ("Query 2 (SST)", "What is the SST near Chennai?"),
    ("Query 3 (Weather)", "What is the weather near Chennai?"),
    ("Query 4 (Cross-agent Fishing)", "Can I go fishing near Chennai today?"),
]

def run_queries():
    print("=" * 80)
    print("ORCA PHASE 16 REAL INTEGRATION VERIFICATION")
    print("=" * 80)

    for label, query in QUERIES:
        print(f"\n>>> Executing {label}: '{query}'")
        resp = client.post("/api/query", json={"query": query, "session_id": "phase16-verify"})
        assert resp.status_code == 200, f"Failed with {resp.status_code}: {resp.text}"
        data = resp.json()

        print(f"HTTP Status: {resp.status_code}")
        print(f"Risk Level: {data.get('risk_level')}")
        print(f"Confidence: {data.get('confidence')}")

        eo = data.get("eo_result")
        if eo:
            print(f"  [EO Result] Source: {eo.get('source')}, Dataset: {eo.get('dataset')}, "
                  f"Value: {eo.get('value')} {eo.get('unit')}, Date: {eo.get('observation_date')}, "
                  f"Freshness: {eo.get('freshness')}, Type: {eo.get('data_source_type')}")

        ocean = data.get("ocean_result")
        if ocean:
            print(f"  [Ocean Result] Source: {ocean.get('source')}, Status: {ocean.get('status')}, "
                  f"Data Time: {ocean.get('data_time')}, Freshness: {ocean.get('freshness')}, "
                  f"Type: {ocean.get('data_source_type')}")
            if "sea_surface_temperature" in ocean:
                print(f"    SST: {ocean['sea_surface_temperature']}")

        weather = data.get("weather_result")
        if weather:
            print(f"  [Weather Result] Source: {weather.get('source')}, Status: {weather.get('status')}, "
                  f"Type: {weather.get('data_source_type')}, Freshness: {weather.get('freshness')}")
            if "wind" in weather:
                print(f"    Wind: {weather['wind']}")

        analysis = data.get("marine_analysis")
        if analysis:
            print(f"  [Marine Analysis] Decision: {analysis.get('decision', {}).get('recommendation')}, "
                  f"Conflict Detected: {analysis.get('conflict_detected')}, "
                  f"Overall Reliability: {analysis.get('data_quality', {}).get('overall_reliability')}")
            conflicts = analysis.get("conflicts", [])
            if conflicts:
                print(f"    Conflicts: {conflicts}")

        print(f"\n  Final Answer:\n  {data.get('answer')}\n")
        print("-" * 80)

if __name__ == "__main__":
    run_queries()
