"""
Phase 15 Test Suite — Authenticated MOSDAC Automatic Data Ingestion.

Verifies:
1. Missing credentials handling (no crash, structured fallback, no fake data)
2. Invalid credentials handling (401 handled, zero secrets leaked, local dataset preserved)
3. Successful mocked authenticated download (NetCDF validated, active dataset promoted)
4. Corrupted authenticated download (rejected by validation, staging pruned, fallback intact)
5. Dataset not available for date (structured fallback, local archive preserved)
6. Repeated query protection (refresh interval / cooldown prevents hammering)
7. Retention enforcement (MOSDAC_MAX_CACHED_FILES strictly respected)
8. Credential confidentiality (passwords/tokens never logged or returned)
9. EO Agent integration (Chennai chlorophyll extracted reliably)
10. End-to-end /api/query integration (multi-agent orchestration remains green)
"""
from datetime import datetime, timedelta, timezone
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.services.mosdac_api_service import (
    AUTH_FAILURE_COOLDOWN_SECONDS,
    MAX_CONSECUTIVE_AUTH_FAILURES,
    MosdacApiService,
    sanitize_sensitive_data,
)
from app.services.mosdac_downloader import (
    MosdacDownloader,
    calculate_data_age_hours,
    classify_freshness,
    promote_downloaded_file,
    validate_netcdf_file,
)
from app.services.mosdac_service import MosdacService

# Authoritative test NetCDF fixture
SAMPLE_VALID_NC = getattr(settings, "MOSDAC_NETCDF_PATH", r"C:\home\sys_oper\MOSDAC_Downloads\E06OCML4AC_20260903_25km_v1.0.1.nc")
CANARY_SECRET = "super_secret_canary_password_xyz123"


# ── TEST 1: Missing credentials ──────────────────────────────────────────────

def test_01_missing_credentials_handled_gracefully():
    """Verify missing username/password returns structured fallback without crashing."""
    service = MosdacApiService(
        username="",
        password="",
        auto_download_enabled=True,
    )
    res = service.download_latest_dataset()
    assert res["success"] is False
    assert res["data_source_type"] == "local_fallback"
    assert res["fallback_used"] is True
    assert "missing" in res["error"].lower() or "not configured" in res["error"].lower()


# ── TEST 2: Invalid credentials ──────────────────────────────────────────────

def test_02_invalid_credentials_handled_without_leaking_secrets():
    """Verify invalid credentials return 401 error, redact secrets, and preserve local cache."""
    service = MosdacApiService(
        username="test_user",
        password=CANARY_SECRET,
        auto_download_enabled=True,
    )

    # Mock execute_official_download to simulate a 401 response from MOSDAC
    with patch.object(
        service,
        "execute_official_download",
        return_value=(False, None, "MOSDAC authentication failed: Invalid username or password (HTTP 401)."),
    ):
        res = service.download_latest_dataset()

    assert res["success"] is False
    assert res["fallback_used"] is True
    assert "401" in res["error"]
    # Verify canary secret is strictly absent from error string
    assert CANARY_SECRET not in res["error"]
    assert CANARY_SECRET not in str(res)


# ── TEST 3: Successful mocked authenticated download ─────────────────────────

def test_03_successful_mocked_authenticated_download():
    """Verify successful download promotes validated NetCDF and updates active metadata."""
    temp_cache = tempfile.mkdtemp(prefix="orca_test_cache_")
    try:
        # Pre-seed with sample file as simulated download
        staged_copy = os.path.join(temp_cache, "E06OCML4AC_20260904_25km_v1.0.1.nc")
        shutil.copyfile(SAMPLE_VALID_NC, staged_copy)

        service = MosdacApiService(
            username="valid_user",
            password="valid_password",
            auto_download_enabled=True,
        )

        with patch.object(service, "execute_official_download", return_value=(True, staged_copy, None)):
            res = service.download_latest_dataset(target_dir=temp_cache, force=True)

        assert res["success"] is True
        assert res["data_source_type"] == "remote_authenticated"
        assert res["observation_date"] == "2026-09-03"
        assert res["fallback_used"] is False
        assert os.path.isfile(res["file_path"])
    finally:
        shutil.rmtree(temp_cache, ignore_errors=True)


# ── TEST 4: Corrupted authenticated download ─────────────────────────────────

