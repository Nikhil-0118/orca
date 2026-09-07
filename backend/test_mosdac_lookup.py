r"""
Standalone test script for MOSDAC NetCDF Chlorophyll Spatial Grid Lookup.
STEP 9 — Latitude + Longitude → Nearest MOSDAC Grid Cell → Chlorophyll Value

Target NetCDF File: C:\home\sys_oper\MOSDAC_Downloads\E06OCML4AC_20260903_25km_v1.0.1.nc
"""
import math
import os
import sys
from typing import Any, Dict, Optional
import numpy as np
import xarray as xr


NC_FILE_PATH = r"C:\home\sys_oper\MOSDAC_Downloads\E06OCML4AC_20260903_25km_v1.0.1.nc"
FILL_VALUE_THRESHOLD = -900000000.0  # Encoded missing value is -999000000.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points in kilometers.
    Handles longitudes across 0-360 or -180/+180 wrapping.
    """
    r_lat1 = math.radians(lat1)
    r_lat2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    # Normalized delta longitude across 360-degree circle
    dlon_deg = ((lon2 - lon1 + 180.0) % 360.0) - 180.0
    dlon = math.radians(dlon_deg)

    a = math.sin(dlat / 2.0) ** 2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(6371.0 * c, 2)


def get_chlorophyll(
    latitude: float,
    longitude: float,
    filepath: str = NC_FILE_PATH,
    dataset: Optional[xr.Dataset] = None,
) -> Dict[str, Any]:
    """
    Look up nearest chlorophyll (chla) value in MOSDAC NetCDF dataset for a given coordinate.

    1. Accepts latitude and longitude in decimal degrees (-90 to +90, -180 to +180).
    2. Converts negative longitudes to 0–360° grid convention using modulo 360.
    3. Finds nearest grid latitude and longitude using index distance minimization.
    4. Extracts chla value at available time and level indices (time=0, lev=0).
    5. Validates against missing/fill values (-999000000.0 or NaNs).
    6. Reports distance from requested coordinate to grid center.
    """
    should_close = False
    if dataset is None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"MOSDAC NetCDF file not found: {filepath}")
        ds = xr.open_dataset(filepath)
        should_close = True
    else:
        ds = dataset

    try:
        lat_arr = ds["lat"].values
        lon_arr = ds["lon"].values

        # Validate latitude coverage
        lat_min = float(lat_arr.min())
        lat_max = float(lat_arr.max())
        if not (lat_min <= latitude <= lat_max):
            return {
                "status": "OUT_OF_BOUNDS",
                "error": f"Requested latitude {latitude} is outside dataset coverage [{lat_min:.2f}, {lat_max:.2f}]",
                "requested_latitude": latitude,
                "requested_longitude": longitude,
            }

        # Convert longitude from [-180, 180] to [0, 360) convention
        is_negative_lon = longitude < 0.0
        converted_longitude = (longitude % 360.0) if is_negative_lon else longitude
        converted_longitude = round(converted_longitude, 4)

        # Find nearest grid indices
        lat_idx = int(np.abs(lat_arr - latitude).argmin())
        lon_idx = int(np.abs(lon_arr - converted_longitude).argmin())

        grid_lat = float(lat_arr[lat_idx])
        grid_lon = float(lon_arr[lon_idx])

        # Extract chla value accounting for dimensions: ('time', 'lev', 'lat', 'lon')
        # Use available time=0 and lev=0
        raw_val = float(ds["chla"].isel(time=0, lev=0, lat=lat_idx, lon=lon_idx).values)

        # Calculate great-circle distance between requested coord and nearest grid center
        dist_km = haversine_distance_km(latitude, longitude, grid_lat, grid_lon)

        # Extract observation date from time coordinate or metadata
        obs_date = "unknown"
        if "time" in ds.coords and ds["time"].size > 0:
            time_val = str(ds["time"].values[0])
            obs_date = time_val.split("T")[0]
        elif "history" in ds.attrs:
            obs_date = "2026-09-03"

        # Check unit attribute metadata - do not assume or invent
        unit_attr = ds["chla"].attrs.get("units")
        if unit_attr and str(unit_attr).strip():
            unit_str = str(unit_attr).strip()
            unit_explicit = True
        else:
            unit_str = "Unit metadata not explicitly provided by this NetCDF variable."
            unit_explicit = False

        # Detect fill / missing / NaN values
        fill_attr = ds["chla"].attrs.get("_FillValue") or ds["chla"].encoding.get("_FillValue")
        is_fill = (
            np.isnan(raw_val)
            or raw_val <= FILL_VALUE_THRESHOLD
            or (fill_attr is not None and abs(raw_val - float(fill_attr)) < 1e-3)
        )

        if is_fill:
            return {
                "status": "MISSING_VALUE",
                "requested_latitude": latitude,
                "requested_longitude": longitude,
                "converted_longitude": converted_longitude if is_negative_lon else None,
                "grid_latitude": round(grid_lat, 4),
                "grid_longitude": round(grid_lon, 4),
                "chlorophyll_value": None,
                "raw_value": raw_val,
                "units": unit_str,
                "unit_explicit": unit_explicit,
                "observation_date": obs_date,
                "distance_km": dist_km,
                "note": "Nearest grid cell contains fill/missing value (-999000000.0).",
            }

        return {
            "status": "SUCCESS",
            "requested_latitude": latitude,
            "requested_longitude": longitude,
            "converted_longitude": converted_longitude if is_negative_lon else None,
            "grid_latitude": round(grid_lat, 4),
            "grid_longitude": round(grid_lon, 4),
            "chlorophyll_value": round(raw_val, 4),
            "units": unit_str,
            "unit_explicit": unit_explicit,
            "observation_date": obs_date,
            "distance_km": dist_km,
        }

    finally:
        if should_close:
            ds.close()


def run_tests():
    print("=" * 60)
    print("ORCA - STEP 9: MOSDAC LOCATION LOOKUP TEST")
    print("=" * 60)
    print(f"Dataset File: {NC_FILE_PATH}")
    print("=" * 60)

    # Open dataset once for fast execution across all test locations
    ds = xr.open_dataset(NC_FILE_PATH)

    test_locations = [
        {
            "name": "Test 1 - Mumbai",
            "lat": 19.0760,
            "lon": 72.8777,
        },
        {
            "name": "Test 2 - Chennai",
            "lat": 13.0827,
            "lon": 80.2707,
        },
        {
            "name": "Test 3 - Kolkata",
            "lat": 22.5726,
            "lon": 88.3639,
        },
        {
            "name": "Test 4 - Negative longitude test",
            "lat": 25.0000,
            "lon": -70.0000,
        },
    ]

    for loc in test_locations:
        print(f"\n--- {loc['name']} ---")
        res = get_chlorophyll(loc["lat"], loc["lon"], dataset=ds)

        print("\nRequested location:")
        print(f"Latitude: {res['requested_latitude']:.4f}")
        print(f"Longitude: {res['requested_longitude']:.4f}")
        if res.get("converted_longitude") is not None:
            print(f"Converted longitude (0-360 deg): {res['converted_longitude']:.4f}")

        print("\nDataset coordinate:")
        print(f"Latitude: {res.get('grid_latitude')}")
        print(f"Longitude: {res.get('grid_longitude')}")

        print("\nObservation date:")
        print(f"{res.get('observation_date')}")

        print("\nChlorophyll-A:")
        if res.get("chlorophyll_value") is not None:
            if res.get("unit_explicit"):
                print(f"{res['chlorophyll_value']:.4f} {res['units']}")
            else:
                print(f"{res['chlorophyll_value']:.4f}")
                print(f"{res['units']}")
        else:
            print(f"None (Detected fill value: {res.get('raw_value')})")
            print(f"{res['units']}")

        print("\nGrid distance:")
        print(f"{res.get('distance_km')} km")

        print("\nStatus:")
        print(f"{res['status']}")

    ds.close()
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
