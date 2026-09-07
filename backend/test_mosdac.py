r"""
Standalone test script to inspect and verify MOSDAC NetCDF Chlorophyll Data.
STEP 8 — Phase 1: Isolated NetCDF Inspection

File: C:\home\sys_oper\MOSDAC_Downloads\E06OCML4AC_20260903_25km_v1.0.1.nc
"""
import os
import sys
import numpy as np
import xarray as xr


NC_FILE_PATH = r"C:\home\sys_oper\MOSDAC_Downloads\E06OCML4AC_20260903_25km_v1.0.1.nc"


def inspect_mosdac_netcdf(filepath: str = NC_FILE_PATH):
    print("=" * 80)
    print("ORCA — STEP 8: MOSDAC NetCDF Chlorophyll Inspection")
    print("=" * 80)
    print(f"Target NetCDF File: {filepath}")

    if not os.path.exists(filepath):
        print(f"\n[ERROR] File not found at: {filepath}")
        sys.exit(1)

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"File Size: {file_size_mb:.2f} MB")
    print("-" * 80)

    # 1. Open dataset with xarray
    print("\n[1] Opening dataset with xarray.open_dataset()...")
    ds = xr.open_dataset(filepath)

    # 2. Dataset summary
    print("\n" + "=" * 80)
    print("[2] DATASET SUMMARY (ds)")
    print("=" * 80)
    print(ds)

    # 3. All dimensions
    print("\n" + "=" * 80)
    print("[3] DIMENSIONS")
    print("=" * 80)
    for dim_name, dim_size in ds.sizes.items():
        print(f"  - {dim_name}: {dim_size}")

    # 4. Coordinates
    print("\n" + "=" * 80)
    print("[4] COORDINATES")
    print("=" * 80)
    for coord_name, coord_var in ds.coords.items():
        dtype = coord_var.dtype
        shape = coord_var.shape
        dims = coord_var.dims
        attrs = dict(coord_var.attrs)
        print(f"  - {coord_name}: shape={shape}, dims={dims}, dtype={dtype}")
        if attrs:
            print(f"      attrs: {attrs}")

    # 5. Data variables
    print("\n" + "=" * 80)
    print("[5] DATA VARIABLES")
    print("=" * 80)
    for var_name, var_data in ds.data_vars.items():
        print(f"  - {var_name}: shape={var_data.shape}, dims={var_data.dims}, dtype={var_data.dtype}")
        attrs_snippet = {k: v for k, v in list(var_data.attrs.items())[:4]}
        print(f"      attrs: {attrs_snippet}")

    # 6. chla variable information
    print("\n" + "=" * 80)
    print("[6] CHLOROPHYLL ('chla') VARIABLE INSPECTION")
    print("=" * 80)
    chla_var_name = None
    if "chla" in ds.variables:
        chla_var_name = "chla"
    else:
        # Check if alternative casing or name exists
        for candidate in ["chla", "chlorophyll_a", "chlorophyll", "CHLA", "chl"]:
            if candidate in ds.variables:
                chla_var_name = candidate
                break

    if chla_var_name is None:
        print("  [FAIL] 'chla' variable NOT found in dataset variables!")
        print(f"  Available variables: {list(ds.variables.keys())}")
    else:
        chla = ds[chla_var_name]
        print(f"  Variable Name: '{chla_var_name}'")
        print(f"  Shape: {chla.shape}")
        print(f"  Dimensions: {chla.dims}")
        print(f"  Data Type: {chla.dtype}")
        print("\n  Attributes / Metadata:")
        for attr_k, attr_v in chla.attrs.items():
            print(f"    - {attr_k}: {attr_v}")

        # Missing / fill value information
        print("\n  Missing / Fill Value Information:")
        print(f"    - _FillValue (attrs): {chla.attrs.get('_FillValue')}")
        print(f"    - _FillValue (encoding): {chla.encoding.get('_FillValue')}")
        print(f"    - missing_value (attrs): {chla.attrs.get('missing_value')}")
        print(f"    - missing_value (encoding): {chla.encoding.get('missing_value')}")

    # 7. Latitude information
    print("\n" + "=" * 80)
    print("[7] LATITUDE INFORMATION")
    print("=" * 80)
    lat_coord_name = None
    for name in ["latitude", "lat", "latitudes", "LATITUDE"]:
        if name in ds.coords or name in ds.variables:
            lat_coord_name = name
            break

    if lat_coord_name:
        lat = ds[lat_coord_name]
        print(f"  Coordinate Name: '{lat_coord_name}'")
        print(f"  Shape: {lat.shape}, Dims: {lat.dims}, Dtype: {lat.dtype}")
        print(f"  Min Latitude: {float(lat.min()):.4f}")
        print(f"  Max Latitude: {float(lat.max()):.4f}")
        first_few = lat.values[:5] if lat.ndim == 1 else lat.values.ravel()[:5]
        last_few = lat.values[-5:] if lat.ndim == 1 else lat.values.ravel()[-5:]
        print(f"  First 5 values: {first_few}")
        print(f"  Last 5 values:  {last_few}")
        print(f"  Attributes: {dict(lat.attrs)}")
    else:
        print("  [FAIL] Latitude coordinate not found!")

    # 8. Longitude information
    print("\n" + "=" * 80)
    print("[8] LONGITUDE INFORMATION")
    print("=" * 80)
    lon_coord_name = None
    for name in ["longitude", "lon", "longitudes", "LONGITUDE"]:
        if name in ds.coords or name in ds.variables:
            lon_coord_name = name
            break

    if lon_coord_name:
        lon = ds[lon_coord_name]
        print(f"  Coordinate Name: '{lon_coord_name}'")
        print(f"  Shape: {lon.shape}, Dims: {lon.dims}, Dtype: {lon.dtype}")
        print(f"  Min Longitude: {float(lon.min()):.4f}")
        print(f"  Max Longitude: {float(lon.max()):.4f}")
        first_few = lon.values[:5] if lon.ndim == 1 else lon.values.ravel()[:5]
        last_few = lon.values[-5:] if lon.ndim == 1 else lon.values.ravel()[-5:]
        print(f"  First 5 values: {first_few}")
        print(f"  Last 5 values:  {last_few}")
        print(f"  Attributes: {dict(lon.attrs)}")
    else:
        print("  [FAIL] Longitude coordinate not found!")

    # 9. Time information
    print("\n" + "=" * 80)
    print("[9] TIME INFORMATION")
    print("=" * 80)
    time_coord_name = None
    for name in ["time", "date", "TIME", "datetime"]:
        if name in ds.coords or name in ds.variables:
            time_coord_name = name
            break

    if time_coord_name:
        t = ds[time_coord_name]
        print(f"  Coordinate Name: '{time_coord_name}'")
        print(f"  Shape: {t.shape}, Dims: {t.dims}, Dtype: {t.dtype}")
        print(f"  Time Value(s): {t.values}")
        print(f"  Attributes: {dict(t.attrs)}")
    else:
        print("  [INFO] No explicit 'time' coordinate found in coordinates.")
        # Check global attributes for time/date
        time_attrs = {k: v for k, v in ds.attrs.items() if any(w in k.lower() for w in ["time", "date", "day", "start", "end"])}
        print(f"  Time-related Global Attributes: {time_attrs}")

    # Global attributes
    print("\n" + "=" * 80)
    print("[10] GLOBAL ATTRIBUTES")
    print("=" * 80)
    for k, v in ds.attrs.items():
        print(f"  - {k}: {v}")

    # 10. Sanity Checks
    print("\n" + "=" * 80)
    print("[11] SANITY CHECKS")
    print("=" * 80)

    # Sanity Check 1: chla exists
    chla_exists = chla_var_name is not None
    print(f"  [CHECK 1] 'chla' variable exists: {'PASSED' if chla_exists else 'FAILED'}")

    # Sanity Check 2: latitude and longitude exist
    coords_exist = (lat_coord_name is not None) and (lon_coord_name is not None)
    print(f"  [CHECK 2] Latitude & Longitude exist: {'PASSED' if coords_exist else 'FAILED'} (lat='{lat_coord_name}', lon='{lon_coord_name}')")

    # Sanity Check 3: Observation date around 2026-09-03
    date_found = False
    date_info_str = "None"
    if time_coord_name and ("2026-09-03" in str(ds[time_coord_name].values) or "20260903" in str(ds[time_coord_name].values)):
        date_found = True
        date_info_str = f"Time coordinate contains {ds[time_coord_name].values}"
    else:
        # Check global attributes or filename
        for k, v in ds.attrs.items():
            if "2026-09-03" in str(v) or "20260903" in str(v):
                date_found = True
                date_info_str = f"Global attribute '{k}': {v}"
                break
        if not date_found and ("20260903" in filepath or "2026-09-03" in filepath):
            date_found = True
            date_info_str = f"Filename timestamp confirms: 20260903"

    print(f"  [CHECK 3] Expected observation date around 2026-09-03: {'PASSED' if date_found else 'WARNING'} ({date_info_str})")

    # Sanity Check 4: Valid non-NaN chlorophyll values exist
    has_valid_values = False
    if chla_exists:
        chla_data = ds[chla_var_name].values
        total_pixels = chla_data.size
        nan_pixels = int(np.isnan(chla_data).sum())
        finite_mask = np.isfinite(chla_data)

        # Also account for raw fill values if not automatically masked
        raw_fill = ds[chla_var_name].attrs.get("_FillValue")
        if raw_fill is not None:
            finite_mask = finite_mask & (chla_data != raw_fill)

        valid_pixels = int(finite_mask.sum())
        valid_percentage = (valid_pixels / total_pixels) * 100.0

        if valid_pixels > 0:
            has_valid_values = True
            valid_vals = chla_data[finite_mask]
            min_val = float(np.min(valid_vals))
            max_val = float(np.max(valid_vals))
            mean_val = float(np.mean(valid_vals))
            median_val = float(np.median(valid_vals))
            print(f"  [CHECK 4] Valid / non-NaN chlorophyll values: PASSED")
            print(f"      - Total Grid Cells: {total_pixels:,}")
            print(f"      - NaN / Fill Cells: {nan_pixels:,} ({(nan_pixels / total_pixels) * 100:.1f}%)")
            print(f"      - Valid Data Cells: {valid_pixels:,} ({valid_percentage:.1f}%)")
            print(f"      - Min Chlorophyll:  {min_val:.4f} {ds[chla_var_name].attrs.get('units', '')}")
            print(f"      - Max Chlorophyll:  {max_val:.4f} {ds[chla_var_name].attrs.get('units', '')}")
            print(f"      - Mean Chlorophyll: {mean_val:.4f} {ds[chla_var_name].attrs.get('units', '')}")
            print(f"      - Median Chlorophyll: {median_val:.4f} {ds[chla_var_name].attrs.get('units', '')}")
        else:
            print(f"  [CHECK 4] Valid / non-NaN chlorophyll values: FAILED (All {total_pixels} cells are NaN or fill value)")

    print("=" * 80)
    all_passed = chla_exists and coords_exist and date_found and has_valid_values
    print(f"OVERALL SANITY STATUS: {'ALL CHECKS PASSED - SUCCESS' if all_passed else 'SOME CHECKS REQUIRE ATTENTION'}")
    print("=" * 80)

    ds.close()
    return all_passed


if __name__ == "__main__":
    success = inspect_mosdac_netcdf()
    sys.exit(0 if success else 1)
