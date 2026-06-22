"""Google Gemini LLM provider."""

from __future__ import annotations

import time

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import Settings
from src.llm.errors import (
    extract_retry_delay_seconds,
    is_quota_exceeded,
    is_transient_rate_limit,
    raise_if_quota_exceeded,
)
from src.llm.schema_utils import pydantic_to_json_schema


def _should_retry_gemini(exc: BaseException) -> bool:
    if is_quota_exceeded(exc):
        return False
    return is_transient_rate_limit(exc)


class GeminiProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key.strip():
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

        from google import genai

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    def structured_completion(
        self,
        system_prompt: str,
        user_content: str,
        schema_model: type[BaseModel],
    ) -> BaseModel:
        return self._structured_completion_with_retry(
            system_prompt,
            user_content,
            schema_model,
        )

    @retry(
        retry=retry_if_exception(_should_retry_gemini),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def _structured_completion_with_retry(
        self,
        system_prompt: str,
        user_content: str,
        schema_model: type[BaseModel],
    ) -> BaseModel:
        try:
            return self._generate_structured(system_prompt, user_content, schema_model)
        except Exception as exc:
            raise_if_quota_exceeded(exc)
            delay = extract_retry_delay_seconds(exc)
            if delay and is_transient_rate_limit(exc):
                time.sleep(min(delay, 60))
            raise

    def _generate_structured(
        self,
        system_prompt: str,
        user_content: str,
        schema_model: type[BaseModel],
    ) -> BaseModel:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=pydantic_to_json_schema(schema_model),
            ),
        )

        raw_text = (response.text or "").strip()
        if not raw_text:
            raise ValueError("Gemini returned an empty structured response")

        try:
            return schema_model.model_validate_json(raw_text)
        except ValidationError as exc:
            raise ValueError(f"Gemini response failed schema validation: {exc}") from exc
