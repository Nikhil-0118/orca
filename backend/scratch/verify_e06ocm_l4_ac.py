import requests
import json

url = "https://mosdac.gov.in/apios/datasets.json"
params = {
    "datasetId": "E06OCM_L4_AC",
    "startTime": "2026-09-01",
    "endTime": "2026-09-04",
    "count": "5"
}

r = requests.get(url, params=params, timeout=15)
print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    print("Total Results:", data.get("totalResults"))
    print("Items Per Page:", data.get("itemsPerPage"))
    for i, e in enumerate(data.get("entries", [])):
        print(f"\nEntry {i+1}:")
        print("  Identifier:", e.get("identifier"))
        print("  ID:", e.get("id"))
        print("  Updated:", e.get("updated"))
        print("  dcDate:", e.get("dcDate"))
        print("  BoundingBox:", e.get("boundbox"))
        print("  Summary:", e.get("summary")[:120] if e.get("summary") else None)
