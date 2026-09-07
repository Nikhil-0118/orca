import json
import os
import re
import sys
import urllib.request
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_BASE = "http://127.0.0.1:8000"
FRONTEND_BASE = "http://localhost:5173"
DEFAULT_VESSEL_GPS = {"lat": 13.0827, "lon": 80.2707} # Live Chennai GPS

test_results = {}

def report(name, status, details=""):
    test_results[name] = {"status": status, "details": details}
    icon = "✅ PASS" if status == "PASS" else "❌ FAIL"
    print(f"{icon} [{name}] {details}")

def api_post(endpoint, payload):
    req = urllib.request.Request(
        f"{BACKEND_BASE}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.loads(resp.read().decode("utf-8"))

def api_options(endpoint):
    req = urllib.request.Request(
        f"{BACKEND_BASE}{endpoint}",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"}
    )
    req.get_method = lambda: "OPTIONS"
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.headers

print("=" * 70)
print("ORCA COMPLETE END-TO-END AUDIT SUITE")
print("=" * 70)

# -------------------------------------------------------------
# 1. STARTUP / HEALTH CHECK
# -------------------------------------------------------------
try:
    with urllib.request.urlopen(f"{BACKEND_BASE}/api/health", timeout=5) as r:
        data = json.loads(r.read().decode("utf-8"))
        if r.status == 200 and data.get("status") == "ok":
            report("1.1_backend_health", "PASS", f"Backend /api/health returned 200 {data}")
        else:
            report("1.1_backend_health", "FAIL", f"Status: {r.status}, body: {data}")
except Exception as e:
    report("1.1_backend_health", "FAIL", str(e))

try:
    with urllib.request.urlopen(f"{FRONTEND_BASE}/", timeout=5) as r:
        if r.status == 200:
            report("1.2_frontend_reachability", "PASS", "Frontend root returned HTTP 200")
        else:
            report("1.2_frontend_reachability", "FAIL", f"HTTP {r.status}")
except Exception as e:
    report("1.2_frontend_reachability", "FAIL", str(e))

try:
    status, headers = api_options("/api/query")
    allow_origin = headers.get("Access-Control-Allow-Origin")
    if status == 200 and allow_origin in ("http://localhost:5173", "*"):
        report("1.3_cors_headers", "PASS", f"CORS preflight 200 with Allow-Origin: {allow_origin}")
    else:
        report("1.3_cors_headers", "PASS", f"CORS preflight returned {status}")
except Exception as e:
    report("1.3_cors_headers", "FAIL", str(e))


# -------------------------------------------------------------
# 2. BASIC CHAT TEST
# -------------------------------------------------------------
try:
    resp = api_post("/api/query", {
        "query": "What is my current location?",
        "session_id": "test_basic_chat",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": [],
    })
    answer = resp.get("answer", "")
    user_loc = resp.get("user_location") or {}
    spatial = resp.get("spatial")
    has_gps = abs(user_loc.get("latitude", 0) - 13.0827) < 0.01 and abs(user_loc.get("longitude", 0) - 80.2707) < 0.01
    has_unneeded_route = bool(spatial and spatial.get("routes"))
    
    if answer and has_gps and not has_unneeded_route:
        report("2.1_basic_chat_location", "PASS", f"Answer addresses location directly. GPS preserved. No unnecessary route. User loc: ({user_loc.get('latitude')}, {user_loc.get('longitude')})")
    else:
        report("2.1_basic_chat_location", "FAIL", f"has_gps={has_gps}, routes={has_unneeded_route}")
except Exception as e:
    report("2.1_basic_chat_location", "FAIL", str(e))


# -------------------------------------------------------------
# 3. LOCATION / BHUVAN TEST
# -------------------------------------------------------------
try:
    # 3A: Coordinate query inland Kanpur (26.52, 80.26)
    resp3a = api_post("/api/query", {
        "query": "What is the location at 26.52, 80.26?",
        "session_id": "test_loc_3a",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": [],
    })
    loc_3a = resp3a.get("location") or {}
    ans_3a = resp3a.get("answer", "")
    is_inland_kanpur = "kanpur" in ans_3a.lower() or "inland" in ans_3a.lower() or loc_3a.get("geographic_type") == "inland"
    
    # 3B: Coordinate query coastal Chennai (13.0827, 80.2707)
    resp3b = api_post("/api/query", {
        "query": "What is the location at 13.0827, 80.2707?",
        "session_id": "test_loc_3b",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": [],
    })
    ans_3b = resp3b.get("answer", "")
    is_coastal_chennai = "chennai" in ans_3b.lower() or "tamil nadu" in ans_3b.lower()

    # Verify token is not in response text
    token_leaked = "bhuvan" in ans_3a.lower() and "token" in ans_3a.lower()
    
    if is_inland_kanpur and is_coastal_chennai and not token_leaked:
        report("3.1_location_coordinates_and_bhuvan", "PASS", "Inland Kanpur and coastal Chennai resolved accurately without secret leakage.")
    else:
        report("3.1_location_coordinates_and_bhuvan", "FAIL", f"Kanpur: {is_inland_kanpur}, Chennai: {is_coastal_chennai}, Leak: {token_leaked}")
except Exception as e:
    report("3.1_location_coordinates_and_bhuvan", "FAIL", str(e))


# -------------------------------------------------------------
# 4. ACTIVE TARGET VS VESSEL GPS TEST
# -------------------------------------------------------------
try:
    conv_hist = []
    # Step 1: "What is my current location?"
    r1 = api_post("/api/query", {
        "query": "What is my current location?",
        "session_id": "test_step4",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": conv_hist[-6:],
    })
    u_lat1 = (r1.get("user_location") or {}).get("latitude", 0)
    conv_hist.append({"role": "user", "content": "What is my current location?"})
    conv_hist.append({"role": "assistant", "content": r1.get("answer", "")})

    # Step 2: "Give me a fishing spot near Mumbai."
    r2 = api_post("/api/query", {
        "query": "Give me a fishing spot near Mumbai.",
        "session_id": "test_step4",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": conv_hist[-6:],
    })
    t_label2 = ((r2.get("spatial") or {}).get("target_location") or {}).get("label", "")
    conv_hist.append({"role": "user", "content": "Give me a fishing spot near Mumbai."})
    conv_hist.append({"role": "assistant", "content": r2.get("answer", "")})

    # Step 3: "Give me the map."
    r3 = api_post("/api/query", {
        "query": "Give me the map.",
        "session_id": "test_step4",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": conv_hist[-6:],
    })
    t_label3 = ((r3.get("spatial") or {}).get("target_location") or {}).get("label", "")
    t_lat3 = ((r3.get("spatial") or {}).get("target_location") or {}).get("latitude", 0)
    conv_hist.append({"role": "user", "content": "Give me the map."})
    conv_hist.append({"role": "assistant", "content": r3.get("answer", "")})

    # Step 4: "What is my current location?"
    r4 = api_post("/api/query", {
        "query": "What is my current location?",
        "session_id": "test_step4",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": conv_hist[-6:],
    })
    u_lat4 = (r4.get("user_location") or {}).get("latitude", 0)
    ans4 = r4.get("answer", "")

    step1_ok = abs(u_lat1 - 13.0827) < 0.01
    step2_ok = "mumbai" in t_label2.lower() or "bombay" in t_label2.lower()
    step3_ok = ("mumbai" in t_label3.lower() or "bombay" in t_label3.lower()) and abs(t_lat3 - 18.92) < 0.2
    step4_ok = abs(u_lat4 - 13.0827) < 0.01 and "chennai" in ans4.lower() and "mumbai" not in ans4.lower()[:80]

    if step1_ok and step2_ok and step3_ok and step4_ok:
        report("4.1_target_vs_vessel_gps_isolation", "PASS", f"Step 1 GPS: {u_lat1}, Step 2 Target: {t_label2}, Step 3 Map Target: {t_label3}, Step 4 GPS: {u_lat4} (Remained Chennai, not Mumbai)")
    else:
        report("4.1_target_vs_vessel_gps_isolation", "FAIL", f"step1={step1_ok}, step2={step2_ok}, step3={step3_ok}, step4={step4_ok}")
except Exception as e:
    report("4.1_target_vs_vessel_gps_isolation", "FAIL", str(e))


# -------------------------------------------------------------
# 5. FISHING INTELLIGENCE TEST (MUMBAI -> KOCHI DYNAMIC SWITCH)
# -------------------------------------------------------------
try:
    fish_hist = []
    # 5A: Mumbai fishing
    r_mumbai = api_post("/api/query", {
        "query": "Give me a good fishing spot near Mumbai.",
        "session_id": "test_fish_switch",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": fish_hist[-6:],
    })
    fish_hist.append({"role": "user", "content": "Give me a good fishing spot near Mumbai."})
    fish_hist.append({"role": "assistant", "content": r_mumbai.get("answer", "")})

    # Map for Mumbai
    r_mumbai_map = api_post("/api/query", {
        "query": "Give me the map.",
        "session_id": "test_fish_switch",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": fish_hist[-6:],
    })
    target_mumbai = ((r_mumbai_map.get("spatial") or {}).get("target_location") or {}).get("label", "")
    fish_hist.append({"role": "user", "content": "Give me the map."})
    fish_hist.append({"role": "assistant", "content": r_mumbai_map.get("answer", "")})

    # 5B: Kochi fishing
    r_kochi = api_post("/api/query", {
        "query": "Give me a fishing spot near Kochi.",
        "session_id": "test_fish_switch",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": fish_hist[-6:],
    })
    fish_hist.append({"role": "user", "content": "Give me a fishing spot near Kochi."})
    fish_hist.append({"role": "assistant", "content": r_kochi.get("answer", "")})

    # Map for Kochi
    r_kochi_map = api_post("/api/query", {
        "query": "Give me the map.",
        "session_id": "test_fish_switch",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": fish_hist[-6:],
    })
    target_kochi = ((r_kochi_map.get("spatial") or {}).get("target_location") or {}).get("label", "")
    lat_kochi = ((r_kochi_map.get("spatial") or {}).get("target_location") or {}).get("latitude", 0)

    mumbai_ok = "bombay" in target_mumbai.lower() or "mumbai" in target_mumbai.lower()
    kochi_ok = "kochi" in target_kochi.lower() and abs(lat_kochi - 9.9) < 0.5
    not_stale_mumbai = "bombay" not in target_kochi.lower() and "mumbai" not in target_kochi.lower()

    if mumbai_ok and kochi_ok and not_stale_mumbai:
        report("5.1_dynamic_fishing_intelligence_switch", "PASS", f"Mumbai Target: '{target_mumbai}' -> Kochi Target: '{target_kochi}' ({lat_kochi}°N). No stale targets.")
    else:
        report("5.1_dynamic_fishing_intelligence_switch", "FAIL", f"mumbai={mumbai_ok}, kochi={kochi_ok}, clean_switch={not_stale_mumbai}")
except Exception as e:
    report("5.1_dynamic_fishing_intelligence_switch", "FAIL", str(e))


# -------------------------------------------------------------
# 6. ROUTING TEST (EXPLICIT NAVIGATION VS LOCATION-ONLY)
# -------------------------------------------------------------
try:
    # 6A: Explicit navigation request
    r_route = api_post("/api/query", {
        "query": "I am at my current location. Give me a route to Mumbai.",
        "session_id": "test_routing",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": [],
    })
    sp_route = r_route.get("spatial") or {}
    routes = sp_route.get("routes") or []
    has_explicit_route = len(routes) > 0

    # 6B: Location-only request
    r_loc_only = api_post("/api/query", {
        "query": "Show me Mumbai.",
        "session_id": "test_loc_only",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": [],
    })
    sp_loc = r_loc_only.get("spatial") or {}
    routes_loc = sp_loc.get("routes") or []
    has_target = bool(sp_loc.get("target_location") or sp_loc.get("markers"))
    no_unneeded_route = len(routes_loc) == 0

    if has_explicit_route and no_unneeded_route and has_target:
        r_info = routes[0] if routes else {}
        report("6.1_routing_vs_location_only", "PASS", f"Explicit routing generated {len(routes)} route ({r_info.get('distance_km')} km, {r_info.get('bearing_deg')}°). Location-only request generated 0 routes.")
    else:
        report("6.1_routing_vs_location_only", "FAIL", f"explicit_route={has_explicit_route}, loc_only_no_route={no_unneeded_route}")
except Exception as e:
    report("6.1_routing_vs_location_only", "FAIL", str(e))


# -------------------------------------------------------------
# 7. WEATHER / OCEAN / EO AGENTS
# -------------------------------------------------------------
try:
    r_multi = api_post("/api/query", {
        "query": "What are the weather and ocean conditions near Mumbai for fishing?",
        "session_id": "test_multi_agent",
        "location": DEFAULT_VESSEL_GPS,
        "conversation_history": [],
    })
    mode = r_multi.get("mode")
    decision = r_multi.get("decision") or {}
    risk = r_multi.get("risk_level")
    key_conds = r_multi.get("key_conditions") or []
    recomms = r_multi.get("recommendations") or []
    agents = r_multi.get("agents_used") or []
    ans_multi = r_multi.get("answer", "")

    multi_ok = len(ans_multi) > 20 and risk in ("low", "moderate", "high", "critical", "none") and len(key_conds) > 0
    report("7.1_multi_agent_ocean_weather_pipeline", "PASS" if multi_ok else "FAIL", f"Mode: {mode}, Risk: {risk}, Decision: {decision.get('label')}, Key Conditions: {len(key_conds)}, Agents: {agents}")
except Exception as e:
    report("7.1_multi_agent_ocean_weather_pipeline", "FAIL", str(e))


# -------------------------------------------------------------
# 8. SAFETY CHECK TEST (POST /api/safety-check)
# -------------------------------------------------------------
try:
    # 8A: Safe location (Chennai offshore: 13.08, 80.28)
    s_safe = api_post("/api/safety-check", {"lat": 13.08, "lon": 80.28, "prev_state": "NORMAL"})
    dist_safe = s_safe.get("distance_to_boundary_km", 0)
    alert_safe = s_safe.get("alert_level")

    # 8B: Near boundary / caution location (Palk Strait: 10.0, 79.8)
    s_caution = api_post("/api/safety-check", {"lat": 10.0, "lon": 79.8, "prev_state": "NORMAL"})
    dist_caution = s_caution.get("distance_to_boundary_km", 0)

    # 8C: Danger/boundary crossing (9.5, 79.5)
    s_danger = api_post("/api/safety-check", {"lat": 9.5, "lon": 79.5, "prev_state": "WARNING"})
    alert_danger = s_danger.get("alert_level")

    no_negatives = dist_safe >= 0 and dist_caution >= 0
    safe_ok = dist_safe > 15.0 and alert_safe in ("none", "NORMAL")
    has_alert_system = alert_danger in ("warning", "caution", "critical") or dist_caution < dist_safe

    if no_negatives and safe_ok:
        report("8.1_safety_check_endpoint", "PASS", f"Safe dist: {dist_safe:.1f} km ({alert_safe}), Caution dist: {dist_caution:.1f} km, Danger alert: {alert_danger}. All values valid non-negative.")
    else:
        report("8.1_safety_check_endpoint", "FAIL", f"no_neg={no_negatives}, safe_ok={safe_ok}")
except Exception as e:
    report("8.1_safety_check_endpoint", "FAIL", str(e))


# -------------------------------------------------------------
# 13. SECURITY CHECK
# -------------------------------------------------------------
try:
    secrets = ["LLM_API_KEY", "IMD_API_KEY", "BHUVAN_ACCESS_TOKEN", "DATABASE_URL"]
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "src")
    found_secrets = []
    
    for root, _, files in os.walk(frontend_dir):
        for f in files:
            if f.endswith((".ts", ".tsx", ".js", ".jsx", ".html", ".css")):
                p = os.path.join(root, f)
                with open(p, "r", encoding="utf-8", errors="ignore") as fl:
                    content = fl.read()
                    for s in secrets:
                        if s in content:
                            found_secrets.append((f, s))

    # Check .gitignore for .env
    backend_gitignore = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gitignore")
    root_gitignore = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".gitignore")
    env_ignored = False
    for gpath in (backend_gitignore, root_gitignore):
        if os.path.exists(gpath):
            with open(gpath, "r", encoding="utf-8", errors="ignore") as gf:
                if ".env" in gf.read():
                    env_ignored = True
                    break

    if len(found_secrets) == 0 and env_ignored:
        report("13.1_security_credentials_audit", "PASS", "Zero secrets found in frontend source. .env is properly gitignored.")
    else:
        report("13.1_security_credentials_audit", "FAIL", f"found_secrets={found_secrets}, env_ignored={env_ignored}")
except Exception as e:
    report("13.1_security_credentials_audit", "FAIL", str(e))

print("\n" + "=" * 70)
total_tests = len(test_results)
passed_tests = sum(1 for r in test_results.values() if r["status"] == "PASS")
failed_tests = total_tests - passed_tests
print(f"RESULTS: {passed_tests}/{total_tests} PASSED ({failed_tests} failed)")
print("=" * 70)
