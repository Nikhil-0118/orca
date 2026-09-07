"""
ORCA Replaceable LLM Provider Abstraction.

Supports Google Gemini, OpenAI-compatible (OpenAI, Groq, Ollama, OpenRouter), and Anthropic.
Handles timeouts, credentials, system instructions, and error isolation without exposing secrets.
"""
from abc import ABC, abstractmethod
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger("orca.services.llm")


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers in ORCA."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, timeout: float = 12.0):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_payload: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        """
        Generate completion from LLM.
        Returns generated text on success, or None on failure/timeout.
        """
        pass


class GoogleGeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider using direct REST API."""

    async def generate(
        self,
        system_prompt: str,
        user_payload: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        if not self.api_key:
            return None

        # Clean model name if passed with 'models/' prefix
        model_name = self.model.replace("models/", "")
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

        body = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_payload}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            logger.info("llm_request_started", extra={"provider": "google", "model": model_name})
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    endpoint,
                    params={"key": self.api_key},
                    json=body,
                    headers={"Content-Type": "application/json"},
                )

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates") or []
                    if candidates:
                        content = candidates[0].get("content") or {}
                        parts = content.get("parts") or []
                        if parts:
                            text = parts[0].get("text", "").strip()
                            logger.info("llm_response_completed", extra={"provider": "google", "chars": len(text)})
                            return text
                    logger.warning("llm_empty_response", extra={"provider": "google", "response": data})
                    return None
                else:
                    logger.warning(
                        "llm_request_failed",
                        extra={"provider": "google", "status_code": resp.status_code, "detail": resp.text[:200]},
                    )
                    return None
        except Exception as e:
            logger.warning("llm_exception", extra={"provider": "google", "error_type": type(e).__name__})
            return None


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI-compatible LLM provider (OpenAI, Groq, Ollama, OpenRouter, vLLM)."""

    async def generate(
        self,
        system_prompt: str,
        user_payload: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        if not self.api_key:
            return None

        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        endpoint = f"{base}/chat/completions"

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            logger.info("llm_request_started", extra={"provider": "openai_compatible", "model": self.model})
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=body, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices") or []
                    if choices:
                        message = choices[0].get("message") or {}
                        text = message.get("content", "").strip()
                        logger.info("llm_response_completed", extra={"provider": "openai_compatible", "chars": len(text)})
                        return text
                    return None
                else:
                    logger.warning(
                        "llm_request_failed",
                        extra={"provider": "openai_compatible", "status_code": resp.status_code, "detail": resp.text[:200]},
                    )
                    return None
        except Exception as e:
            logger.warning("llm_exception", extra={"provider": "openai_compatible", "error_type": type(e).__name__})
            return None


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider."""

    async def generate(
        self,
        system_prompt: str,
        user_payload: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        if not self.api_key:
            return None

        endpoint = "https://api.anthropic.com/v1/messages"
        body = {
            "model": self.model or "claude-3-5-sonnet-20241022",
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_payload},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            logger.info("llm_request_started", extra={"provider": "anthropic", "model": self.model})
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=body, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content_blocks = data.get("content") or []
                    if content_blocks:
                        text = content_blocks[0].get("text", "").strip()
                        logger.info("llm_response_completed", extra={"provider": "anthropic", "chars": len(text)})
                        return text
                    return None
                else:
                    logger.warning(
                        "llm_request_failed",
                        extra={"provider": "anthropic", "status_code": resp.status_code, "detail": resp.text[:200]},
                    )
                    return None
        except Exception as e:
            logger.warning("llm_exception", extra={"provider": "anthropic", "error_type": type(e).__name__})
            return None


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Optional[BaseLLMProvider]:
    """
    Factory to instantiate the configured LLM provider.
    Returns None if api_key is missing or empty.
    """
    key = api_key if api_key is not None else getattr(settings, "LLM_API_KEY", "")
    if not key or not str(key).strip():
        return None

    prov = (provider_name or getattr(settings, "LLM_PROVIDER", "google") or "google").lower().strip()
    mdl = model or getattr(settings, "LLM_MODEL", "gemini-1.5-flash")
    b_url = base_url if base_url is not None else getattr(settings, "LLM_BASE_URL", None)
    t_out = timeout if timeout is not None else getattr(settings, "LLM_TIMEOUT_SECONDS", 12.0)

    if prov in ("google", "gemini"):
        return GoogleGeminiProvider(api_key=key, model=mdl, base_url=b_url, timeout=t_out)
    elif prov in ("openai", "groq", "ollama", "openrouter", "vllm"):
        return OpenAICompatibleProvider(api_key=key, model=mdl, base_url=b_url, timeout=t_out)
    elif prov in ("anthropic", "claude"):
        return AnthropicProvider(api_key=key, model=mdl, base_url=b_url, timeout=t_out)
    else:
        # Default fallback to OpenAI-compatible interface for custom providers
        return OpenAICompatibleProvider(api_key=key, model=mdl, base_url=b_url, timeout=t_out)
