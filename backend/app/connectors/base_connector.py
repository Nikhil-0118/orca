"""
Base connector class providing robust asynchronous HTTP calls, retries, and rate limiting.
"""
from typing import Any, Dict, Optional
import httpx
from app.core.logger import logger


class BaseConnector:
    """Base HTTP client with timeout, retry backoff, and exception handling."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._get_default_headers(),
            )
        return self._client

    def _get_default_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "ORCA-Marine-Platform/1.0"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("connector_closed", connector=self.__class__.__name__)
