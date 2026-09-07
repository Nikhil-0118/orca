import asyncio
import json
import httpx

API_URL = "http://127.0.0.1:8000/api/query"

async def test_live_suite():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Default vessel location (e.g. Kanpur GPS)
        vessel = {
            "latitude": 26.5207,
            "longitude": 80.2564,
            "source": "browser_gps",
            "label": "Kanpur, Uttar Pradesh",
            "geographic_type": "inland",
        }

        print("\n" + "="*70)
        print("ORCA DYNAMIC LOCATION & FISHING DESTINATION LIVE VERIFICATION")
        print("="*70)

        # 1. Best fishing spot near Mumbai
        print("\n--- Test 1: 'Best fishing spot near Mumbai' ---")
        payload = {"query": "Best fishing spot near Mumbai", "location": vessel, "session_id": "live_test"}
        res1 = await client.post(API_URL, json=payload)
        d1 = res1.json()
        sp1 = d1.get("spatial") or {}
        print(f"Status: {res1.status_code}")
        print(f"Target Place: {d1.get('location', {}).get('resolved_place')}")
        print(f"Spatial Enabled: {sp1.get('enabled')}, Type: {sp1.get('type')}")
        print(f"Target Location: {sp1.get('target_location')}")
        assert res1.status_code == 200, f"Error: {res1.text}"
        assert sp1.get("type") == "fishing_destination", f"Expected fishing_destination, got {sp1.get('type')}"
        assert abs(sp1.get("target_location", {}).get("latitude", 0) - 18.92) < 0.1

        # 2. Give the map (follow-up to Mumbai)
        print("\n--- Test 2: 'Give the map' (follow-up to Mumbai) ---")
        history_mumbai = [
            {"role": "user", "content": "Best fishing spot near Mumbai"},
            {"role": "assistant", "content": d1.get("answer", "")[:200]},
        ]
        payload = {"query": "Give the map", "location": vessel, "session_id": "live_test", "conversation_history": history_mumbai}
        res2 = await client.post(API_URL, json=payload)
        d2 = res2.json()
        sp2 = d2.get("spatial") or {}
        print(f"Status: {res2.status_code}")
        print(f"Target Place: {d2.get('location', {}).get('resolved_place')}")
        print(f"Spatial Enabled: {sp2.get('enabled')}, Type: {sp2.get('type')}")
        print(f"Target Location: {sp2.get('target_location')}")
        assert res2.status_code == 200
        assert sp2.get("type") == "fishing_destination"
        assert abs(sp2.get("target_location", {}).get("latitude", 0) - 18.92) < 0.1

        # 3. Best fishing spot near Chennai
        print("\n--- Test 3: 'Best fishing spot near Chennai' ---")
        payload = {"query": "Best fishing spot near Chennai", "location": vessel, "session_id": "live_test"}
        res3 = await client.post(API_URL, json=payload)
        d3 = res3.json()
        sp3 = d3.get("spatial") or {}
        print(f"Status: {res3.status_code}")
        print(f"Target Place: {d3.get('location', {}).get('resolved_place')}")
        print(f"Spatial Enabled: {sp3.get('enabled')}, Type: {sp3.get('type')}")
        print(f"Target Location: {sp3.get('target_location')}")
        assert res3.status_code == 200
        assert sp3.get("type") == "fishing_destination"
        assert abs(sp3.get("target_location", {}).get("latitude", 0) - 12.85) < 0.1

        # 4. Give the map (follow-up to Chennai)
        print("\n--- Test 4: 'Give the map' (follow-up to Chennai) ---")
        history_chennai = [
            {"role": "user", "content": "Best fishing spot near Chennai"},
            {"role": "assistant", "content": d3.get("answer", "")[:200]},
        ]
        payload = {"query": "Give the map", "location": vessel, "session_id": "live_test", "conversation_history": history_chennai}
        res4 = await client.post(API_URL, json=payload)
        d4 = res4.json()
        sp4 = d4.get("spatial") or {}
        print(f"Status: {res4.status_code}")
        print(f"Target Place: {d4.get('location', {}).get('resolved_place')}")
        print(f"Spatial Enabled: {sp4.get('enabled')}, Type: {sp4.get('type')}")
        print(f"Target Location: {sp4.get('target_location')}")
        assert res4.status_code == 200
        assert sp4.get("type") == "fishing_destination"
        assert abs(sp4.get("target_location", {}).get("latitude", 0) - 12.85) < 0.1

        # 5. Best fishing spot near Kochi
        print("\n--- Test 5: 'Best fishing spot near Kochi' ---")
        payload = {"query": "Best fishing spot near Kochi", "location": vessel, "session_id": "live_test"}
        res5 = await client.post(API_URL, json=payload)
        d5 = res5.json()
        sp5 = d5.get("spatial") or {}
        print(f"Status: {res5.status_code}")
        print(f"Target Place: {d5.get('location', {}).get('resolved_place')}")
        print(f"Spatial Enabled: {sp5.get('enabled')}, Type: {sp5.get('type')}")
        print(f"Target Location: {sp5.get('target_location')}")
        assert res5.status_code == 200
        assert sp5.get("type") == "fishing_destination"
        assert abs(sp5.get("target_location", {}).get("latitude", 0) - 9.93) < 0.1

        # 6. Give the map (follow-up to Kochi)
        print("\n--- Test 6: 'Give the map' (follow-up to Kochi) ---")
        history_kochi = [
            {"role": "user", "content": "Best fishing spot near Kochi"},
            {"role": "assistant", "content": d5.get("answer", "")[:200]},
        ]
        payload = {"query": "Give the map", "location": vessel, "session_id": "live_test", "conversation_history": history_kochi}
        res6 = await client.post(API_URL, json=payload)
        d6 = res6.json()
        sp6 = d6.get("spatial") or {}
        print(f"Status: {res6.status_code}")
        print(f"Target Place: {d6.get('location', {}).get('resolved_place')}")
        print(f"Spatial Enabled: {sp6.get('enabled')}, Type: {sp6.get('type')}")
        print(f"Target Location: {sp6.get('target_location')}")
        assert res6.status_code == 200
        assert sp6.get("type") == "fishing_destination"
        assert abs(sp6.get("target_location", {}).get("latitude", 0) - 9.93) < 0.1

        # 7. Best fishing spot near Goa
        print("\n--- Test 7: 'Best fishing spot near Goa' ---")
        payload = {"query": "Best fishing spot near Goa", "location": vessel, "session_id": "live_test"}
        res7 = await client.post(API_URL, json=payload)
        d7 = res7.json()
        sp7 = d7.get("spatial") or {}
        print(f"Status: {res7.status_code}")
        print(f"Target Place: {d7.get('location', {}).get('resolved_place')}")
        print(f"Spatial Enabled: {sp7.get('enabled')}, Type: {sp7.get('type')}")
        print(f"Target Location: {sp7.get('target_location')}")
        assert res7.status_code == 200
        assert sp7.get("type") == "fishing_destination"
        assert abs(sp7.get("target_location", {}).get("latitude", 0) - 15.48) < 0.3

        # 8. What is my current location?
        print("\n--- Test 8: 'What is my current location?' ---")
        payload = {"query": "What is my current location?", "location": vessel, "session_id": "live_test"}
        res8 = await client.post(API_URL, json=payload)
        d8 = res8.json()
        sp8 = d8.get("spatial") or {}
        print(f"Status: {res8.status_code}")
        print(f"Spatial Type: {sp8.get('type')}")
        print(f"Markers: {[m.get('marker_type') for m in sp8.get('markers', [])]}")
        assert res8.status_code == 200
        assert sp8.get("type") == "user_location"
        assert "fishing" not in [m.get("marker_type") for m in sp8.get("markers", [])]

        # 9. Show the safe zone near Chennai
        print("\n--- Test 9: 'Show the safe zone near Chennai' ---")
        payload = {"query": "Show the safe zone near Chennai", "location": vessel, "session_id": "live_test"}
        res9 = await client.post(API_URL, json=payload)
        d9 = res9.json()
        sp9 = d9.get("spatial") or {}
        print(f"Status: {res9.status_code}")
        print(f"Spatial Type: {sp9.get('type')}")
        print(f"Zones present: {len(sp9.get('zones', [])) > 0}")
        assert res9.status_code == 200
        assert sp9.get("type") == "boundary_safety"
        assert sp9.get("type") != "fishing_destination"

        print("\n" + "="*70)
        print("ALL 9 MANUAL VERIFICATION TESTS PASSED ACCURATELY AGAINST LIVE API!")
        print("="*70)

if __name__ == "__main__":
    asyncio.run(test_live_suite())
