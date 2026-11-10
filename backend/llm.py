"""Minimal LLM client with resilient handling of a third-party API.

- Supports Anthropic or OpenAI, picked from whichever API key is configured.
- Per-attempt timeout, bounded retries with exponential backoff + jitter.
- Retries only on retryable failures (429, 5xx, network errors) and honours
  the Retry-After header, capped so a request never hangs for long.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Callable

import httpx

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


class LLMError(Exception):
    """Raised when the LLM call fails after all retries (or is not retryable)."""

    def __init__(self, reason: str, attempts: int) -> None:
        super().__init__(reason)
        self.reason = reason
        self.attempts = attempts


@dataclass
class LLMResult:
    text: str
    model: str
    attempts: int


@dataclass
class LLMConfig:
    provider: str  # "anthropic" | "openai"
    api_key: str
    model: str
    timeout_s: float = 6.0
    max_attempts: int = 3
    base_delay_s: float = 0.4
    max_delay_s: float = 3.0

    @staticmethod
    def from_env() -> "LLMConfig | None":
        model_override = os.getenv("LLM_MODEL")
        if key := os.getenv("ANTHROPIC_API_KEY"):
            return LLMConfig("anthropic", key, model_override or "claude-haiku-5-5")
        if key := os.getenv("OPENAI_API_KEY"):
            return LLMConfig("openai", key, model_override or "gpt-4.1-mini")
        return None


class LLMClient:
    def __init__(
        self,
        config: LLMConfig,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._http = httpx.Client(timeout=config.timeout_s, transport=transport)

    def complete(self, system: str, user: str, max_tokens: int = 160) -> LLMResult:
        cfg = self.config
        last_reason = "unknown"
        for attempt in range(1, cfg.max_attempts + 1):
            try:
                resp = self._send(system, user, max_tokens)
            except httpx.TimeoutException:
                last_reason, retry_after = "timeout", None
            except httpx.TransportError:
                last_reason, retry_after = "network_error", None
            else:
                if resp.status_code == 200:
                    return LLMResult(self._extract_text(resp.json()), cfg.model, attempt)
                last_reason = f"http_{resp.status_code}"
                if resp.status_code not in RETRYABLE_STATUS:
                    raise LLMError(last_reason, attempt)
                retry_after = _parse_retry_after(resp.headers.get("retry-after"))

            if attempt < cfg.max_attempts:
                self._sleep(self._backoff(attempt, retry_after))
        raise LLMError(last_reason, cfg.max_attempts)

    def _backoff(self, attempt: int, retry_after: float | None) -> float:
        cfg = self.config
        if retry_after is not None:
            return min(retry_after, cfg.max_delay_s)
        exp = cfg.base_delay_s * (2 ** (attempt - 1))
        # Full jitter avoids synchronised retries from many clients.
        return min(cfg.max_delay_s, random.uniform(0, exp))

    def _send(self, system: str, user: str, max_tokens: int) -> httpx.Response:
        cfg = self.config
        if cfg.provider == "anthropic":
            return self._http.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": cfg.api_key, "anthropic-version": "2023-06-01"},
                json={
                    "model": cfg.model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
        return self._http.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {cfg.api_key}"},
            json={
                "model": cfg.model,
                "max_tokens": max_tokens,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )

    def _extract_text(self, body: dict) -> str:
        if self.config.provider == "anthropic":
            parts = [b.get("text", "") for b in body.get("content", []) if b.get("type") == "text"]
            return "".join(parts).strip()
        return body["choices"][0]["message"]["content"].strip()


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
