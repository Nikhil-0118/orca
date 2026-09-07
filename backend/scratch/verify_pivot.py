import asyncio
import httpx

API_URL = "http://127.0.0.1:8000/api/query"

async def test_pivot():
    async with httpx.AsyncClient(timeout=30.0) as client:
        vessel = {
            "latitude": 26.5207,
            "longitude": 80.2564,
            "source": "browser_gps",
            "label": "Kanpur, Uttar Pradesh",
            "geographic_type": "inland",
        }

        # Turn 1: Best fishing spot near Mumbai?
        res1 = await client.post(API_URL, json={
            "query": "Best fishing spot near Mumbai?",
            "location": vessel,
            "session_id": "pivot_test"
        })
        d1 = res1.json()
        print("Turn 1 (Mumbai):", d1.get("spatial", {}).get("target_location"))

        # Turn 2: What about Chennai?
        res2 = await client.post(API_URL, json={
            "query": "What about Chennai?",
            "location": vessel,
            "session_id": "pivot_test",
            "conversation_history": [
                {"role": "user", "content": "Best fishing spot near Mumbai?"},
                {"role": "assistant", "content": d1.get("answer", "")[:200]},
            ]
        })
        d2 = res2.json()
        print("Turn 2 (What about Chennai?):", d2.get("location", {}).get("resolved_place"))

        # Turn 3: Give me the map
        res3 = await client.post(API_URL, json={
            "query": "Give me the map",
            "location": vessel,
            "session_id": "pivot_test",
            "conversation_history": [
                {"role": "user", "content": "Best fishing spot near Mumbai?"},
                {"role": "assistant", "content": d1.get("answer", "")[:200]},
                {"role": "user", "content": "What about Chennai?"},
                {"role": "assistant", "content": d2.get("answer", "")[:200]},
            ]
        })
        d3 = res3.json()
        target = d3.get("spatial", {}).get("target_location")
        print("Turn 3 (Give me the map): Target =", target)
        assert abs(target.get("latitude", 0) - 12.85) < 0.1, f"Expected Chennai (~12.85), got {target}"
        print("PIVOT TEST VERIFIED: Chennai is final map target!")

if __name__ == "__main__":
    asyncio.run(test_pivot())
