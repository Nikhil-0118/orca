"""
ISRO Bhuvan Geoportal Client for Village Reverse Geocoding.

Approved API: Bhuvan Village Reverse Geocoding API
Endpoint: https://bhuvan-app1.nrsc.gov.in/api/api_proximity/curl_reverse_village.php
Method: GET
Parameters: lat, lon, token

Authoritative Rules:
1. BHUVAN_ACCESS_TOKEN is optional. If empty, the client returns None immediately.
2. The token is never logged, exposed to the frontend, or included in raw error messages.
3. Failures (HTTP 401 expired token, timeout, connection error, non-JSON response)
   are handled gracefully and return None without raising exceptions.
4. Operates as an optional enrichment layer; primary location resolution never depends on Bhuvan.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger("orca.services.bhuvan_client")

_BHUVAN_VRG_ENDPOINT = "https://bhuvan-app1.nrsc.gov.in/api/api_proximity/curl_reverse_village.php"
_REQUEST_TIMEOUT_SECONDS = 2.5
_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "ORCA-Marine-Platform/1.0 (sih-isro-prototype)",
}


class BhuvanClient:
    """Client for ISRO Bhuvan Village Reverse Geocoding API."""

    def __init__(self, timeout_seconds: float = _REQUEST_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds
        # In-memory spatial cache: key -> (timestamp, normalized_data)
        self._cache: Dict[str, Optional[Dict[str, Any]]] = {}

    def _cache_key(self, lat: float, lon: float) -> str:
        """Bucket coordinates to ~110m (3 decimal places) to cache duplicate queries."""
        return f"{round(lat, 3):.3f},{round(lon, 3):.3f}"

    def _get_token(self) -> str:
        """Read BHUVAN_ACCESS_TOKEN from settings."""
        return (getattr(settings, "BHUVAN_ACCESS_TOKEN", "") or "").strip()

    def _parse_response_data(self, data: Any, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Safely parse and normalize Bhuvan response payload.
        Handles list of records, single record, or 'False'/empty states.
        """
        if not data:
            return None

        # API returns "False" or boolean False when no village is matched
        if data is False or data == "False" or data == "false":
            return None

        record: Optional[Dict[str, Any]] = None
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                record = data[0]
        elif isinstance(data, dict):
            # Check for error responses
            if "error" in data or data.get("status") == "error":
                return None
            record = data

        if not record:
            return None

        village_name = (record.get("name1") or record.get("village_name") or "").strip()
        district_name = (record.get("dhq_name") or record.get("district_name") or "").strip()
        sub_district = (record.get("thq_name") or record.get("tehsil_name") or record.get("taluk_name") or "").strip()
        village_id = str(record.get("vid") or "").strip()

        # If no identifiable geographic name was returned, consider it unresolvable
        if not village_name and not district_name and not sub_district:
            return None

        # Parse optional census statistics if present
        census_data: Dict[str, Any] = {}
        for key, target in [
            ("no_hh", "households"),
            ("tot_p", "total_population"),
            ("tot_m", "male_population"),
            ("tot_f", "female_population"),
            ("m_lit", "male_literates"),
            ("f_lit", "female_literates"),
        ]:
            if key in record and record[key] is not None:
                try:
                    census_data[target] = int(str(record[key]).strip())
                except (ValueError, TypeError):
                    pass

        # Infer state from district / Census prefix when possible
        # In Bhuvan VRG, '28' prefix in 16-digit Census vid corresponds to Andhra Pradesh, '29' to Karnataka
        state: Optional[str] = None
        if village_id.startswith("28"):
            state = "Andhra Pradesh"
        elif village_id.startswith("29"):
            state = "Karnataka"

        normalized = {
            "village": village_name or None,
            "district": district_name or None,
            "sub_district": sub_district or None,
            "village_id": village_id or None,
            "state": state,
            "census_data": census_data if census_data else None,
            "source": "isro_bhuvan",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
        return normalized

    async def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Asynchronously reverse-geocode latitude and longitude using Bhuvan.
        Returns normalized village location dictionary or None on any failure/absence.
        """
        token = self._get_token()
        if not token:
            logger.debug("bhuvan_token_missing_skipping")
            return None

        cache_k = self._cache_key(lat, lon)
        if cache_k in self._cache:
            return self._cache[cache_k]

        params = {
            "lat": lat,
            "lon": lon,
            "token": token,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, verify=False) as client:
                resp = await client.get(_BHUVAN_VRG_ENDPOINT, params=params, headers=_HEADERS)

                if resp.status_code == 401:
                    logger.info("bhuvan_auth_401_expired_or_invalid_token")
                    self._cache[cache_k] = None
                    return None

                if resp.status_code != 200:
                    logger.info("bhuvan_http_status_non_200", extra={"status": resp.status_code})
                    self._cache[cache_k] = None
                    return None

                # Handle raw text or JSON response safely
                raw_text = resp.text.strip()
                if not raw_text or raw_text in ("False", "false", "null"):
                    self._cache[cache_k] = None
                    return None

                try:
                    data = resp.json()
                except (json.JSONDecodeError, ValueError):
                    logger.debug("bhuvan_non_json_payload_received")
                    self._cache[cache_k] = None
                    return None

                parsed = self._parse_response_data(data, lat, lon)
                self._cache[cache_k] = parsed
                return parsed

        except httpx.TimeoutException:
            logger.info("bhuvan_request_timeout")
            return None
        except Exception as exc:
            # Never include token in exception logs
            logger.info("bhuvan_request_error", extra={"error_type": type(exc).__name__})
            return None

    def reverse_geocode_sync(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Synchronously reverse-geocode latitude and longitude using Bhuvan.
        Returns normalized village location dictionary or None on any failure/absence.
        """
        token = self._get_token()
        if not token:
            return None

        cache_k = self._cache_key(lat, lon)
        if cache_k in self._cache:
            return self._cache[cache_k]

        params = {
            "lat": lat,
            "lon": lon,
            "token": token,
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds, verify=False) as client:
                resp = client.get(_BHUVAN_VRG_ENDPOINT, params=params, headers=_HEADERS)

                if resp.status_code == 401:
                    logger.info("bhuvan_auth_401_expired_or_invalid_token")
                    self._cache[cache_k] = None
                    return None

                if resp.status_code != 200:
                    self._cache[cache_k] = None
                    return None

                raw_text = resp.text.strip()
                if not raw_text or raw_text in ("False", "false", "null"):
                    self._cache[cache_k] = None
                    return None

                try:
                    data = resp.json()
                except (json.JSONDecodeError, ValueError):
                    self._cache[cache_k] = None
                    return None

                parsed = self._parse_response_data(data, lat, lon)
                self._cache[cache_k] = parsed
                return parsed

        except httpx.TimeoutException:
            return None
        except Exception as exc:
            logger.info("bhuvan_sync_request_error", extra={"error_type": type(exc).__name__})
            return None


# Global singleton client instance
bhuvan_client = BhuvanClient()
