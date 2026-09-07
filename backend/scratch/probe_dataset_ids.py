import requests
import time

url = "https://mosdac.gov.in/apios/datasets.json"

candidates = [
    # Based on E06OCML4AC_20260903_25km_v1.0.1.nc
    "E06OCML4AC",
    "E06OCM_L4AC",
    "E06_OCM_L4AC",
    "E06OCM_L4_AC",
    "E06OCML4A",
    "E06OCM_L4A",
    "E06OCML4",
    "E06OCM_L4",
    "E06_OCM_L4",
    "E06OCM_L4_CHLA",
    "E06OCM_L4_CHL",
    "E06OCML4_CHLA",
    "E06OCML4_CHL",
    "E06OCM_CHLA",
    "E06OCM_CHL",
    "EOS06_OCM_L4",
    "EOS06_OCM_L4AC",
    "EOS06_OCML4AC",
    "OCM_L4_CHLA",
    "OCM_L4AC",
    "OCML4AC",
    "E06OCML4AC_25KM",
    "E06OCM_L4AC_25KM",
    "E06OCM_L4_25KM",
    "E06OCM_L4A_25KM",
    "E06OCM_L3_CHLA",
    "E06OCM_L2C_CHL",
    "E06OCM_L2C_AD",
    "E06OCM_L2C",
    "E06OCM_L1B",
    "E06OCM_L1C",
    "E06OCM_L2B",
    "E06OCM_L3",
    "E06OCM_L4_GLOBAL",
    "E06OCM_L4_IND",
    "E06OCM_L4_IO",
    "E06OCM_CHLA_25KM",
    "E06_OCM_CHLA_25KM",
    "E06_OCM_L4_CHLA_25KM",
    "E06OCML4AC25KM",
    "E06OCML4_25KM",
    "E06OCM_L4AC_25km",
    "E06OCML4AC_25km",
]

print(f"Testing {len(candidates)} candidates...")
found = []
for c in candidates:
    try:
        r = requests.get(url, params={"datasetId": c, "count": "1"}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            total = data.get("totalResults", 0)
            print(f"[FOUND] {c} -> totalResults: {total}")
            entries = data.get("entries", [])
            if entries:
                print(f"        sample identifier: {entries[0].get('identifier')}")
            found.append((c, total, entries[0] if entries else None))
        elif r.status_code != 500:
            print(f"[STATUS {r.status_code}] {c}")
    except Exception as e:
        print(f"[ERR] {c}: {e}")
    time.sleep(0.1)

print("\n=== RESULTS ===")
for c, tot, entry in found:
    print(f"datasetId: {c}, totalResults: {tot}, sample: {entry.get('identifier') if entry else 'none'}")
