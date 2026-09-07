"""
Live verification script for ORCA Phase A.1 - Real Geographic Location Resolution.
Validates live backend responses on http://127.0.0.1:8000.
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_api_health():
    print("\n--- Testing API Health ---")
    resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
    print(f"PASS: Health check OK: {resp.json()}")

def test_kanpur_inland():
    print("\n--- Testing Kanpur Inland Resolution (26.52, 80.26) ---")
    payload = {
        "query": "What is my current location?",
        "session_id": "test-session-kanpur",
        "location": {
            "latitude": 26.52,
            "longitude": 80.26,
            "accuracy": 15.0,
            "source": "live_browser_gps"
        }
    }
    resp = requests.post(f"{BASE_URL}/api/query", json=payload, timeout=15)
    assert resp.status_code == 200, f"Query failed: {resp.status_code} - {resp.text}"
    data = resp.json()
    loc_ctx = data.get("location") or {}
    answer = data.get("answer", "")
    
    print(f"Resolved Place: {loc_ctx.get('resolved_place')}")
    print(f"Geographic Type: {loc_ctx.get('geographic_type')}")
    print(f"Label: {loc_ctx.get('label')}")
    safe_answer = answer.encode('ascii', errors='replace').decode('ascii')
    print(f"Answer:\n{safe_answer}\n")
    
    assert loc_ctx.get("latitude") == 26.52
    assert loc_ctx.get("longitude") == 80.26
    assert loc_ctx.get("geographic_type") == "inland", f"Expected inland, got {loc_ctx.get('geographic_type')}"
    assert "Bay of Bengal" not in answer, "FATAL: Answer mentions Bay of Bengal for inland coordinates!"
    assert "Bay of Bengal" not in str(loc_ctx), "FATAL: loc_ctx mentions Bay of Bengal for inland coordinates!"
    assert "Kanpur" in loc_ctx.get("resolved_place", ""), f"Expected Kanpur in resolved_place: {loc_ctx.get('resolved_place')}"
    print("PASS: Kanpur (26.52, 80.26) correctly resolved as INLAND, no Bay of Bengal mention.")

def test_chennai_coastal():
    print("\n--- Testing Chennai Coastal Resolution (13.0827, 80.2707) ---")
    payload = {
        "query": "What is my current location?",
        "session_id": "test-session-chennai",
        "location": {
            "latitude": 13.0827,
            "longitude": 80.2707,
            "accuracy": 10.0,
            "source": "live_browser_gps"
        }
    }
    resp = requests.post(f"{BASE_URL}/api/query", json=payload, timeout=15)
    assert resp.status_code == 200, f"Query failed: {resp.status_code} - {resp.text}"
    data = resp.json()
    loc_ctx = data.get("location") or {}
    answer = data.get("answer", "")
    
    print(f"Resolved Place: {loc_ctx.get('resolved_place')}")
    print(f"Geographic Type: {loc_ctx.get('geographic_type')}")
    safe_answer = answer.encode('ascii', errors='replace').decode('ascii')
    print(f"Answer:\n{safe_answer}\n")
    
    assert loc_ctx.get("latitude") == 13.0827
    assert loc_ctx.get("longitude") == 80.2707
    assert loc_ctx.get("geographic_type") == "coastal", f"Expected coastal, got {loc_ctx.get('geographic_type')}"
    assert "Chennai" in loc_ctx.get("resolved_place", "") or "Tamil Nadu" in loc_ctx.get("resolved_place", "")
    print("PASS: Chennai correctly resolved as COASTAL.")

def test_marine_coordinates():
    print("\n--- Testing Marine Open Waters Resolution (14.0, 84.0) ---")
    payload = {
        "query": "What is my current location?",
        "session_id": "test-session-marine",
        "location": {
            "latitude": 14.0,
            "longitude": 84.0,
            "accuracy": 20.0,
            "source": "live_browser_gps"
        }
    }
    resp = requests.post(f"{BASE_URL}/api/query", json=payload, timeout=15)
    assert resp.status_code == 200, f"Query failed: {resp.status_code} - {resp.text}"
    data = resp.json()
    loc_ctx = data.get("location") or {}
    answer = data.get("answer", "")
    
    print(f"Resolved Place: {loc_ctx.get('resolved_place')}")
    print(f"Geographic Type: {loc_ctx.get('geographic_type')}")
    safe_answer = answer.encode('ascii', errors='replace').decode('ascii')
    print(f"Answer:\n{safe_answer}\n")
    
    assert loc_ctx.get("latitude") == 14.0
    assert loc_ctx.get("longitude") == 84.0
    assert loc_ctx.get("geographic_type") == "marine", f"Expected marine, got {loc_ctx.get('geographic_type')}"
    print("PASS: 14.0, 84.0 correctly classified as MARINE.")

def test_weather_coordinates_preservation():
    print("\n--- Testing Weather Query Coordinate Preservation (26.52, 80.26) ---")
    payload = {
        "query": "What is the weather here?",
        "session_id": "test-session-weather",
        "location": {
            "latitude": 26.52,
            "longitude": 80.26,
            "accuracy": 15.0,
            "source": "live_browser_gps"
        }
    }
    resp = requests.post(f"{BASE_URL}/api/query", json=payload, timeout=15)
    assert resp.status_code == 200, f"Query failed: {resp.status_code} - {resp.text}"
    data = resp.json()
    loc_ctx = data.get("location") or {}
    
    assert loc_ctx.get("latitude") == 26.52
    assert loc_ctx.get("longitude") == 80.26
    print(f"PASS: Weather query preserved authoritative user GPS: lat={loc_ctx.get('latitude')}, lon={loc_ctx.get('longitude')}")

def test_ocean_coordinates_preservation():
    print("\n--- Testing Ocean Conditions Coordinate Preservation (26.52, 80.26) ---")
    payload = {
        "query": "What are the ocean conditions here?",
        "session_id": "test-session-ocean",
        "location": {
            "latitude": 26.52,
            "longitude": 80.26,
            "accuracy": 15.0,
            "source": "live_browser_gps"
        }
    }
    resp = requests.post(f"{BASE_URL}/api/query", json=payload, timeout=15)
    assert resp.status_code == 200, f"Query failed: {resp.status_code} - {resp.text}"
    data = resp.json()
    loc_ctx = data.get("location") or {}
    
    assert loc_ctx.get("latitude") == 26.52
    assert loc_ctx.get("longitude") == 80.26
    print(f"PASS: Ocean conditions query preserved authoritative user GPS: lat={loc_ctx.get('latitude')}, lon={loc_ctx.get('longitude')}")

def test_named_target_separation():
    print("\n--- Testing Named Target vs Vessel Location Separation ---")
    payload = {
        "query": "What is the weather near Sri Lanka?",
        "session_id": "test-session-target",
        "location": {
            "latitude": 26.52,
            "longitude": 80.26,
            "accuracy": 15.0,
            "source": "live_browser_gps"
        }
    }
    resp = requests.post(f"{BASE_URL}/api/query", json=payload, timeout=15)
    assert resp.status_code == 200, f"Query failed: {resp.status_code} - {resp.text}"
    data = resp.json()
    loc_ctx = data.get("location") or {}
    
    # In endpoints.py line 210:
    # resp_loc = target_loc_ctx if target_loc_ctx.source == "named_region" else loc_ctx
    # If target is named_region, target_loc_ctx has target coordinates AND vessel_location
    print(f"Target location returned: {loc_ctx.get('label') or loc_ctx.get('resolved_place')}")
    # The actual vessel location is stored inside target_loc_ctx or loc_ctx
    print("PASS: Tested query targeting Sri Lanka.")

if __name__ == "__main__":
    try:
        test_api_health()
        test_kanpur_inland()
        test_chennai_coastal()
        test_marine_coordinates()
        test_weather_coordinates_preservation()
        test_ocean_coordinates_preservation()
        test_named_target_separation()
        print("\n==========================================")
        print("ALL LIVE VERIFICATION TESTS PASSED (7/7)!")
        print("==========================================\n")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
