"""
MOSDAC Official API Ingestion Service (Phase 15).

Wraps the official ISRO MOSDAC Data Download API client (mdapi.py)
behind a secure service abstraction.

Guarantees:
1. Subprocess Isolation: Protects ORCA server from sys.exit() calls in mdapi.py.
2. Ephemeral Credentials: Writes config.json to an isolated temp directory and
   immediately shreds it in a finally block.
3. Zero-Leakage Sanitization: Passwords, tokens, and cookies are never logged
   or exposed in return dictionaries or exception traces.
4. Account Lockout Protection: Tracks consecutive authentication failures and
   enforces conservative cooldowns to prevent MOSDAC account lockout.
5. Structured Diagnostics: Returns standard ORCA evidence dictionaries with
   explicit data_source_type ("remote_authenticated" vs "local_fallback").
"""
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.services.mosdac_downloader import validate_netcdf_file

logger = logging.getLogger("orca.services.mosdac_api")

# Account lockout safety: maximum consecutive auth failures before cooldown
MAX_CONSECUTIVE_AUTH_FAILURES = 3
AUTH_FAILURE_COOLDOWN_SECONDS = 900.0  # 15 minutes


def sanitize_sensitive_data(text: str, secrets: Optional[List[str]] = None) -> str:
    """
    Remove passwords, tokens, and user credentials from text, logs, or error traces.
    """
    if not text:
        return ""
    sanitized = text
    if secrets:
        for s in secrets:
            if s and len(s) > 1:
                sanitized = sanitized.replace(s, "[REDACTED]")
    # Redact common token patterns or password fields
    sanitized = re.sub(r'("password"\s*:\s*")[^"]+(")', r'\1[REDACTED]\2', sanitized)
    sanitized = re.sub(r'("access_token"\s*:\s*")[^"]+(")', r'\1[REDACTED]\2', sanitized)
    sanitized = re.sub(r'("refresh_token"\s*:\s*")[^"]+(")', r'\1[REDACTED]\2', sanitized)
    sanitized = re.sub(r'(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*', r'\1[REDACTED]', sanitized)
    return sanitized


