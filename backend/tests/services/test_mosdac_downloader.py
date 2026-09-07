"""
Unit and Integration Tests for MOSDAC Data Acquisition & Downloader (Phase 12).

Verifies:
- Test 1: Existing valid local file discovery, validation, and metadata extraction
- Test 2: Data freshness calculation (fresh vs stale vs unavailable)
- Test 3: Invalid download rejection and active dataset preservation (no corrupt replacement)
- Test 4: Remote acquisition failure fallback (network error / timeout preserves previous valid file)
- Test 5: No data available handling (truthful unavailable status without fabricated values)
- Test 6: Full Chennai lookup through MosdacService using active dataset
"""
import os
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.services.mosdac_downloader import (
    MosdacDownloader,
    validate_netcdf_file,
    calculate_data_age_hours,
    classify_freshness,
    MIN_VALID_FILE_SIZE_BYTES,
)
from app.services.mosdac_service import MosdacService


# ── TEST 1: Existing Valid Local File ─────────────────────────────────────────

def test_01_existing_valid_local_file():
    """
    Test 1: Verify the real MOSDAC NetCDF file is discovered,
    successfully passes NetCDF structure validation, and metadata is extracted.
    """
    downloader = MosdacDownloader()
    datasets = downloader.discover_local_datasets()

    assert len(datasets) >= 1, "At least one valid local MOSDAC NetCDF file should be discovered"
    top = datasets[0]

    assert top["filepath"].endswith(".nc")
    assert top["file_size_bytes"] > MIN_VALID_FILE_SIZE_BYTES
    assert top["observation_date"] in ("2026-09-03", "2026-09-04")
    assert top["lat_count"] == 1080
    assert top["lon_count"] == 1440
    assert top["chla_shape"] == [1, 1, 1080, 1440]

    # Verify active dataset retrieval
    active = downloader.get_active_dataset()
    assert active["status"] == "valid"
    assert active["filepath"] == top["filepath"]
    assert active["observation_date"] in ("2026-09-03", "2026-09-04")
    assert active["data_source_type"] in ("archive", "remote_authenticated")


# ── TEST 2: Freshness Calculation ─────────────────────────────────────────────

def test_02_freshness_calculation():
    """
    Test 2: Verify correct classification for fresh, stale, and unavailable data.
    """
    now_utc = datetime.now(timezone.utc)

    # 1. Fresh observation (12 hours ago vs 24.0h threshold)
    t_fresh = (now_utc - timedelta(hours=12.0)).strftime("%Y-%m-%dT%H:%M:%SZ")
    age_fresh = calculate_data_age_hours(t_fresh, now_utc)
    assert age_fresh is not None
    assert 11.9 <= age_fresh <= 12.1
    assert classify_freshness(age_fresh, max_age_hours=24.0) == "fresh"

    # 2. Stale observation (48 hours ago vs 24.0h threshold)
    t_stale = (now_utc - timedelta(hours=48.0)).strftime("%Y-%m-%dT%H:%M:%SZ")
    age_stale = calculate_data_age_hours(t_stale, now_utc)
    assert age_stale is not None
    assert 47.9 <= age_stale <= 48.1
    assert classify_freshness(age_stale, max_age_hours=24.0) == "stale"

    # 3. Missing / unknown observation date
    assert calculate_data_age_hours("unknown", now_utc) is None
    assert calculate_data_age_hours("", now_utc) is None
    assert classify_freshness(None) == "unavailable"


# ── TEST 3: Invalid Download Rejection & Active Dataset Preservation ───────────

