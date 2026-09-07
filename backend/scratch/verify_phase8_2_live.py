"""
Live End-to-End Verification Script for ORCA Phase 8.2.

Executes real HTTP requests against http://localhost:8000/api/query for:
1. hi (General Conversation)
2. how are you? (General Conversation)
3. what's the time? (Utility - Time)
4. what's today's date? (Utility - Date)
5. what are the ocean conditions? (Marine - Ocean Minimality)
6. is it safe to travel? (Safety Supremacy)
7. hello, what is the weather near my location? (Mixed Conversation + Weather)
8. Should I take my boat out tomorrow morning considering the weather and sea conditions? (Multi-Agent Complex)
9. Contextual Follow-up: "What is the sea temperature?" -> "And the wind?"
"""
import json
import time
import urllib.request

BASE_URL = "http://127.0.0.1:8000/api/query"


def send_query(query_str, session_id="live-p82", location=None, history=None):
    payload = {
        "query": query_str,
        "session_id": session_id,
        "location": location or {"lat": 13.0827, "lon": 80.2707},
        "conversation_history": history or [],
    }
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req) as resp:
        duration_ms = (time.time() - t0) * 1000
        data = json.loads(resp.read().decode("utf-8"))
        return data, duration_ms


def run_all_checks():
    print("=" * 70)
    print("ORCA PHASE 8.2 LIVE END-TO-END VERIFICATION")
    print("=" * 70)

    test_cases = [
        {
            "id": 1,
            "title": "General Greeting ('hi')",
            "query": "hi",
            "expected_mode": "conversation",
            "expect_agents": False,
        },
        {
            "id": 2,
            "title": "Social Inquiry ('how are you?')",
            "query": "how are you?",
            "expected_mode": "conversation",
            "expect_agents": False,
        },
        {
            "id": 3,
            "title": "Clock Utility ('what's the time?')",
            "query": "what's the time?",
            "expected_mode": "utility",
            "expect_agents": False,
            "expect_in_answer": ["IST", ":", "M"],  # e.g., "11:45 PM"
        },
        {
            "id": 4,
            "title": "Date Utility ('what's today's date?')",
            "query": "what's today's date?",
            "expected_mode": "utility",
            "expect_agents": False,
            "expect_in_answer": ["2026", "September"],
        },
        {
            "id": 5,
            "title": "Marine Ocean Query ('what are the ocean conditions?')",
            "query": "what are the ocean conditions?",
            "expected_mode": "marine",
            "expect_agents": True,
            "expected_agent": "Ocean",
        },
        {
            "id": 6,
            "title": "Safety Query ('is it safe to travel?')",
            "query": "is it safe to travel?",
            "expected_mode": "safety",
            "expect_agents": True,
            "expected_agent": "Safety",
        },
        {
            "id": 7,
            "title": "Mixed Greeting + Weather ('hello, what is the weather near my location?')",
            "query": "hello, what is the weather near my location?",
            "expected_mode": "marine",
            "expect_agents": True,
            "expected_agent": "Weather",
        },
        {
            "id": 8,
            "title": "Multi-Agent Complex Query ('Should I take my boat out tomorrow morning considering the weather and sea conditions?')",
            "query": "Should I take my boat out tomorrow morning considering the weather and sea conditions?",
            "expected_mode": ["marine", "safety"],
            "expect_agents": True,
            "multiple_agents": True,
        },
    ]

    all_passed = True

    for tc in test_cases:
        print(f"\n[{tc['id']}/8] Testing: {tc['title']}")
        print(f"    Query: \"{tc['query']}\"")
        try:
            res, latency = send_query(tc["query"], session_id=f"sess-test-{tc['id']}")
            mode = res.get("mode")
            answer = res.get("answer", "")
            risk_level = res.get("risk_level")
            agents = res.get("agents_used", [])

            print(f"    Latency:     {latency:.1f} ms")
            print(f"    Mode:        {mode}")
            print(f"    Risk Level:  {risk_level}")
            print(f"    Agents Used: {agents}")
            print(f"    Answer:      {answer[:120]}...")

            # Assertions
            if isinstance(tc["expected_mode"], list):
                assert mode in tc["expected_mode"], f"Expected mode in {tc['expected_mode']}, got {mode}"
            else:
                assert mode == tc["expected_mode"], f"Expected mode {tc['expected_mode']}, got {mode}"

            if not tc["expect_agents"]:
                assert len(agents) == 0, f"Expected 0 agents for {mode}, got {agents}"
                assert risk_level == "none", f"Expected risk_level 'none' for {mode}, got {risk_level}"

            if tc.get("expected_agent"):
                agent_names_lower = [a.lower() for a in agents]
                assert tc["expected_agent"].lower() in agent_names_lower or any(tc["expected_agent"].lower() in a for a in agent_names_lower), (
                    f"Expected agent '{tc['expected_agent']}' in {agents}"
                )

            if tc.get("multiple_agents"):
                assert len(agents) >= 2, f"Expected >= 2 agents for complex query, got {agents}"

            # Strict security checks
            assert "<svg" not in answer.lower(), "Security violation: <svg found in answer text!"
            assert "IMD_API_KEY" not in answer, "Leakage violation: IMD_API_KEY leaked!"
            assert "BHUVAN_ACCESS_TOKEN" not in answer, "Leakage violation: BHUVAN token leaked!"
            assert "```json" not in answer, "Formatting violation: raw JSON exposed in answer!"

            print(f"    Status:      [PASS]")

        except Exception as e:
            print(f"    Status:      [FAIL]: {e}")
            all_passed = False

    # 9. Contextual Follow-Up Test
    print("\n[9/9] Testing Contextual Follow-Up Sequence:")
    print("    Turn 1: \"What is the sea temperature?\"")
    res1, lat1 = send_query("What is the sea temperature?", session_id="followup-sess")
    print(f"    Turn 1 Mode: {res1.get('mode')} | Agents: {res1.get('agents_used')}")

    print("    Turn 2: \"And the wind?\" (with context history)")
    history = [
        {"role": "user", "content": "What is the sea temperature?"},
        {"role": "assistant", "content": res1.get("answer", "")},
    ]
    res2, lat2 = send_query("And the wind?", session_id="followup-sess", history=history)
    print(f"    Turn 2 Mode: {res2.get('mode')} | Agents: {res2.get('agents_used')}")
    print(f"    Turn 2 Answer: {res2.get('answer', '')[:120]}...")

    assert res2.get("mode") == "marine", f"Expected marine mode for follow-up, got {res2.get('mode')}"
    agents2 = [a.lower() for a in res2.get("agents_used", [])]
    assert "weather" in agents2, f"Expected weather agent selected for wind follow-up, got {agents2}"
    print("    Status:      [PASS] (Contextual follow-up resolved successfully)")

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL 9 LIVE VERIFICATION SUITES PASSED! Phase 8.2 Certified Operational.")
    else:
        print("SOME TESTS FAILED.")
    print("=" * 70)


if __name__ == "__main__":
    run_all_checks()