def test_04_corrupted_authenticated_download_rejected():
    """Verify corrupted / truncated download is rejected, staging pruned, and old cache intact."""
    temp_cache = tempfile.mkdtemp(prefix="orca_test_corrupt_")
    try:
        # Existing valid dataset
        existing_file = os.path.join(temp_cache, "E06OCML4AC_20260901_25km_v1.0.1.nc")
        shutil.copyfile(SAMPLE_VALID_NC, existing_file)

        # Create a corrupt stub file (< 100 KB HTML error stub)
        corrupt_staged = os.path.join(temp_cache, "E06OCML4AC_20260904_25km_v1.0.1.nc.staged")
        with open(corrupt_staged, "w") as f:
            f.write("<html><body>500 Internal Server Error</body></html>")

        service = MosdacApiService(
            username="valid_user",
            password="valid_password",
            auto_download_enabled=True,
        )

        with patch.object(service, "execute_official_download", return_value=(True, corrupt_staged, None)):
            res = service.download_latest_dataset(target_dir=temp_cache, force=True)

        # Download validation must fail
        assert res["success"] is False
        assert res["fallback_used"] is True
        assert "validation failed" in res["error"].lower()

        # Existing dataset must remain safe and readable
        assert os.path.isfile(existing_file)
        is_valid, _, _ = validate_netcdf_file(existing_file)
        assert is_valid is True
    finally:
        shutil.rmtree(temp_cache, ignore_errors=True)


# ── TEST 5: Dataset not available for date ───────────────────────────────────

