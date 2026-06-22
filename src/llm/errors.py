"""LLM error helpers for quota detection and readable messages."""

from __future__ import annotations

from typing import Any


class LlmQuotaExceededError(RuntimeError):
    """Raised when the LLM provider quota or hard rate limit is exceeded."""


def unwrap_exception(exc: BaseException) -> BaseException:
    """Return the underlying exception from tenacity RetryError wrappers."""
    last_attempt = getattr(exc, "last_attempt", None)
    if last_attempt is not None and getattr(last_attempt, "failed", False):
        nested = last_attempt.exception()
        if nested is not None:
            return nested
    return exc


def format_llm_error(exc: BaseException) -> str:
    """Format an LLM error for logs and UI (unwraps RetryError)."""
    root = unwrap_exception(exc)
    message = str(root).strip()
    if message:
        return message
    return f"{type(root).__name__} (no message)"


def is_quota_exceeded(exc: BaseException) -> bool:
    """Return True when the error indicates daily quota or billing limits."""
    root = unwrap_exception(exc)
    text = format_llm_error(root).lower()
    markers = (
        "quota exceeded",
        "resource_exhausted",
        "exceeded your current quota",
        "perday",
        "per day",
        "billing",
    )
    return any(marker in text for marker in markers)


def is_transient_rate_limit(exc: BaseException) -> bool:
    """Return True for short-lived 429s that may succeed after a delay."""
    if is_quota_exceeded(exc):
        return False
    root = unwrap_exception(exc)
    text = format_llm_error(root).lower()
    return "429" in text or "rate limit" in text or "too many requests" in text


def raise_if_quota_exceeded(exc: BaseException) -> None:
    """Raise LlmQuotaExceededError when the provider reports quota exhaustion."""
    if not is_quota_exceeded(exc):
        return
    root = unwrap_exception(exc)
    raise LlmQuotaExceededError(format_llm_error(root)) from exc


def extract_retry_delay_seconds(exc: BaseException) -> float | None:
    """Parse RetryInfo delay from a Google GenAI ClientError when present."""
    root = unwrap_exception(exc)
    details = _client_error_details(root)
    for item in details:
        if not isinstance(item, dict):
            continue
        if item.get("@type", "").endswith("RetryInfo"):
            delay = item.get("retryDelay")
            if isinstance(delay, str) and delay.endswith("s"):
                try:
                    return float(delay[:-1])
                except ValueError:
                    return None
            if isinstance(delay, (int, float)):
                return float(delay)
    return None


def _client_error_details(exc: BaseException) -> list[Any]:
    response = getattr(exc, "response", None)
    if response is None:
        return []
    payload = getattr(response, "body", None) or getattr(response, "json", None)
    if callable(payload):
        try:
            payload = payload()
        except Exception:
            return []
    if not isinstance(payload, dict):
        return []
    error = payload.get("error") or {}
    if not isinstance(error, dict):
        return []
    details = error.get("details") or []
    return details if isinstance(details, list) else []
