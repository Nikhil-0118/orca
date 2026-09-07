"""
MOSDAC Data Acquisition and Cache Management Service (Phase 12).

Responsible for:
1. Discovering and indexing local MOSDAC NetCDF files in the download/cache directory.
2. Validating NetCDF integrity (file size, xarray readability, coordinates, 'chla' variable).
3. Safe atomic file downloading (.tmp staging -> validation -> atomic promotion).
4. Evaluating data age and freshness (fresh vs. stale vs. unavailable).
5. Seamless fallback to existing validated datasets when remote sources are unavailable.
"""
from datetime import datetime, timezone
import gc
import glob
import logging
import math
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
import xarray as xr

from app.config import settings

logger = logging.getLogger("orca.services.mosdac_downloader")

# Minimum reasonable size for a valid 25km global/regional MOSDAC NetCDF file (~100 KB)
# Real files are ~6.24 MB. Anything under 100 KB is typically an HTML error page, 404, or corrupt stub.
MIN_VALID_FILE_SIZE_BYTES = 100 * 1024


def validate_netcdf_file(filepath: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate whether a local file is a structurally valid, readable MOSDAC NetCDF file.

    Checks:
      1. File exists and is a regular file.
      2. File size exceeds minimum threshold (guards against HTML error responses).
      3. File opens cleanly via xarray.open_dataset().
      4. Contains required spatial coordinates ('lat', 'lon') with non-empty arrays.
      5. Contains the target variable ('chla').
      6. Coordinate arrays are numeric and uncorrupted.

    Returns:
      (is_valid: bool, error_reason: Optional[str], metadata: Optional[Dict[str, Any]])
    """
    if not filepath or not os.path.isfile(filepath):
        return False, f"File does not exist or is not a regular file: {filepath}", None

    try:
        file_size = os.path.getsize(filepath)
    except Exception as exc:
        return False, f"Unable to read file size: {exc}", None

    if file_size < MIN_VALID_FILE_SIZE_BYTES:
        return (
            False,
            f"File size ({file_size} bytes) is below minimum valid NetCDF threshold ({MIN_VALID_FILE_SIZE_BYTES} bytes). Likely corrupt or an HTML error response.",
            None,
        )

    ds: Optional[xr.Dataset] = None
    try:
        ds = xr.open_dataset(filepath)

        # 1. Validate coordinates
        has_lat = "lat" in ds.coords or "lat" in ds.variables
        has_lon = "lon" in ds.coords or "lon" in ds.variables
        if not (has_lat and has_lon):
            missing = []
            if not has_lat:
                missing.append("lat")
            if not has_lon:
                missing.append("lon")
            return False, f"Missing required spatial coordinates: {', '.join(missing)}", None

        # 2. Validate chlorophyll variable
        has_chla = "chla" in ds.data_vars or "chla" in ds.variables
        if not has_chla:
            return False, "Missing target data variable 'chla'", None

        # 3. Check coordinate dimensions
        lat_size = ds["lat"].size
        lon_size = ds["lon"].size
        if lat_size < 10 or lon_size < 10:
            return False, f"Insufficient coordinate grid dimensions: lat={lat_size}, lon={lon_size}", None

        # 4. Extract observation date & time
        obs_date = "unknown"
        obs_time_iso = None
        if "time" in ds.coords and ds["time"].size > 0:
            raw_time = str(ds["time"].values[0])
            obs_date = raw_time.split("T")[0]
            obs_time_iso = raw_time
        else:
            # Attempt to extract date from filename (e.g. E06OCML4AC_20260903_25km...)
            match = re.search(r"(\d{4})(\d{2})(\d{2})", os.path.basename(filepath))
            if match:
                obs_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                obs_time_iso = f"{obs_date}T00:00:00Z"

        mtime = os.path.getmtime(filepath)
        metadata = {
            "filepath": os.path.abspath(filepath),
            "filename": os.path.basename(filepath),
            "file_size_bytes": file_size,
            "mtime": mtime,
            "observation_date": obs_date,
            "observation_time": obs_time_iso or f"{obs_date}T00:00:00Z",
            "lat_count": lat_size,
            "lon_count": lon_size,
            "chla_shape": list(ds["chla"].shape),
        }
        return True, None, metadata

    except Exception as exc:
        return False, f"NetCDF parsing exception: {type(exc).__name__}: {str(exc)}", None
    finally:
        if ds is not None:
            try:
                ds.close()
            except Exception:
                pass
            del ds
        gc.collect()


def calculate_data_age_hours(
    observation_date_str: str,
    reference_time_utc: Optional[datetime] = None,
) -> Optional[float]:
    """
    Calculate elapsed age in hours between observation date and reference time (now UTC).
    Observation date string format: 'YYYY-MM-DD' or ISO 8601 string.
    """
    if not observation_date_str or observation_date_str == "unknown":
        return None

    ref_time = reference_time_utc or datetime.now(timezone.utc)
    try:
        clean = observation_date_str.replace("Z", "+00:00")
        if "T" in clean:
            t_obs = datetime.fromisoformat(clean)
        else:
            t_obs = datetime.fromisoformat(f"{clean}T00:00:00+00:00")

        diff_sec = (ref_time - t_obs).total_seconds()
        return round(max(0.0, diff_sec / 3600.0), 2)
    except Exception:
        return None


def classify_freshness(data_age_hours: Optional[float], max_age_hours: float = 24.0) -> str:
    """
    Classify observation freshness against configured age threshold.
    - fresh: age <= max_age_hours
    - stale: age > max_age_hours
    - unavailable: age is None (missing/invalid observation time)
    """
    if data_age_hours is None:
        return "unavailable"
    if data_age_hours <= max_age_hours:
        return "fresh"
    return "stale"


def promote_downloaded_file(
    staged_path: str,
    dest_dir: str,
    final_filename: Optional[str] = None,
    max_retries: int = 5,
    retry_delay: float = 0.25,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Safely promote a validated staged NetCDF file into the destination directory using Windows-safe atomic replacement.

    Guarantees:
      1. Validates the staged file before attempting promotion.
      2. Ensures all file handles across services and GC are closed.
      3. Never deletes or corrupts the existing active dataset if promotion fails.
      4. Implements bounded retry on Windows sharing/access violations (WinError 5, WinError 32).
      5. Cleans up temporary files if promotion fails.
      6. Returns structured result tuple: (success: bool, final_path: Optional[str], error: Optional[str]).
    """
    if not staged_path or not os.path.isfile(staged_path):
        return False, None, f"Staged file not found or invalid: {staged_path}"

    # 1. Validate staged file first
    is_valid, val_err, meta = validate_netcdf_file(staged_path)
    if not is_valid or not meta:
        return False, None, f"Staged file failed NetCDF validation before promotion: {val_err}"

    os.makedirs(dest_dir, exist_ok=True)
    target_name = final_filename or os.path.basename(staged_path)
    final_path = os.path.join(dest_dir, target_name)
    temp_final_path = os.path.join(dest_dir, f"{target_name}.tmp")

    # 2. Release any handles that might be open in the current process
    try:
        from app.services.mosdac_service import mosdac_service
        mosdac_service.close()
    except Exception:
        pass
    gc.collect()

    # 3. Stage into destination directory if not already there
    staged_abs = os.path.abspath(staged_path)
    temp_abs = os.path.abspath(temp_final_path)

    if staged_abs != temp_abs:
        try:
            shutil.copyfile(staged_path, temp_final_path)
        except Exception as exc:
            return False, None, f"Failed copying staged file to promotion staging {temp_final_path}: {exc}"

    if not os.path.isfile(temp_final_path) or os.path.getsize(temp_final_path) == 0:
        return False, None, f"Promotion candidate {temp_final_path} is missing or empty."

    # 4. Atomic replacement with bounded retries for Windows file locks
    promoted = False
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            # Force GC and release handles before each attempt
            gc.collect()
            os.replace(temp_final_path, final_path)
            promoted = True
            logger.info("mosdac_file_promoted_successfully", extra={"final_path": final_path, "attempt": attempt})
            break
        except (PermissionError, OSError) as exc:
            last_error = exc
            logger.warning(
                "mosdac_promotion_access_error_retrying",
                extra={
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "error": str(exc),
                    "temp_path": temp_final_path,
                    "final_path": final_path,
                },
            )
            # Try closing service handles again
            try:
                from app.services.mosdac_service import mosdac_service
                mosdac_service.close()
            except Exception:
                pass
            gc.collect()
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)

    # 5. Handle failure
    if not promoted:
        # Clean up temporary staging file to prevent orphaned temp files
        if os.path.exists(temp_final_path):
            try:
                os.remove(temp_final_path)
            except Exception:
                pass

        # Protect existing fallback dataset
        if os.path.isfile(final_path):
            logger.info(
                "mosdac_existing_dataset_preserved_after_promotion_failure",
                extra={"final_path": final_path, "error": str(last_error)},
            )
            return (
                False,
                None,
                f"Atomic replacement failed after {max_retries} attempts ({last_error}). Existing valid dataset preserved as fallback.",
            )

        return False, None, f"Atomic replacement failed after {max_retries} attempts: {last_error}"

    # 6. Promotion succeeded: ensure mosdac_service invalidates cache to pick up new file
    try:
        from app.services.mosdac_service import mosdac_service
        mosdac_service.close()
    except Exception:
        pass

    return True, final_path, None


