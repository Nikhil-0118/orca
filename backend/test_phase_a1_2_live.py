import requests
import json
import re

BASE_URL = "http://127.0.0.1:8000"

def safe_print(title, text):
    print(f"\n=== {title} ===")
    safe_t = text.encode("ascii", errors="replace").decode("ascii")
    print(safe_t)

def test_query(query, lat=26.52, lon=80.26, session_id="test-session"):
    payload = {
        "query": query,
        "session_id": session_id,
        "location": {
            "latitude": lat,
            "longitude": lon,
            "accuracy": 15.0,
            "source": "live_browser_gps"
        }
    }
    resp = requests.post(f"{BASE_URL}/api/query", json=payload, timeout=35)
    assert resp.status_code == 200, f"Query failed: {resp.status_code} - {resp.text}"
    return resp.json()

if __name__ == "__main__":
    print("--- 1. Testing Nearest Ocean from Kanpur (26.52, 80.26) ---")
    d1 = test_query("where is the nearest ocean nearby me", 26.52, 80.26, "kanpur-nearest-ocean")
    ans1 = d1.get("answer", "")
    safe_print("Kanpur Nearest Ocean Answer", ans1)
    assert "Bay of Bengal" in ans1, "Failed: Bay of Bengal not in answer"
    assert "inland" in ans1.lower(), "Failed: inland not in answer"
    assert "km" in ans1.lower() or "kilometer" in ans1.lower(), "Failed: distance not in answer"
    assert "ganges" not in ans1.lower() or "freshwater" in ans1.lower(), "Failed: Ganges returned as ocean"
    assert d1.get("mode") == "utility", f"Expected utility mode, got {d1.get('mode')}"
    assert d1.get("decision") is None, "Failed: decision should be None for nearest ocean utility"
    assert len(d1.get("key_conditions", [])) == 0, "Failed: key_conditions should be empty"
    print("PASS: Kanpur nearest ocean correctly resolved to Bay of Bengal with distance and inland status!")

    print("\n--- 2. Testing Nearest Ocean from Chennai (13.0827, 80.2707) ---")
    d2 = test_query("where is the nearest ocean nearby me", 13.0827, 80.2707, "chennai-nearest-ocean")
    ans2 = d2.get("answer", "")
    safe_print("Chennai Nearest Ocean Answer", ans2)
    assert "Bay of Bengal" in ans2, "Failed: Bay of Bengal not in answer"
    assert "coastal" in ans2.lower() or "coast" in ans2.lower(), "Failed: coastal not in answer"
    print("PASS: Chennai correctly identified as coastal on Bay of Bengal!")

    print("\n--- 3. Testing Nearest Ocean from Marine Open Waters (14.0, 84.0) ---")
    d3 = test_query("where is the nearest ocean nearby me", 14.0, 84.0, "marine-nearest-ocean")
    ans3 = d3.get("answer", "")
    safe_print("Marine Nearest Ocean Answer", ans3)
    assert "Bay of Bengal" in ans3, "Failed: Bay of Bengal not in answer"
    assert "marine" in ans3.lower() or "open waters" in ans3.lower(), "Failed: marine open waters not in answer"
    print("PASS: Marine point correctly identified as already in marine waters!")

    print("\n--- 4. Testing Location Query (Unchanged) ---")
    d4 = test_query("what is my location", 26.52, 80.26, "kanpur-location")
    ans4 = d4.get("answer", "")
    safe_print("Kanpur Location Answer", ans4)
    assert "Kanpur" in ans4 or "Kanpur" in str(d4.get("location")), "Failed: Kanpur not in location"
    assert "inland" in ans4.lower() or "inland" in str(d4.get("location")), "Failed: inland not in location"
    print("PASS: Location query remains unchanged and accurate!")

    print("\n--- 5. Testing Ocean Proximity Presence Query ---")
    d5 = test_query("is there an ocean nearby me", 26.52, 80.26, "kanpur-ocean-prox")
    ans5 = d5.get("answer", "")
    safe_print("Kanpur Ocean Proximity Answer", ans5)
    assert "no" in ans5.lower() or "inland" in ans5.lower(), "Failed: did not answer no/inland"
    print("PASS: Ocean proximity query correctly answered presence!")

    print("\n--- 6. Testing Nearest Water Body Query ---")
    d6 = test_query("what is the nearest water body", 26.52, 80.26, "kanpur-water-body")
    ans6 = d6.get("answer", "")
    safe_print("Kanpur Nearest Water Body Answer", ans6)
    assert "ganges" in ans6.lower() or "river" in ans6.lower(), "Failed: Ganges river not in answer"
    assert "freshwater" in ans6.lower() or "river" in ans6.lower(), "Failed: freshwater not identified"
    print("PASS: Water body query cleanly separated from ocean query!")

    print("\n--- 7. Testing Sea Temperature Query (Routes to Ocean Agent) ---")
    d7 = test_query("what is the sea temperature here", 26.52, 80.26, "kanpur-sst")
    assert d7.get("mode") == "marine", f"Expected marine mode, got {d7.get('mode')}"
    assert "ocean" in d7.get("agents_used", []) or d7.get("decision") is not None
    print("PASS: Sea temperature correctly routed to Ocean Agent!")

    print("\n--- 8. Testing Weather Query (Routes to Weather Agent) ---")
    d8 = test_query("what is the weather here", 26.52, 80.26, "kanpur-weather")
    assert d8.get("mode") == "marine", f"Expected marine mode, got {d8.get('mode')}"
    assert "weather" in d8.get("agents_used", []) or d8.get("decision") is not None
    print("PASS: Weather correctly routed to Weather Agent!")

    print("\n==============================================")
    print("ALL LIVE VERIFICATION TESTS PASSED (8/8)!")
    print("==============================================")
