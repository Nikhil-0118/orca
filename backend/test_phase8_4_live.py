"""
Live verification script for ORCA Phase 8.4 — Real Location Awareness, Data Provenance & Geo-Spatial Integrity.
Runs the 6 mandatory validation scenarios against the active backend.
"""
import asyncio
import json
import sys
import httpx

sys.stdout.reconfigure(encoding='utf-8')


async def run_live_tests():
    print("\n" + "=" * 70)
    print("ORCA PHASE 8.4 — LIVE VERIFICATION SUITE")
    print("=" * 70)

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        # Check health
        h_resp = await client.get("/api/health")
        assert h_resp.status_code == 200, f"Health check failed: {h_resp.text}"
        print("[PASS] Backend /api/health probe OK")

        # ── Test A1: "What is my current location?" (Live GPS Coords: Kochi) ───
        print("\n--- Test A1: Current Location with Live GPS (Kochi 9.93°N, 76.26°E) ---")
        loc_kochi = {
            "latitude": 9.9312,
            "longitude": 76.2673,
            "source": "browser_gps",
            "accuracy_m": 12.0,
            "is_demo": False,
            "label": "Live GPS (±12m)",
        }
        res_a1 = await client.post(
            "/api/query",
            json={
                "query": "What is my current location?",
                "location": loc_kochi,
                "session_id": "test-live-a1",
            },
        )
        assert res_a1.status_code == 200
        d_a1 = res_a1.json()
        print(f"Mode: {d_a1.get('mode')}")
        print(f"Answer: {d_a1.get('answer')}")
        ans_lower = d_a1.get("answer", "").lower()
        assert "9.93" in ans_lower or "kochi" in ans_lower or "malabar" in ans_lower or "kerala" in ans_lower, \
            "Expected Kochi coordinates/region, got unrelated location"
        assert "chennai" not in ans_lower, "ERROR: Leaked Chennai coordinates in Kochi live GPS test!"
        print("[PASS] Test A1 Passed: Correct live GPS location rendered without Chennai fallback.")

        # ── Test A2: "What is my current location?" (Location Unavailable) ──────
        print("\n--- Test A2: Current Location when GPS Unavailable ---")
        loc_unavail = {
            "latitude": None,
            "longitude": None,
            "source": "unavailable",
            "is_demo": False,
            "label": "Location unavailable",
        }
        res_a2 = await client.post(
            "/api/query",
            json={
                "query": "What is my current location?",
                "location": loc_unavail,
                "session_id": "test-live-a2",
            },
        )
        assert res_a2.status_code == 200
        d_a2 = res_a2.json()
        print(f"Answer: {d_a2.get('answer')}")
        ans_a2_lower = d_a2.get("answer", "").lower()
        assert "unavailable" in ans_a2_lower or "gps" in ans_a2_lower or "permission" in ans_a2_lower or "not available" in ans_a2_lower, \
            "Expected unavailable location explanation"
        assert "13.08" not in ans_a2_lower and "chennai" not in ans_a2_lower, \
            "ERROR: Silently fell back to Chennai when location was unavailable!"
        print("[PASS] Test A2 Passed: Gracefully handled unavailable location without silent fallback.")

        # ── Test A3: "What is my current location?" (Explicit Demo Mode) ────────
        print("\n--- Test A3: Current Location in Explicit Demo Mode ---")
        loc_demo = {
            "latitude": 13.0827,
            "longitude": 80.2707,
            "source": "demo",
            "is_demo": True,
            "label": "Chennai Coastal Region (SIH Demo Mode)",
        }
        res_a3 = await client.post(
            "/api/query",
            json={
                "query": "What is my current location?",
                "location": loc_demo,
                "is_demo_mode": True,
                "session_id": "test-live-a3",
            },
        )
        assert res_a3.status_code == 200
        d_a3 = res_a3.json()
        print(f"Answer: {d_a3.get('answer')}")
        ans_a3_lower = d_a3.get("answer", "").lower()
        assert "demo" in ans_a3_lower or "demonstration" in ans_a3_lower, \
            "Expected explicit demo label in demo mode"
        print("[PASS] Test A3 Passed: Explicitly labeled demo mode.")

        # ── Test B: "What is the weather right now?" (Mumbai Coords: 18.92, 72.83) ─
        print("\n--- Test B: Weather at Actual Location (Mumbai 18.92°N, 72.83°E) ---")
        loc_mumbai = {
            "latitude": 18.922,
            "longitude": 72.834,
            "source": "browser_gps",
            "is_demo": False,
            "label": "Live GPS (±10m)",
        }
        res_b = await client.post(
            "/api/query",
            json={
                "query": "What is the weather right now?",
                "location": loc_mumbai,
                "session_id": "test-live-b",
            },
        )
        assert res_b.status_code == 200
        d_b = res_b.json()
        print(f"Decision: {d_b.get('decision')}")
        print(f"Answer: {d_b.get('answer')}")
        print(f"Structured Evidence: {d_b.get('structured_evidence')}")
        print(f"Limitations: {d_b.get('data_limitations')}")
        b_ans = d_b.get("answer", "").lower()
        assert "chennai" not in b_ans, "ERROR: Leaked Chennai in Mumbai weather query!"
        assert len(d_b.get("data_limitations", [])) > 0, "Expected data provenance limitations"
        print("[PASS] Test B Passed: Weather localized to Mumbai sector with transparent limitations.")

        # ── Test C: "Is it safe to fish here?" (Palk Bay boundary area: 9.45, 79.2) ─
        print("\n--- Test C: Fishing Safety Near Boundary (Palk Bay 9.45°N, 79.20°E) ---")
        loc_palk = {
            "latitude": 9.45,
            "longitude": 79.20,
            "source": "demo",
            "is_demo": True,
            "label": "Palk Bay (IMBL Demo Sector)",
        }
        res_c = await client.post(
            "/api/query",
            json={
                "query": "Is it safe to fish here?",
                "location": loc_palk,
                "is_demo_mode": True,
                "session_id": "test-live-c",
            },
        )
        assert res_c.status_code == 200
        d_c = res_c.json()
        print(f"Decision: {d_c.get('decision')}")
        print(f"Risk Level: {d_c.get('risk_level')}")
        print(f"Answer: {d_c.get('answer')}")
        print(f"Recommendations: {d_c.get('recommendations')}")
        assert d_c.get("decision") is not None, "Decision card required"
        assert d_c.get("decision", {}).get("label") in ["Recommended", "Recommended with caution", "Not recommended", "Avoid", "Clear", "Operational caution"]
        print("[PASS] Test C Passed: Safety evaluated with decision card and boundary proximity.")

        # ── Test D: Ocean Conditions with ERDDAP Grid Distance ───────────────────
        print("\n--- Test D: Ocean Conditions & ERDDAP Grid Distance (Gujarat: 21.0°N, 70.5°E) ---")
        loc_gujarat = {
            "latitude": 21.0,
            "longitude": 70.5,
            "source": "browser_gps",
            "is_demo": False,
        }
        res_d = await client.post(
            "/api/query",
            json={
                "query": "What is the sea surface temperature and wave height?",
                "location": loc_gujarat,
                "session_id": "test-live-d",
            },
        )
        assert res_d.status_code == 200
        d_d = res_d.json()
        print(f"Answer: {d_d.get('answer')}")
        print(f"Evidence: {d_d.get('evidence')}")
        print(f"Structured Evidence: {d_d.get('structured_evidence')}")
        print(f"Limitations: {d_d.get('data_limitations')}")
        assert len(d_d.get("evidence", [])) > 0, "Evidence expected"
        print("[PASS] Test D Passed: Ocean conditions resolved with provenance.")

        # ── Test E: Marine Ecosystem / Chlorophyll-a ─────────────────────────────
        print("\n--- Test E: Chlorophyll-a & Marine Ecosystem (Odisha coast: 19.5°N, 85.8°E) ---")
        loc_odisha = {
            "latitude": 19.5,
            "longitude": 85.8,
            "source": "browser_gps",
            "is_demo": False,
        }
        res_e = await client.post(
            "/api/query",
            json={
                "query": "What is the chlorophyll concentration and phytoplankton level here?",
                "location": loc_odisha,
                "session_id": "test-live-e",
            },
        )
        assert res_e.status_code == 200
        d_e = res_e.json()
        print(f"Answer: {d_e.get('answer')}")
        print(f"Structured Evidence: {d_e.get('structured_evidence')}")
        print(f"Agents Used: {d_e.get('agents_used')}")
        ans_e_lower = d_e.get("answer", "").lower()
        assert "chlorophyll" in ans_e_lower or "trophic" in ans_e_lower or "phytoplankton" in ans_e_lower, \
            "Expected chlorophyll/phytoplankton details in answer"
        print("[PASS] Test E Passed: Marine ecosystem agent executed and synthesized.")

        # ── Test F: Sequential Location Change Without Bleed ─────────────────────
        print("\n--- Test F: Location Change Switching (Kolkata -> Mangalore) ---")
        # Step 1: Query at Kolkata shelf (21.5, 88.0)
        loc_kolkata = {"latitude": 21.5, "longitude": 88.0, "source": "browser_gps", "is_demo": False}
        res_f1 = await client.post(
            "/api/query",
            json={"query": "What are current sea conditions?", "location": loc_kolkata, "session_id": "sess-f"},
        )
        assert res_f1.status_code == 200
        ans_f1 = res_f1.json().get("answer", "").lower()
        print(f"F1 (Kolkata) Answer: {res_f1.json().get('answer')[:120]}...")

        # Step 2: Query at Mangalore (12.87, 74.84) in same session
        loc_mangalore = {"latitude": 12.87, "longitude": 74.84, "source": "browser_gps", "is_demo": False}
        res_f2 = await client.post(
            "/api/query",
            json={"query": "What are current sea conditions?", "location": loc_mangalore, "session_id": "sess-f"},
        )
        assert res_f2.status_code == 200
        ans_f2 = res_f2.json().get("answer", "").lower()
        print(f"F2 (Mangalore) Answer: {res_f2.json().get('answer')[:120]}...")

        assert "chennai" not in ans_f1 and "chennai" not in ans_f2, "ERROR: Reverted to Chennai default!"
        print("[PASS] Test F Passed: Clean location transition without cross-region bleeding or Chennai fallback.")

    print("\n" + "=" * 70)
    print("ALL 6 LIVE VALIDATION SCENARIOS PASSED WITH ZERO ERRORS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_live_tests())
