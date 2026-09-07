import requests

url = "https://mosdac.gov.in/apios/datasets.json"
params = {
    "datasetId": "3RIMG_L2B_SST",
    "startTime": "2024-01-01",
    "endTime": "2024-01-02",
    "count": "1"
}
try:
    r = requests.get(url, params=params, timeout=15)
    print("Status:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        print("Total results:", data.get("totalResults"))
        print("Keys:", data.keys())
        entries = data.get("entries", [])
        if entries:
            print("First entry sample:", entries[0])
    else:
        print("Response:", r.text[:300])
except Exception as e:
    print("Err:", e)