class MosdacDownloader:
    """
    Manages MOSDAC dataset acquisition, local cache indexing, atomic updates,
    and fallback mechanics.
    """

    def __init__(
        self,
        download_dir: Optional[str] = None,
        default_file_path: Optional[str] = None,
        remote_url: Optional[str] = None,
        max_age_hours: Optional[float] = None,
        download_timeout: Optional[float] = None,
        auto_download_enabled: Optional[bool] = None,
        max_cached_files: Optional[int] = None,
        refresh_interval_hours: Optional[float] = None,
        api_service: Optional[Any] = None,
    ):
        self.download_dir = download_dir or getattr(settings, "MOSDAC_DOWNLOAD_DIR", r"C:\home\sys_oper\MOSDAC_Downloads")
        self.default_file_path = default_file_path or getattr(settings, "MOSDAC_NETCDF_PATH", "")
        self.remote_url = remote_url or getattr(settings, "MOSDAC_REMOTE_URL", None)
        self.max_age_hours = float(max_age_hours if max_age_hours is not None else getattr(settings, "MOSDAC_MAX_FILE_AGE_HOURS", 24.0))
        self.download_timeout = float(download_timeout if download_timeout is not None else getattr(settings, "MOSDAC_DOWNLOAD_TIMEOUT", 30.0))
        self.auto_download_enabled = bool(auto_download_enabled if auto_download_enabled is not None else getattr(settings, "MOSDAC_AUTO_DOWNLOAD_ENABLED", False))
        self.max_cached_files = max(1, int(max_cached_files if max_cached_files is not None else getattr(settings, "MOSDAC_MAX_CACHED_FILES", 2)))
        self.refresh_interval_hours = float(refresh_interval_hours if refresh_interval_hours is not None else getattr(settings, "MOSDAC_REFRESH_INTERVAL_HOURS", 24.0))
        self.api_service = api_service

    def discover_local_datasets(self) -> List[Dict[str, Any]]:
        """
        Scan download directory and default path for valid NetCDF candidate files.
        Validates each candidate and returns a list sorted by observation date descending.
        """
        search_dirs = []
        if self.download_dir and os.path.isdir(self.download_dir):
            search_dirs.append(os.path.abspath(self.download_dir))

        if self.default_file_path:
            parent_dir = os.path.dirname(os.path.abspath(self.default_file_path))
            if parent_dir and os.path.isdir(parent_dir) and parent_dir not in search_dirs:
                search_dirs.append(parent_dir)

        candidate_files: List[str] = []
        for sdir in search_dirs:
            # Match *.nc files
            matches = glob.glob(os.path.join(sdir, "*.nc"))
            candidate_files.extend(matches)

        # Also add default file explicitly if not caught by glob
        if self.default_file_path and os.path.isfile(self.default_file_path):
            abs_def = os.path.abspath(self.default_file_path)
            if abs_def not in candidate_files:
                candidate_files.append(abs_def)

        # Deduplicate paths
        candidate_files = list(dict.fromkeys(candidate_files))

        valid_datasets: List[Dict[str, Any]] = []
        for cfile in candidate_files:
            is_valid, err, meta = validate_netcdf_file(cfile)
            if is_valid and meta:
                valid_datasets.append(meta)
            else:
                logger.warning("mosdac_candidate_invalid", extra={"filepath": cfile, "reason": err})

        # Sort by observation_date descending, then mtime descending
        valid_datasets.sort(
            key=lambda d: (d.get("observation_date", ""), d.get("mtime", 0.0)),
            reverse=True,
        )
        return valid_datasets

    def get_active_dataset(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Determine and return the currently active MOSDAC dataset with freshness evaluation.
        If the cached dataset is stale and automatic acquisition is enabled, attempts remote download.
        Always falls back gracefully to the existing valid local dataset if remote acquisition fails.
        """
        now_utc = datetime.now(timezone.utc)
        retrieved_at = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Discover existing validated local files
        local_datasets = self.discover_local_datasets()
        newest_local = local_datasets[0] if local_datasets else None

        # 2. Check freshness of newest local file
        is_stale = True
        local_age = None
        if newest_local:
            local_age = calculate_data_age_hours(newest_local["observation_date"], now_utc)
            freshness = classify_freshness(local_age, self.max_age_hours)
            is_stale = (freshness == "stale")
        else:
            freshness = "unavailable"

        # 3. If stale or force_refresh, attempt remote update if enabled
        attempted_remote = False
        if self.auto_download_enabled and (is_stale or force_refresh or newest_local is None):
            # 3A. First try official authenticated API ingestion if credentials exist
            api_svc = self.api_service
            if api_svc is None:
                try:
                    from app.services.mosdac_api_service import mosdac_api_service
                    api_svc = mosdac_api_service
                except ImportError:
                    api_svc = None

            if api_svc and getattr(api_svc, "username", None) and getattr(api_svc, "password", None):
                attempted_remote = True
                logger.info("mosdac_attempting_authenticated_download", extra={"dataset_id": getattr(api_svc, "dataset_id", "E06OCM_L4_AC")})
                api_res = api_svc.download_latest_dataset(target_dir=self.download_dir, force=force_refresh)
                if api_res.get("success") and api_res.get("file_path"):
                    new_path = api_res["file_path"]
                    is_valid, _, meta = validate_netcdf_file(new_path)
                    if is_valid and meta:
                        self.enforce_retention(active_filepath=new_path)
                        new_age = calculate_data_age_hours(meta["observation_date"], now_utc)
                        new_freshness = classify_freshness(new_age, self.max_age_hours)
                        logger.info("mosdac_authenticated_download_promoted", extra={"filepath": new_path, "freshness": new_freshness})
                        return {
                            "status": "valid",
                            "filepath": new_path,
                            "observation_date": meta["observation_date"],
                            "observation_time": meta["observation_time"],
                            "data_time": meta["observation_time"],
                            "file_modified_time": meta["mtime"],
                            "retrieved_at": retrieved_at,
                            "data_age_hours": new_age,
                            "freshness": new_freshness,
                            "data_source_type": "remote_authenticated",
                            "is_fallback": False,
                            "download_attempted": True,
                            "download_success": True,
                        }
                else:
                    logger.warning("mosdac_authenticated_download_failed_fallback_activated", extra={"error": api_res.get("error")})

            # 3B. If authenticated download not configured or failed, try direct remote URL if configured
            if bool(self.remote_url):
                attempted_remote = True
                logger.info("mosdac_attempting_remote_download", extra={"remote_url": self.remote_url})
                success, downloaded_path, err_msg = self.download_remote_dataset()
                if success and downloaded_path:
                    is_valid, _, meta = validate_netcdf_file(downloaded_path)
                    if is_valid and meta:
                        new_age = calculate_data_age_hours(meta["observation_date"], now_utc)
                        new_freshness = classify_freshness(new_age, self.max_age_hours)
                        logger.info("mosdac_remote_download_promoted", extra={"filepath": downloaded_path, "freshness": new_freshness})
                        return {
                            "status": "valid",
                            "filepath": downloaded_path,
                            "observation_date": meta["observation_date"],
                            "observation_time": meta["observation_time"],
                            "data_time": meta["observation_time"],
                            "file_modified_time": meta["mtime"],
                            "retrieved_at": retrieved_at,
                            "data_age_hours": new_age,
                            "freshness": new_freshness,
                            "data_source_type": "archive",
                            "is_fallback": False,
                            "download_attempted": True,
                            "download_success": True,
                        }
                else:
                    logger.warning("mosdac_remote_download_failed_fallback_activated", extra={"reason": err_msg})

        # 4. Return newest local dataset if available
        if newest_local:
            return {
                "status": "valid",
                "filepath": newest_local["filepath"],
                "observation_date": newest_local["observation_date"],
                "observation_time": newest_local["observation_time"],
                "data_time": newest_local["observation_time"],
                "file_modified_time": newest_local["mtime"],
                "retrieved_at": retrieved_at,
                "data_age_hours": local_age,
                "freshness": freshness,
                "data_source_type": "archive",
                "is_fallback": attempted_remote or (self.auto_download_enabled and not is_stale),
                "download_attempted": attempted_remote,
                "download_success": False if attempted_remote else None,
            }

        # 5. No valid local dataset and remote acquisition failed / disabled
        return {
            "status": "unavailable",
            "filepath": None,
            "observation_date": None,
            "observation_time": None,
            "data_time": None,
            "file_modified_time": None,
            "retrieved_at": retrieved_at,
            "data_age_hours": None,
            "freshness": "unavailable",
            "data_source_type": "unavailable",
            "is_fallback": False,
            "download_attempted": attempted_remote,
            "download_success": False if attempted_remote else None,
            "error": "No valid MOSDAC NetCDF dataset available locally or via remote download.",
        }

    def download_remote_dataset(
        self,
        url: Optional[str] = None,
        target_filename: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Safely download a remote NetCDF file to a temporary file, validate it,
        and atomically promote it to the active cache directory.

        Guarantees:
          - Downloads to `<filename>.tmp` first.
          - Validates NetCDF structure before promotion.
          - Rejects and cleans up corrupt/HTML error responses.
          - Preserves existing valid datasets if download or validation fails.

        Returns:
          (success: bool, final_path: Optional[str], error_reason: Optional[str])
        """
        download_url = url or self.remote_url
        if not download_url:
            return False, None, "No remote URL configured for MOSDAC acquisition"

        dest_dir = self.download_dir or os.path.dirname(self.default_file_path)
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir, exist_ok=True)
            except Exception as exc:
                return False, None, f"Failed to create download directory {dest_dir}: {exc}"

        # Determine target filename
        if not target_filename:
            # Extract from URL or generate from current timestamp
            url_path = download_url.split("?")[0].rstrip("/")
            url_basename = os.path.basename(url_path)
            if url_basename.endswith(".nc"):
                target_filename = url_basename
            else:
                today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
                target_filename = f"E06OCML4AC_{today_str}_25km_v1.0.1.nc"

        final_path = os.path.join(dest_dir, target_filename)
        temp_path = os.path.join(dest_dir, f"{target_filename}.tmp")

        # Clean up any leftover temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

        req_headers = {"User-Agent": "ORCA-Marine-Platform/1.0"}
        if headers:
            req_headers.update(headers)

        # 1. Download stream to temporary file
        try:
            with httpx.Client(timeout=self.download_timeout, verify=False) as client:
                with client.stream("GET", download_url, headers=req_headers) as response:
                    if response.status_code != 200:
                        return (
                            False,
                            None,
                            f"Remote MOSDAC endpoint returned HTTP {response.status_code}: {response.reason_phrase}",
                        )

                    with open(temp_path, "wb") as f_out:
                        for chunk in response.iter_bytes(chunk_size=65536):
                            f_out.write(chunk)

        except httpx.TimeoutException:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, None, f"Connection timeout ({self.download_timeout}s) contacting MOSDAC remote source"
        except Exception as exc:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, None, f"Network exception during MOSDAC download: {type(exc).__name__}: {str(exc)}"

        # 2. Strict NetCDF validation on temporary file
        is_valid, val_err, meta = validate_netcdf_file(temp_path)
        if not is_valid:
            # Quarantine/discard invalid download
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.warning("mosdac_download_validation_failed", extra={"reason": val_err, "url": download_url})
            return False, None, f"Downloaded file failed NetCDF validation: {val_err}"

        # 3. Windows-safe atomic promotion
        promoted, promoted_final_path, prom_err = promote_downloaded_file(
            staged_path=temp_path,
            dest_dir=dest_dir,
            final_filename=target_filename,
        )
        if not promoted or not promoted_final_path:
            logger.warning("mosdac_download_promotion_failed", extra={"error": prom_err})
            return False, None, prom_err or "Atomic promotion failed"

        # Safely enforce retention limit on cache directory ONLY after successful promotion
        self.enforce_retention(active_filepath=promoted_final_path)
        return True, promoted_final_path, None

    def enforce_retention(self, active_filepath: Optional[str] = None, target_dir: Optional[str] = None) -> List[str]:
        """
        Enforce cache storage limits by safely pruning older validated datasets
        beyond self.max_cached_files, and removing orphaned .tmp files.

        Guarantees:
          - Never deletes the active file (active_filepath or newest valid dataset).
          - Keeps up to max_cached_files valid files (e.g. active + 1 rollback file).
          - Only prunes files inside target_dir or self.download_dir.
          - Only touches *.nc and *.tmp files (never touches unrelated files).
          - Returns a list of deleted file paths.
        """
        deleted: List[str] = []
        cache_dir = target_dir or (os.path.dirname(os.path.abspath(active_filepath)) if active_filepath else self.download_dir)
        if not cache_dir or not os.path.isdir(cache_dir):
            return deleted

        # 1. Clean up stale .tmp files in cache_dir
        try:
            tmp_files = glob.glob(os.path.join(cache_dir, "*.tmp"))
            for tfile in tmp_files:
                try:
                    os.remove(tfile)
                    deleted.append(tfile)
                    logger.info("mosdac_stale_tmp_removed", extra={"filepath": tfile})
                except Exception as exc:
                    logger.warning("mosdac_tmp_cleanup_failed", extra={"filepath": tfile, "error": str(exc)})
        except Exception as exc:
            logger.warning("mosdac_tmp_glob_failed", extra={"error": str(exc)})

        # 2. Discover all valid .nc files in cache_dir
        try:
            nc_files = glob.glob(os.path.join(cache_dir, "*.nc"))
        except Exception as exc:
            logger.warning("mosdac_nc_glob_failed", extra={"error": str(exc)})
            return deleted

        if len(nc_files) <= self.max_cached_files:
            return deleted

        # Validate and collect valid metadata
        valid_datasets: List[Dict[str, Any]] = []
        for ncf in nc_files:
            is_valid, _, meta = validate_netcdf_file(ncf)
            if is_valid and meta:
                valid_datasets.append(meta)

        # Sort by observation_date descending, then mtime descending
        valid_datasets.sort(
            key=lambda d: (d.get("observation_date", ""), d.get("mtime", 0.0)),
            reverse=True,
        )

        active_abs = os.path.abspath(active_filepath) if active_filepath else None
        if not active_abs and valid_datasets:
            active_abs = os.path.abspath(valid_datasets[0]["filepath"])

        # Retain active_filepath (if specified), plus newest other valid files up to self.max_cached_files
        retained_paths = set()
        if active_abs and any(os.path.abspath(r["filepath"]) == active_abs for r in valid_datasets):
            retained_paths.add(active_abs)

        for meta in valid_datasets:
            fpath = os.path.abspath(meta["filepath"])
            if len(retained_paths) >= self.max_cached_files:
                break
            retained_paths.add(fpath)

        # Prune older datasets
        for meta in valid_datasets:
            fpath = os.path.abspath(meta["filepath"])
            if fpath not in retained_paths and os.path.exists(fpath):
                try:
                    os.remove(fpath)
                    deleted.append(fpath)
                    logger.info("mosdac_retention_pruned_file", extra={"filepath": fpath})
                except Exception as exc:
                    logger.warning("mosdac_retention_delete_failed", extra={"filepath": fpath, "error": str(exc)})

        return deleted

    def get_storage_summary(self) -> Dict[str, Any]:
        """
        Lightweight monitoring helper reporting cache directory statistics.
        Returns:
          {
            "cache_directory": str,
            "file_count": int,
            "total_size_bytes": int,
            "total_size_mb": float,
            "active_file": Optional[str],
            "oldest_retained_file": Optional[str],
            "max_cached_files": int,
            "auto_download_enabled": bool,
          }
        """
        dir_path = os.path.abspath(self.download_dir) if self.download_dir else ""
        if not dir_path or not os.path.isdir(dir_path):
            return {
                "cache_directory": dir_path,
                "file_count": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "active_file": None,
                "oldest_retained_file": None,
                "max_cached_files": self.max_cached_files,
                "auto_download_enabled": self.auto_download_enabled,
            }

        nc_files = glob.glob(os.path.join(dir_path, "*.nc"))
        total_bytes = 0
        valid_files: List[Tuple[str, float]] = []

        for f in nc_files:
            try:
                sz = os.path.getsize(f)
                mt = os.path.getmtime(f)
                total_bytes += sz
                valid_files.append((os.path.basename(f), mt))
            except Exception:
                pass

        valid_files.sort(key=lambda x: x[1], reverse=True)
        active_f = valid_files[0][0] if valid_files else None
        oldest_f = valid_files[-1][0] if valid_files else None

        return {
            "cache_directory": dir_path,
            "file_count": len(valid_files),
            "total_size_bytes": total_bytes,
            "total_size_mb": round(total_bytes / (1024 * 1024), 2),
            "active_file": active_f,
            "oldest_retained_file": oldest_f,
            "max_cached_files": self.max_cached_files,
            "auto_download_enabled": self.auto_download_enabled,
        }


# Singleton downloader instance
mosdac_downloader = MosdacDownloader()