def test_05_dataset_unavailable_for_date_graceful_fallback():
    """Verify missing remote product for requested date gracefully falls back to local data."""
    temp_cache = tempfile.mkdtemp(prefix="orca_test_date_")
    try:
        local_nc = os.path.join(temp_cache, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        shutil.copyfile(SAMPLE_VALID_NC, local_nc)

        service = MosdacApiService(
            username="valid_user",
            password="valid_password",
            auto_download_enabled=True,
        )

        with patch.object(
            service,
            "execute_official_download",
            return_value=(False, None, "No matching datasets found for date range 2026-09-04"),
        ):
            res = service.download_latest_dataset(target_dir=temp_cache, force=True)

        assert res["success"] is False
        assert res["data_source_type"] == "local_fallback"
        assert res["fallback_used"] is True

        # Downloader returns local valid dataset
        downloader = MosdacDownloader(download_dir=temp_cache, api_service=service, auto_download_enabled=False)
        active = downloader.get_active_dataset()
        assert active["status"] == "valid"
        assert active["observation_date"] in ("2026-09-03", "2026-09-04")
    finally:
        shutil.rmtree(temp_cache, ignore_errors=True)


# ── TEST 6: Repeated query cooldown protection ──────────────────────────────

def test_06_repeated_query_respects_refresh_interval():
    """Verify refresh interval prevents hammering MOSDAC on consecutive queries."""
    service = MosdacApiService(
        username="valid_user",
        password="valid_password",
        auto_download_enabled=True,
        refresh_interval_hours=24.0,
    )

    # First attempt: simulated execution
    with patch.object(service, "execute_official_download", return_value=(False, None, "simulated_fail")):
        service.download_latest_dataset()

    # Second immediate attempt without force: should be deferred by cooldown
    can_attempt, reason = service.should_attempt_download(force=False)
    assert can_attempt is False
    assert "refresh interval not met" in reason.lower()


# ── TEST 7: Retention enforcement ────────────────────────────────────────────

def test_07_retention_enforces_max_cached_files():
    """Verify retention deletes older .nc files beyond max_cached_files and prunes .tmp files."""
    temp_cache = tempfile.mkdtemp(prefix="orca_test_retention_")
    try:
        # Create 4 mock .nc files with different dates
        file_paths = []
        for d in ["20260830", "20260831", "20260901", "20260902"]:
            p = os.path.join(temp_cache, f"E06OCML4AC_{d}_25km_v1.0.1.nc")
            shutil.copyfile(SAMPLE_VALID_NC, p)
            file_paths.append(p)

        # Create an orphan .tmp file
        orphan_tmp = os.path.join(temp_cache, "stale_upload.nc.tmp")
        with open(orphan_tmp, "w") as f:
            f.write("temporary junk")

        downloader = MosdacDownloader(
            download_dir=temp_cache,
            max_cached_files=2,
        )

        # Active file is the newest: 20260902
        active_p = file_paths[-1]
        deleted = downloader.enforce_retention(active_filepath=active_p)

        # Pruned orphan tmp + oldest 2 .nc files
        assert orphan_tmp in deleted
        assert not os.path.exists(orphan_tmp)

        remaining_nc = [f for f in os.listdir(temp_cache) if f.endswith(".nc")]
        assert len(remaining_nc) <= 2
        # The active file must never be deleted
        assert os.path.basename(active_p) in remaining_nc
    finally:
        shutil.rmtree(temp_cache, ignore_errors=True)


# ── TEST 8: Credentials confidentiality ─────────────────────────────────────

def test_08_credentials_never_appear_in_sanitized_strings():
    """Verify sanitizer redacts canary password from text, JSON, and headers."""
    dirty_text = f"Error: Failed authentication for password={CANARY_SECRET} with token=Bearer abc123def456"
    cleaned = sanitize_sensitive_data(dirty_text, [CANARY_SECRET])

    assert CANARY_SECRET not in cleaned
    assert "[REDACTED]" in cleaned

    # Test JSON structure sanitization
    json_str = f'{{"username": "sailor", "password": "{CANARY_SECRET}", "access_token": "secret_token_789"}}'
    cleaned_json = sanitize_sensitive_data(json_str, [CANARY_SECRET])
    assert CANARY_SECRET not in cleaned_json
    assert "secret_token_789" not in cleaned_json


# ── TEST 9: EO Agent Chennai extraction ──────────────────────────────────────

def test_09_eo_agent_chennai_chlorophyll_extraction():
    """Verify EO Agent extracts Chennai chlorophyll correctly using MosdacService."""
    service = MosdacService(filepath=SAMPLE_VALID_NC)
    res = service.get_chlorophyll(13.0827, 80.2707)

    assert res["status"] == "success"
    assert res["source"] == "MOSDAC"
    assert res["parameter"] == "chlorophyll_a"
    assert res["value"] == 0.0885
    assert res["unit"] is None  # Preserved truthfully
    assert res["observation_date"] == "2026-09-03"
    assert res["grid_distance_km"] is not None
    assert res["grid_distance_km"] < 15.0


# ── TEST 10: Complete /api/query integration ────────────────────────────────

@pytest.mark.asyncio
async def test_10_full_api_query_with_mosdac():
    """Verify complete /api/query endpoint responds with MOSDAC chlorophyll data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/query",
            json={
                "query": "Give me chlorophyll data near Chennai",
                "location": {"lat": 13.0827, "lon": 80.2707},
                "session_id": "test-p15-t10",
            },
        )
        assert response.status_code == 200
        data = response.json()

        answer = data.get("answer", "")
        evidence = data.get("evidence", [])

        assert any("0.0885" in e or "MOSDAC" in e for e in evidence)
        assert "0.0885" in answer or "chlorophyll" in answer.lower()
        # Verify unit is never falsely claimed as mg/m³
        assert "mg/m³" not in answer or "MOSDAC" not in answer


# ── TEST 11: Phase 15.1 — Successful Windows-safe promotion ──────────────────

def test_11_successful_windows_safe_promotion():
    """Verify valid staged file promotes atomically into destination directory."""
    temp_dir = tempfile.mkdtemp(prefix="orca_test_p15_1_prom_")
    try:
        dest_dir = os.path.join(temp_dir, "dest")
        staging_dir = os.path.join(temp_dir, "staging")
        os.makedirs(dest_dir, exist_ok=True)
        os.makedirs(staging_dir, exist_ok=True)

        staged_file = os.path.join(staging_dir, "E06OCML4AC_20260904_25km_v1.0.1.nc")
        shutil.copyfile(SAMPLE_VALID_NC, staged_file)

        success, promoted_path, err = promote_downloaded_file(
            staged_path=staged_file,
            dest_dir=dest_dir,
        )

        assert success is True
        assert err is None
        assert promoted_path is not None
        assert os.path.isfile(promoted_path)
        assert os.path.basename(promoted_path) == "E06OCML4AC_20260904_25km_v1.0.1.nc"
        # Verify temporary file is cleaned up
        temp_file = os.path.join(dest_dir, "E06OCML4AC_20260904_25km_v1.0.1.nc.tmp")
        assert not os.path.exists(temp_file)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── TEST 12: Phase 15.1 — Validation failure prevents promotion ──────────────

def test_12_validation_failure_prevents_promotion():
    """Verify invalid staged file is rejected by validation and not promoted."""
    temp_dir = tempfile.mkdtemp(prefix="orca_test_p15_1_valfail_")
    try:
        dest_dir = os.path.join(temp_dir, "dest")
        staging_dir = os.path.join(temp_dir, "staging")
        os.makedirs(dest_dir, exist_ok=True)
        os.makedirs(staging_dir, exist_ok=True)

        # Pre-seed destination with valid file
        existing_active = os.path.join(dest_dir, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        shutil.copyfile(SAMPLE_VALID_NC, existing_active)
        orig_size = os.path.getsize(existing_active)

        # Create corrupt staged file
        corrupt_staged = os.path.join(staging_dir, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        with open(corrupt_staged, "w") as f:
            f.write("<html><body>HTML error page 500</body></html>")

        success, promoted_path, err = promote_downloaded_file(
            staged_path=corrupt_staged,
            dest_dir=dest_dir,
        )

        assert success is False
        assert promoted_path is None
        assert "validation" in err.lower()
        # Existing active dataset must be preserved
        assert os.path.isfile(existing_active)
        assert os.path.getsize(existing_active) == orig_size
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── TEST 13: Phase 15.1 — Promotion failure with bounded retries & fallback ─

def test_13_promotion_permission_error_bounded_retries_and_fallback():
    """Verify WinError 5 PermissionError triggers bounded retries and falls back cleanly."""
    temp_dir = tempfile.mkdtemp(prefix="orca_test_p15_1_lock_")
    try:
        dest_dir = os.path.join(temp_dir, "dest")
        staging_dir = os.path.join(temp_dir, "staging")
        os.makedirs(dest_dir, exist_ok=True)
        os.makedirs(staging_dir, exist_ok=True)

        # Pre-seed destination with valid file
        existing_active = os.path.join(dest_dir, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        shutil.copyfile(SAMPLE_VALID_NC, existing_active)
        orig_size = os.path.getsize(existing_active)

        staged_file = os.path.join(staging_dir, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        shutil.copyfile(SAMPLE_VALID_NC, staged_file)

        # Simulate Windows WinError 5 access denied on os.replace
        replace_attempts = []

        def mock_replace(src, dst):
            replace_attempts.append((src, dst))
            raise PermissionError(5, "Access is denied: Windows file lock")

        with patch("os.replace", side_effect=mock_replace):
            success, promoted_path, err = promote_downloaded_file(
                staged_path=staged_file,
                dest_dir=dest_dir,
                max_retries=3,
                retry_delay=0.01,
            )

        assert success is False
        assert promoted_path is None
        assert len(replace_attempts) == 3  # Exact bounded retries
        assert "access is denied" in err.lower()
        assert "preserved" in err.lower()
        # Existing valid dataset must still be intact on disk
        assert os.path.isfile(existing_active)
        assert os.path.getsize(existing_active) == orig_size

        # Also verify download_latest_dataset() handles promotion failure gracefully
        service = MosdacApiService(
            username="test_user",
            password="test_password",
            auto_download_enabled=True,
        )
        with patch.object(service, "execute_official_download", return_value=(True, staged_file, None)), \
             patch("os.replace", side_effect=mock_replace):
            res = service.download_latest_dataset(target_dir=dest_dir, force=True)

        assert res["success"] is False
        assert res["fallback_used"] is True
        assert res["data_source_type"] == "local_fallback"
        assert "failed" in res["error"].lower()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── TEST 14: Phase 15.1 — Resource closure before promotion ─────────────────

def test_14_resource_closure_releases_file_handles():
    """Verify validate_netcdf_file and MosdacService do not leave file handles locked."""
    temp_dir = tempfile.mkdtemp(prefix="orca_test_p15_1_handles_")
    try:
        test_file = os.path.join(temp_dir, "test_resource.nc")
        shutil.copyfile(SAMPLE_VALID_NC, test_file)

        # 1. Validation opens and closes immediately
        is_valid, err, meta = validate_netcdf_file(test_file)
        assert is_valid is True

        # Immediately attempt renaming/replacing the validated file: should succeed without lock
        renamed = os.path.join(temp_dir, "test_resource_renamed.nc")
        os.replace(test_file, renamed)
        assert os.path.isfile(renamed)
        assert not os.path.exists(test_file)

        # 2. MosdacService load_dataset closes handle immediately
        svc = MosdacService(filepath=renamed)
        loaded = svc.load_dataset()
        assert loaded is True

        # Verify we can replace/rewrite renamed file even while svc is loaded
        temp_replacement = os.path.join(temp_dir, "replacement.nc.tmp")
        shutil.copyfile(renamed, temp_replacement)
        os.replace(temp_replacement, renamed)
        assert os.path.isfile(renamed)

        # Service still produces chlorophyll from memory
        chla_res = svc.get_chlorophyll(13.0827, 80.2707)
        assert chla_res["status"] == "success"
        assert chla_res["value"] == 0.0885
        svc.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── TEST 15: Phase 15.1 — Same filename download handles replacement safely ─

def test_15_same_filename_download_preserves_active_on_failure():
    """Verify same-filename downloads do not corrupt existing file when promotion fails."""
    temp_dir = tempfile.mkdtemp(prefix="orca_test_p15_1_same_")
    try:
        dest_dir = os.path.join(temp_dir, "dest")
        staging_dir = os.path.join(temp_dir, "staging")
        os.makedirs(dest_dir, exist_ok=True)
        os.makedirs(staging_dir, exist_ok=True)

        filename = "E06OCML4AC_20260903_25km_v1.0.1.nc"
        active_path = os.path.join(dest_dir, filename)
        staged_path = os.path.join(staging_dir, filename)

        shutil.copyfile(SAMPLE_VALID_NC, active_path)
        shutil.copyfile(SAMPLE_VALID_NC, staged_path)

        # Promotion fails due to PermissionError
        with patch("os.replace", side_effect=PermissionError(5, "Access is denied")):
            success, promoted, err = promote_downloaded_file(
                staged_path=staged_path,
                dest_dir=dest_dir,
                max_retries=2,
                retry_delay=0.01,
            )

        assert success is False
        assert os.path.isfile(active_path)
        # Active file was preserved without corruption
        is_valid, _, _ = validate_netcdf_file(active_path)
        assert is_valid is True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── TEST 16: Phase 15.1 — Retention executed only after successful promotion ─

def test_16_retention_executed_only_after_successful_promotion():
    """Verify retention policy is not triggered if promotion fails, but runs on success."""
    temp_dir = tempfile.mkdtemp(prefix="orca_test_p15_1_ret_")
    try:
        dest_dir = os.path.join(temp_dir, "dest")
        staging_dir = os.path.join(temp_dir, "staging")
        os.makedirs(dest_dir, exist_ok=True)
        os.makedirs(staging_dir, exist_ok=True)

        # Create 3 older valid files
        f1 = os.path.join(dest_dir, "E06OCML4AC_20260901_25km_v1.0.1.nc")
        f2 = os.path.join(dest_dir, "E06OCML4AC_20260902_25km_v1.0.1.nc")
        f3 = os.path.join(dest_dir, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        for f in [f1, f2, f3]:
            shutil.copyfile(SAMPLE_VALID_NC, f)

        # Staged new file
        staged = os.path.join(staging_dir, "E06OCML4AC_20260904_25km_v1.0.1.nc")
        shutil.copyfile(SAMPLE_VALID_NC, staged)

        service = MosdacApiService(
            username="user",
            password="pwd",
            auto_download_enabled=True,
        )

        # 1. Failed promotion: retention must NOT be applied to prune existing files
        with patch.object(service, "execute_official_download", return_value=(True, staged, None)), \
             patch("app.services.mosdac_downloader.promote_downloaded_file", return_value=(False, None, "Locked")):
            res = service.download_latest_dataset(target_dir=dest_dir, force=True)

        assert res["success"] is False
        assert os.path.isfile(f1)
        assert os.path.isfile(f2)
        assert os.path.isfile(f3)

        # 2. Successful promotion: retention must prune down to max_cached_files (2)
        with patch.object(service, "execute_official_download", return_value=(True, staged, None)):
            res = service.download_latest_dataset(target_dir=dest_dir, force=True)

        assert res["success"] is True
        nc_remaining = [p for p in os.listdir(dest_dir) if p.endswith(".nc")]
        assert len(nc_remaining) <= 2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

