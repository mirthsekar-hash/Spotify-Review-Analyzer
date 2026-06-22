"""LLM error helper tests."""

from src.llm.errors import (
    LlmQuotaExceededError,
    format_llm_error,
    is_quota_exceeded,
    raise_if_quota_exceeded,
)


class _FakeClientError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def test_format_llm_error_includes_message():
    cause = _FakeClientError(
        "429 RESOURCE_EXHAUSTED. quota exceeded for generate_content_free_tier_requests"
    )
    message = format_llm_error(cause)
    assert "429 RESOURCE_EXHAUSTED" in message
    assert is_quota_exceeded(cause)


def test_raise_if_quota_exceeded():
    exc = _FakeClientError("You exceeded your current quota, please check your plan")
    try:
        raise_if_quota_exceeded(exc)
        assert False, "Expected LlmQuotaExceededError"
    except LlmQuotaExceededError as quota_exc:
        assert "quota" in str(quota_exc).lower()
