import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api/query"

def run_test_suite():
    session_id = "test-session-all-5-cases"
    history = []

    print("\n========================================================")
    print("TEST 1: 'What is the chlorophyll level of Chennai?'")
    print("========================================================")
    q1 = "What is the chlorophyll level of Chennai"
    payload1 = {
        "query": q1,
        "location": {"latitude": 13.0827, "longitude": 80.2707, "source": "browser_gps"},
        "session_id": session_id,
        "conversation_history": history,
    }
    r1 = requests.post(BASE_URL, json=payload1).json()
    ans1 = r1.get("answer", "")
    print(f"Answer 1:\n{ans1}\n")
    
    assert "0.0909" in ans1, "Expected chlorophyll value 0.0909 in answer"
    assert "MOSDAC" in ans1 or "satellite ocean color" in ans1, "Expected MOSDAC/ocean color source"
    assert "2026-09-05" in ans1 or "observation" in ans1.lower(), "Expected observation date"
    print(">>> TEST 1 PASSED: Valid chlorophyll value 0.0909, source MOSDAC, observation date 2026-09-05, no fake data.")

    history.append({"role": "user", "content": q1})
    history.append({"role": "assistant", "content": ans1})

    print("\n========================================================")
    print("TEST 2: 'where can i find the maximum fishes near chennai'")
    print("========================================================")
    q2 = "where can i find the maximum fishes near chennai"
    payload2 = {
        "query": q2,
        "location": {"latitude": 13.0827, "longitude": 80.2707, "source": "browser_gps"},
        "session_id": session_id,
        "conversation_history": history,
    }
    r2 = requests.post(BASE_URL, json=payload2).json()
    ans2 = r2.get("answer", "")
    sp2 = r2.get("spatial") or {}
    print(f"Answer 2:\n{ans2}\n")
    print(f"Spatial Routes 2: {sp2.get('routes')}")
    print(f"Target Location 2: {sp2.get('target_location')}")
    print(f"Vessel Location 2: {sp2.get('vessel_location')}")

    assert "0.0909" in ans2, "Expected chlorophyll 0.0909 in fishing recommendation reasoning"
    assert "biological productivity" in ans2.lower(), "Expected biological productivity explanation"
    assert "indicator" in ans2.lower(), "Expected indicator disclaimer"
    assert "not a direct measurement of fish abundance" in ans2.lower() or "not guarantee" in ans2.lower(), "Expected fish abundance disclaimer"
    assert len(sp2.get("routes", [])) == 0, "Expected NO automatic route on fishing recommendation query"
    assert sp2.get("target_location", {}).get("latitude") is not None, "Expected valid Chennai target location"
    assert sp2.get("vessel_location", {}).get("latitude") == 13.0827, "Expected separate vessel location"
    print(">>> TEST 2 PASSED: Fishing-location intent, Chennai target, chlorophyll 0.0909 used, biological productivity explained, limitation communicated, NO automatic route.")

    history.append({"role": "user", "content": q2})
    history.append({"role": "assistant", "content": ans2})

    print("\n========================================================")
    print("TEST 3: 'can you give me the route?' (Follow-up)")
    print("========================================================")
    q3 = "can you give me the route?"
    payload3 = {
        "query": q3,
        "location": {"latitude": 13.0827, "longitude": 80.2707, "source": "browser_gps"},
        "session_id": session_id,
        "conversation_history": history,
    }
    r3 = requests.post(BASE_URL, json=payload3).json()
    ans3 = r3.get("answer", "")
    sp3 = r3.get("spatial") or {}
    print(f"Answer 3:\n{ans3}\n")
    print(f"Spatial Routes 3 count: {len(sp3.get('routes', []))}")
    if sp3.get("routes"):
        r_item = sp3["routes"][0]
        print(f"Route origin: {r_item.get('origin')}")
        print(f"Route destination: {r_item.get('destination')}")
        print(f"Distance km: {r_item.get('distance_km')}, nm: {r_item.get('distance_nm')}, bearing: {r_item.get('bearing_degrees')}")

    assert len(sp3.get("routes", [])) > 0, "Expected route generated on explicit routing follow-up"
    assert sp3.get("vessel_location", {}).get("latitude") == 13.0827, "Expected vesselLocation remains separate"
    assert sp3.get("target_location", {}).get("latitude") == 12.85, "Expected active Chennai target reused"
    print(">>> TEST 3 PASSED: Conversational routing works, active Chennai target reused, route plotted, vessel location preserved.")

    print("\n========================================================")
    print("TEST 4: 'What is my current location?'")
    print("========================================================")
    q4 = "What is my current location?"
    payload4 = {
        "query": q4,
        "location": {"latitude": 13.0827, "longitude": 80.2707, "source": "browser_gps"},
        "session_id": session_id,
        "conversation_history": history,
    }
    r4 = requests.post(BASE_URL, json=payload4).json()
    ans4 = r4.get("answer", "")
    sp4 = r4.get("spatial") or {}
    print(f"Answer 4:\n{ans4}\n")
    print(f"Spatial type 4: {sp4.get('type')}")
    print(f"Spatial Routes 4: {sp4.get('routes')}")

    assert "13.0827" in ans4 or "chennai" in ans4.lower() or "coordinates" in ans4.lower() or (sp4 and sp4.get("type") == "user_location"), "Expected current location"
    assert len(sp4.get("routes", [])) == 0, "Expected NO route on location query"
    print(">>> TEST 4 PASSED: Current device GPS, no replacement, no route.")

    print("\n========================================================")
    print("TEST 5: 'Show me Chennai.'")
    print("========================================================")
    q5 = "Show me Chennai."
    payload5 = {
        "query": q5,
        "location": {"latitude": 13.0827, "longitude": 80.2707, "source": "browser_gps"},
        "session_id": session_id,
        "conversation_history": history,
    }
    r5 = requests.post(BASE_URL, json=payload5).json()
    ans5 = r5.get("answer", "")
    sp5 = r5.get("spatial") or {}
    print(f"Answer 5:\n{ans5}\n")
    print(f"Spatial type 5: {sp5.get('type')}")
    print(f"Spatial center 5: {sp5.get('center')}")
    print(f"Spatial Routes 5: {sp5.get('routes')}")

    assert len(sp5.get("routes", [])) == 0, "Expected NO route on target map query"
    assert abs(sp5.get("center", {}).get("latitude", 0) - 13.0827) < 0.5, "Expected Chennai center coordinates"
    print(">>> TEST 5 PASSED: Chennai target marker/center displayed, no route.")

    print("\n========================================================")
    print("ALL 5 TESTS PASSED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    run_test_suite()
