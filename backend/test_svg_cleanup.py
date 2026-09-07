import urllib.request
import json
import re

def test_q(query, lat=26.52, lon=80.26):
    payload = {
        'query': query,
        'session_id': f'test-session-{abs(hash(query))}',
        'location': {
            'latitude': lat,
            'longitude': lon,
            'accuracy': 15.0,
            'source': 'live_browser_gps'
        }
    }
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/query',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    print(f"=== Query: {query} ===")
    print(f"Decision: {data.get('decision')}")
    print(f"Key Conditions: {data.get('key_conditions')}")
    print(f"Recommendations: {data.get('recommendations')}")
    safe_ans = str(data.get('answer'))[:120].encode('ascii', errors='replace').decode('ascii')
    print(f"Answer: {safe_ans}...")
    raw_str = json.dumps(data)
    markers = re.findall(r'\b[Ss][Vv][Gg][A-Z]\w*', raw_str)
    print(f"Found svg markers in JSON: {markers}")
    assert len(markers) == 0, f"Found svg markers: {markers}"
    print("PASS: Clean response!\n")

if __name__ == "__main__":
    test_q("what is my location")
    test_q("oceans nearby me")
    test_q("what is the weather here")
    test_q("what can you do")
    print("ALL 4 API QUERIES PASSED SANITIZATION CHECK!")