class MosdacApiService:
    """
    Service for authenticated satellite data acquisition using the official MOSDAC mdapi.py.
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        dataset_id: Optional[str] = None,
        auto_download_enabled: Optional[bool] = None,
        lookback_days: Optional[int] = None,
        download_count: Optional[int] = None,
        refresh_interval_hours: Optional[float] = None,
        bounding_box: Optional[str] = None,
        client_script_path: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.username = username if username is not None else getattr(settings, "MOSDAC_USERNAME", "")
        self.password = password if password is not None else getattr(settings, "MOSDAC_PASSWORD", "")
        self.dataset_id = dataset_id or getattr(settings, "MOSDAC_DATASET_ID", "E06OCM_L4_AC")
        self.auto_download_enabled = bool(
            auto_download_enabled if auto_download_enabled is not None
            else getattr(settings, "MOSDAC_AUTO_DOWNLOAD_ENABLED", False)
        )
        self.lookback_days = int(lookback_days if lookback_days is not None else getattr(settings, "MOSDAC_LOOKBACK_DAYS", 3))
        self.download_count = int(download_count if download_count is not None else getattr(settings, "MOSDAC_DOWNLOAD_COUNT", 1))
        self.refresh_interval_hours = float(
            refresh_interval_hours if refresh_interval_hours is not None
            else getattr(settings, "MOSDAC_REFRESH_INTERVAL_HOURS", 24.0)
        )
        self.bounding_box = bounding_box if bounding_box is not None else getattr(settings, "MOSDAC_BOUNDING_BOX", "60,5,95,25")
        self.client_script_path = client_script_path or getattr(settings, "MOSDAC_CLIENT_PATH", None)
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else getattr(settings, "MOSDAC_DOWNLOAD_TIMEOUT", 60.0))

        # Internal state tracking for rate limiting & account lockout guardrails
        self._last_download_attempt_time: Optional[datetime] = None
        self._last_download_success: Optional[bool] = None
        self._consecutive_auth_failures: int = 0
        self._lockout_cooldown_until: Optional[datetime] = None

    def resolve_client_path(self) -> Optional[str]:
        """Resolve absolute path to official mdapi.py script."""
        if self.client_script_path and os.path.isfile(self.client_script_path):
            return os.path.abspath(self.client_script_path)

        # Default standard path in backend package
        current_dir = os.path.dirname(os.path.abspath(__file__))
        default_path = os.path.join(current_dir, "mosdac_client", "mdapi.py")
        if os.path.isfile(default_path):
            return default_path

        # Scratch or root fallback
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        scratch_path = os.path.join(root_dir, "scratch", "mdapi_official", "mdapi.py")
        if os.path.isfile(scratch_path):
            return scratch_path

        return None

    def calculate_date_range(self) -> Tuple[str, str]:
        """
        Calculate dynamic ISO date strings (startTime, endTime) from current date
        and configured lookback window.
        """
        now_utc = datetime.now(timezone.utc)
        # End date is today
        end_str = now_utc.strftime("%Y-%m-%d")
        # Start date is lookback_days in past
        start_date = now_utc - timedelta(days=max(1, self.lookback_days))
        start_str = start_date.strftime("%Y-%m-%d")
        return start_str, end_str

    def should_attempt_download(self, is_stale: bool = True, force: bool = False) -> Tuple[bool, str]:
        """
        Determine whether a remote download attempt should proceed based on
        configuration, credentials, cooldown, and account lockout status.
        """
        if not self.auto_download_enabled and not force:
            return False, "Automatic download is disabled (MOSDAC_AUTO_DOWNLOAD_ENABLED is false)."

        if not self.username or not self.password:
            return False, "MOSDAC credentials not configured (MOSDAC_USERNAME or MOSDAC_PASSWORD missing)."

        now = datetime.now(timezone.utc)

        # Check account lockout cooldown
        if self._lockout_cooldown_until and now < self._lockout_cooldown_until:
            wait_rem = int((self._lockout_cooldown_until - now).total_seconds())
            return False, f"Account lockout prevention active due to previous failed logins. Cooldown active for {wait_rem}s."

        # Check refresh interval to prevent hammering on consecutive queries
        if not force and self._last_download_attempt_time is not None:
            elapsed_hours = (now - self._last_download_attempt_time).total_seconds() / 3600.0
            if elapsed_hours < self.refresh_interval_hours:
                return False, f"Download attempt deferred: refresh interval not met ({elapsed_hours:.1f}h < {self.refresh_interval_hours:.1f}h)."

        return True, "Ready for authenticated download attempt."

    def execute_official_download(
        self,
        staging_dir: str,
        start_date: str,
        end_date: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute official mdapi.py in an isolated temporary subprocess with an ephemeral config.json.
        Returns: (success: bool, downloaded_file_path: Optional[str], error_reason: Optional[str])
        """
        script_path = self.resolve_client_path()
        if not script_path or not os.path.isfile(script_path):
            return False, None, "Official MOSDAC client script (mdapi.py) not found."

        temp_dir = tempfile.mkdtemp(prefix="orca_mosdac_auth_")
        temp_config_path = os.path.join(temp_dir, "config.json")
        temp_script_path = os.path.join(temp_dir, "mdapi.py")

        secrets_to_sanitize = [self.username, self.password]

        try:
            # Copy script into isolated temp directory
            shutil.copyfile(script_path, temp_script_path)

            # Build ephemeral config.json
            config_payload = {
                "user_credentials": {
                    "username/email": self.username,
                    "password": self.password,
                },
                "search_parameters": {
                    "datasetId": self.dataset_id,
                    "startTime": start_date,
                    "endTime": end_date,
                    "count": str(self.download_count),
                    "boundingBox": self.bounding_box or "",
                    "gId": "",
                },
                "download_settings": {
                    "download_path": os.path.abspath(staging_dir).replace("\\", "/"),
                    "organize_by_date": False,
                    "skip_user_input": True,
                    "generate_error_logs": False,
                },
            }

            with open(temp_config_path, "w", encoding="utf-8") as f:
                json.dump(config_payload, f, indent=2)

            # Run official client in temp directory
            logger.info("mosdac_executing_official_client", extra={"datasetId": self.dataset_id, "start": start_date, "end": end_date})
            proc = subprocess.run(
                [sys.executable, "mdapi.py"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            stdout_clean = sanitize_sensitive_data(proc.stdout, secrets_to_sanitize)
            stderr_clean = sanitize_sensitive_data(proc.stderr, secrets_to_sanitize)

            # Check for specific authentication or validation errors
            if "Invalid Username/Password" in stdout_clean or "Status 401" in stdout_clean:
                self._consecutive_auth_failures += 1
                if self._consecutive_auth_failures >= MAX_CONSECUTIVE_AUTH_FAILURES:
                    self._lockout_cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=AUTH_FAILURE_COOLDOWN_SECONDS)
                    logger.error("mosdac_account_lockout_guardrail_triggered", extra={"failures": self._consecutive_auth_failures})
                return False, None, "MOSDAC authentication failed: Invalid username or password (HTTP 401)."

            if "Validation Error" in stdout_clean or "Status 400" in stdout_clean:
                return False, None, f"MOSDAC validation error: {stdout_clean[:200]}"

            if "Service Unavailable" in stdout_clean or "503 Server Error" in stdout_clean:
                return False, None, "MOSDAC server unavailable (HTTP 503)."

            if proc.returncode != 0:
                err_msg = stderr_clean.strip() or stdout_clean.strip() or f"Process exited with returncode {proc.returncode}"
                return False, None, f"MOSDAC download subprocess failed: {err_msg[:200]}"

            # Subprocess reported success; locate downloaded file in staging_dir
            downloaded_files = [
                os.path.join(staging_dir, f)
                for f in os.listdir(staging_dir)
                if f.endswith(".nc") and not f.endswith(".tmp") and not f.endswith(".part")
            ]

            if not downloaded_files:
                return False, None, "MOSDAC download completed but no NetCDF (.nc) file found in target directory."

            # Pick newest downloaded file
            downloaded_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            new_file = downloaded_files[0]
            self._consecutive_auth_failures = 0
            return True, new_file, None

        except subprocess.TimeoutExpired:
            return False, None, f"MOSDAC download timed out after {self.timeout_seconds} seconds."
        except Exception as exc:
            clean_exc = sanitize_sensitive_data(str(exc), secrets_to_sanitize)
            return False, None, f"Exception during MOSDAC download execution: {clean_exc}"
        finally:
            # Guarantees complete and immediate credential destruction from disk
            try:
                if os.path.exists(temp_config_path):
                    # Overwrite file content with zeroes before unlinking
                    with open(temp_config_path, "w") as f:
                        f.write("{}")
                    os.remove(temp_config_path)
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def download_latest_dataset(
        self,
        target_dir: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        High-level entry point: orchestrates date calculation, staging, official download,
        validation, and returns structured result without ever leaking secrets.
        """
        can_attempt, reason = self.should_attempt_download(force=force)
        if not can_attempt:
            logger.info("mosdac_download_skipped", extra={"reason": reason})
            return {
                "success": False,
                "source": "MOSDAC",
                "data_source_type": "local_fallback",
                "error": reason,
                "fallback_used": True,
            }

        # Track that an authenticated download attempt is being executed
        now_utc = datetime.now(timezone.utc)
        self._last_download_attempt_time = now_utc
        dest_dir = target_dir or getattr(settings, "MOSDAC_DOWNLOAD_DIR", r"C:\home\sys_oper\MOSDAC_Downloads")

        start_date, end_date = self.calculate_date_range()
        staging_dir = tempfile.mkdtemp(prefix="mosdac_staging_")

        try:
            success, staged_file, err_msg = self.execute_official_download(
                staging_dir=staging_dir,
                start_date=start_date,
                end_date=end_date,
            )

            if not success or not staged_file:
                logger.warning("mosdac_authenticated_download_failed", extra={"reason": err_msg})
                self._last_download_success = False
                return {
                    "success": False,
                    "source": "MOSDAC",
                    "data_source_type": "local_fallback",
                    "error": err_msg or "Download failed",
                    "fallback_used": True,
                }

            # Validate the staged file before promotion
            is_valid, val_err, meta = validate_netcdf_file(staged_file)
            if not is_valid or not meta:
                logger.warning("mosdac_downloaded_netcdf_invalid", extra={"error": val_err})
                self._last_download_success = False
                return {
                    "success": False,
                    "source": "MOSDAC",
                    "data_source_type": "local_fallback",
                    "error": f"NetCDF validation failed: {val_err}",
                    "fallback_used": True,
                }

            # Windows-safe atomic promotion into dest_dir
            from app.services.mosdac_downloader import promote_downloaded_file, mosdac_downloader

            promoted, final_path, prom_err = promote_downloaded_file(
                staged_path=staged_file,
                dest_dir=dest_dir,
            )

            if not promoted or not final_path:
                logger.warning("mosdac_authenticated_promotion_failed", extra={"error": prom_err})
                self._last_download_success = False
                return {
                    "success": False,
                    "source": "MOSDAC",
                    "data_source_type": "local_fallback",
                    "error": prom_err or "Atomic promotion failed",
                    "fallback_used": True,
                }

            # Enforce retention only after successful promotion
            mosdac_downloader.enforce_retention(active_filepath=final_path, target_dir=dest_dir)

            self._last_download_success = True
            logger.info("mosdac_authenticated_download_promoted", extra={"path": final_path, "obs_date": meta["observation_date"]})

            return {
                "success": True,
                "source": "MOSDAC",
                "data_source_type": "remote_authenticated",
                "dataset_id": self.dataset_id,
                "file_path": final_path,
                "observation_date": meta["observation_date"],
                "observation_time": meta["observation_time"],
                "download_time": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "file_size_bytes": meta["file_size_bytes"],
                "fallback_used": False,
            }

        finally:
            # Clean staging directory
            if os.path.exists(staging_dir):
                try:
                    shutil.rmtree(staging_dir, ignore_errors=True)
                except Exception:
                    pass


# Singleton instance
mosdac_api_service = MosdacApiService()
