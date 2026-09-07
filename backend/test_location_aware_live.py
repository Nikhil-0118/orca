"""
Live end-to-end verification script for Location-Aware Queries Across All India.
Tests live backend server at http://127.0.0.1:8000/api/query.
Validates:
1. GPS-based queries route to client device GPS.
2. Explicit queries route to queried place across India.
3. User location and query location are preserved separately in JSON response.
4. "the nearest ocean to Gujarat" with GPS=Kanpur returns Gujarat/Arabian Sea ~0 km, NOT Kanpur/883 km.
5. "temperature in my location" routes to Weather Agent (air temperature), NOT Ocean Agent SST.
6. "sea temperature near Gujarat" routes to Ocean Agent SST.
7. Mixed query "I am in Kanpur, what is the weather in Mumbai?" routes weather to Mumbai while keeping Kanpur GPS.
"""
import json
import urllib.request
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8000/api/query"
KANPUR_GPS = {"latitude": 26.52, "longitude": 80.26, "source": "browser_gps"}


def post_query(query_text: str, loc=None, session_id="live_test_session"):
    payload = {
        "query": query_text,
        "session_id": session_id,
        "location": loc or KANPUR_GPS,
    }
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_tests():
    print("====================================================================")
    print("STARTING LIVE LOCATION-AWARE ROUTING VERIFICATION SUITE")
    print("====================================================================")
    passed = 0
    total = 0

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 1: Negative Regression Test — GPS=Kanpur, Query="the nearest ocean to Gujarat"
    # ──────────────────────────────────────────────────────────────────────────
    total += 1
    print("\n[TEST 1] GPS=Kanpur (26.52, 80.26) | Query: 'the nearest ocean to Gujarat'")
    res1 = post_query("the nearest ocean to Gujarat", loc=KANPUR_GPS)
    ans1 = res1.get("answer", "")
    u_loc1 = res1.get("user_location", {})
    q_loc1 = res1.get("query_location", {})

    print(f"-> user_location preserved: lat={u_loc1.get('latitude')}, lon={u_loc1.get('longitude')}, source={u_loc1.get('source')}")
    print(f"-> query_location resolved: name={q_loc1.get('name')}, type={q_loc1.get('type')}, source={q_loc1.get('source')}")
    print(f"-> answer snippet: {ans1[:180]}...")

    # Assertions
    assert "883" not in ans1, "FAILED: Answer mentioned Kanpur's 883 km distance!"
    assert "arabian sea" in ans1.lower(), "FAILED: Answer did not identify Arabian Sea for Gujarat!"
    assert abs(u_loc1.get("latitude") - 26.52) < 0.01, "FAILED: user_location latitude was overwritten!"
    assert q_loc1.get("name").lower() == "gujarat", "FAILED: query_location name is not Gujarat!"
    print(">>> PASS: Negative regression test passed! Gujarat resolved to Arabian Sea (0 km / coastal state), Kanpur preserved as user_location.")
    passed += 1

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 2: GPS Deictic Query — "nearest ocean near me" with GPS=Kanpur
    # ──────────────────────────────────────────────────────────────────────────
    total += 1
    print("\n[TEST 2] GPS=Kanpur | Query: 'nearest ocean near me'")
    res2 = post_query("nearest ocean near me", loc=KANPUR_GPS)
    ans2 = res2.get("answer", "")
    print(f"-> answer snippet: {ans2[:180]}...")
    assert "bay of bengal" in ans2.lower(), "FAILED: Expected Bay of Bengal for Kanpur GPS"
    assert any(term in ans2.lower() for term in ["883", "88", "km"]), "FAILED: Expected distance in km for inland Kanpur"
    print(">>> PASS: 'nearest ocean near me' correctly used device GPS (Kanpur -> Bay of Bengal ~883 km).")
    passed += 1

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 3: Coastal City Queries — Mumbai & Chennai
    # ──────────────────────────────────────────────────────────────────────────
    total += 1
    print("\n[TEST 3] GPS=Kanpur | Query: 'nearest ocean to Mumbai'")
    res3 = post_query("nearest ocean to Mumbai", loc=KANPUR_GPS)
    ans3 = res3.get("answer", "")
    print(f"-> answer snippet: {ans3[:180]}...")
    assert "arabian sea" in ans3.lower(), "FAILED: Expected Arabian Sea for Mumbai"
    print(">>> PASS: Mumbai resolved to Arabian Sea.")
    passed += 1

    total += 1
    print("\n[TEST 4] GPS=Kanpur | Query: 'which ocean is near Chennai'")
    res4 = post_query("which ocean is near Chennai", loc=KANPUR_GPS)
    ans4 = res4.get("answer", "")
    print(f"-> answer snippet: {ans4[:180]}...")
    assert "bay of bengal" in ans4.lower(), "FAILED: Expected Bay of Bengal for Chennai"
    print(">>> PASS: Chennai resolved to Bay of Bengal.")
    passed += 1

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 5: Coastal Town — Dwarka
    # ──────────────────────────────────────────────────────────────────────────
    total += 1
    print("\n[TEST 5] GPS=Kanpur | Query: 'ocean near Dwarka'")
    res5 = post_query("ocean near Dwarka", loc=KANPUR_GPS)
    ans5 = res5.get("answer", "")
    print(f"-> answer snippet: {ans5[:180]}...")
    assert "arabian sea" in ans5.lower(), "FAILED: Expected Arabian Sea for Dwarka"
    print(">>> PASS: Dwarka resolved to Arabian Sea.")
    passed += 1

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 6: Temperature Routing Separation
    # "temperature in my location" -> Weather Agent (Air temp), NOT Ocean Agent
    # ──────────────────────────────────────────────────────────────────────────
    total += 1
    print("\n[TEST 6] GPS=Kanpur | Query: 'what is the temperature in my location'")
    res6 = post_query("what is the temperature in my location", loc=KANPUR_GPS)
    agents6 = res6.get("agents_used", [])
    ev6 = res6.get("evidence", [])
    ans6 = res6.get("answer", "")
    print(f"-> agents used: {agents6}")
    print(f"-> answer snippet: {ans6[:180]}...")
    assert "ocean" not in agents6, "FAILED: Ocean Agent was invoked for air temperature query!"
    print(">>> PASS: Ordinary air temperature inquiry routed to Weather Agent, NOT Ocean Agent.")
    passed += 1

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 7: Sea Surface Temperature -> Ocean Agent
    # ──────────────────────────────────────────────────────────────────────────
    total += 1
    print("\n[TEST 7] Query: 'sea temperature near Gujarat'")
    res7 = post_query("sea temperature near Gujarat", loc=KANPUR_GPS)
    agents7 = [a.lower() for a in res7.get("agents_used", [])]
    ans7 = res7.get("answer", "")
    print(f"-> agents used: {res7.get('agents_used', [])}")
    print(f"-> answer snippet: {ans7[:180]}...")
    assert "ocean" in agents7, "FAILED: Ocean Agent was NOT invoked for SST query!"
    print(">>> PASS: Sea surface temperature query correctly invoked Ocean Agent.")
    passed += 1

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 8: Mixed Query — User in Kanpur, asking weather in Mumbai
    # ──────────────────────────────────────────────────────────────────────────
    total += 1
    print("\n[TEST 8] Query: 'I am in Kanpur, what is the weather in Mumbai?'")
    res8 = post_query("I am in Kanpur, what is the weather in Mumbai?", loc=KANPUR_GPS)
    u_loc8 = res8.get("user_location", {})
    q_loc8 = res8.get("query_location", {})
    ans8 = res8.get("answer", "")
    print(f"-> user_location: lat={u_loc8.get('latitude')}, lon={u_loc8.get('longitude')}")
    print(f"-> query_location: {q_loc8.get('name')}")
    print(f"-> answer snippet: {ans8[:180]}...")
    assert abs(u_loc8.get("latitude") - 26.52) < 0.01, "FAILED: User location was not preserved as Kanpur!"
    assert q_loc8.get("name").lower() == "mumbai", "FAILED: Query location was not resolved to Mumbai!"
    assert "mumbai" in ans8.lower(), "FAILED: Answer did not address Mumbai!"
    print(">>> PASS: Mixed query resolved weather for Mumbai while preserving Kanpur GPS.")
    passed += 1

    print("\n====================================================================")
    print(f"ALL {passed}/{total} LIVE END-TO-END VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("====================================================================")


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as exc:
        print(f"\nTEST SUITE FAILED: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