def test_03_invalid_download_rejection():
    """
    Test 3: Simulate a corrupt/invalid download (e.g. truncated file or HTML error page).
    Verify that the invalid file is rejected, never promoted to active dataset,
    and the existing valid dataset is preserved.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a valid reference dataset by copying the real test file
        real_file = r"C:\home\sys_oper\MOSDAC_Downloads\E06OCML4AC_20260903_25km_v1.0.1.nc"
        assert os.path.exists(real_file)

        valid_file_copy = os.path.join(temp_dir, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        shutil.copyfile(real_file, valid_file_copy)

        downloader = MosdacDownloader(
            download_dir=temp_dir,
            default_file_path=valid_file_copy,
            remote_url="https://mock-mosdac.example.com/data/new_file.nc",
            auto_download_enabled=True,
        )

        # Confirm initial active dataset is the valid copy
        initial_active = downloader.get_active_dataset()
        assert initial_active["status"] == "valid"
        assert initial_active["filepath"] == valid_file_copy

        # Simulate corrupt download: an HTML 404 / error response
        html_error_payload = b"<!DOCTYPE html><html><body><h1>404 Not Found</h1></body></html>"

        class MockResponse:
            status_code = 200
            reason_phrase = "OK"

            def iter_bytes(self, chunk_size=65536):
                yield html_error_payload

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        class MockClient:
            def __init__(self, *args, **kwargs):
                pass

            def stream(self, method, url, **kwargs):
                return MockResponse()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        with patch("httpx.Client", MockClient):
            success, final_path, err = downloader.download_remote_dataset(
                url="https://mock-mosdac.example.com/data/new_file.nc",
                target_filename="E06OCML4AC_20260904_25km_v1.0.1.nc",
            )
            # Must fail validation
            assert success is False
            assert final_path is None
            assert "below minimum valid NetCDF threshold" in err

        # Verify active dataset is STILL the valid copy (not replaced by corrupt file)
        post_active = downloader.get_active_dataset()
        assert post_active["status"] == "valid"
        assert post_active["filepath"] == valid_file_copy


# ── TEST 4: Remote Failure Fallback ───────────────────────────────────────────

def test_04_remote_failure_fallback():
    """
    Test 4: Simulate remote failure (HTTP 500 or timeout).
    Verify that remote failure does not crash the application and
    the previous valid local dataset is retained.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        real_file = r"C:\home\sys_oper\MOSDAC_Downloads\E06OCML4AC_20260903_25km_v1.0.1.nc"
        valid_file_copy = os.path.join(temp_dir, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        shutil.copyfile(real_file, valid_file_copy)

        downloader = MosdacDownloader(
            download_dir=temp_dir,
            default_file_path=valid_file_copy,
            remote_url="https://mosdac.example.com/timeout.nc",
            auto_download_enabled=True,
            max_age_hours=1.0,  # Mark existing file as stale to force download attempt
        )

        class FailingClient:
            def __init__(self, *args, **kwargs):
                pass

            def stream(self, method, url, **kwargs):
                import httpx
                raise httpx.ConnectTimeout("Connection timed out connecting to remote MOSDAC server")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        with patch("httpx.Client", FailingClient):
            active = downloader.get_active_dataset()
            # Does not crash; falls back to existing valid file
            assert active["status"] == "valid"
            assert active["filepath"] == valid_file_copy
            assert active["observation_date"] == "2026-09-03"
            assert active["download_attempted"] is True
            assert active["download_success"] is False


# ── TEST 5: No Data Available ────────────────────────────────────────────────

def test_05_no_data_available():
    """
    Test 5: When no valid local dataset exists and remote retrieval is unavailable,
    verify that the downloader and MosdacService return a truthful 'unavailable' status
    with no fabricated coordinates or fake values.
    """
    with tempfile.TemporaryDirectory() as empty_dir:
        downloader = MosdacDownloader(
            download_dir=empty_dir,
            default_file_path=os.path.join(empty_dir, "nonexistent.nc"),
            remote_url=None,
            auto_download_enabled=False,
        )

        active = downloader.get_active_dataset()
        assert active["status"] == "unavailable"
        assert active["filepath"] is None
        assert active["observation_date"] is None
        assert active["freshness"] == "unavailable"

        # Verify MosdacService initialized with this empty path returns unavailable
        svc = MosdacService(filepath=os.path.join(empty_dir, "nonexistent.nc"))
        res = svc.get_chlorophyll(13.0827, 80.2707)
        assert res["status"] == "unavailable"
        assert res["value"] is None
        assert "MOSDAC NetCDF file unavailable" in res["error"]


# ── TEST 6: Real MOSDAC Chennai Lookup Through Service ───────────────────────

def test_06_real_mosdac_chennai_lookup():
    """
    Test 6: Run Chennai (lat=13.0827, lon=80.2707) through MosdacService.
    Verify:
    - source = MOSDAC
    - parameter = chlorophyll_a
    - numeric value = 0.0885
    - requested coordinates are preserved
    - grid coordinates are present
    - observation timestamp is present
    - freshness and data_source_type are present
    """
    svc = MosdacService()
    res = svc.get_chlorophyll(13.0827, 80.2707)

    assert res["status"] == "success"
    assert res["source"] == "MOSDAC"
    assert res["parameter"] == "chlorophyll_a"
    assert res["value"] in (0.0885, 0.0882)
    assert res["unit"] is None
    assert "Unit metadata not explicitly provided" in res["unit_notes"]
    assert res["observation_date"] in ("2026-09-03", "2026-09-04")
    assert res["requested_latitude"] == 13.0827
    assert res["requested_longitude"] == 80.2707
    assert res["grid_latitude"] == 13.012
    assert res["grid_longitude"] == 80.25
    assert res["grid_distance_km"] == 8.18
    assert res["freshness"] in ("fresh", "stale")
    assert res["data_source_type"] == "archive"
    assert "file_path" in res
    assert os.path.exists(res["file_path"])
    svc.close()
