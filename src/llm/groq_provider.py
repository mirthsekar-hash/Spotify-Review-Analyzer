"""Groq LLM provider (OpenAI-compatible API, JSON mode + Pydantic validation)."""

from __future__ import annotations

import json
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
from src.llm.schema_utils import pydantic_to_json_schema, strip_json_markdown


def _should_retry_groq(exc: BaseException) -> bool:
    if is_quota_exceeded(exc):
        return False
    return is_transient_rate_limit(exc)


class GroqProvider:
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key.strip():
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

        from openai import OpenAI

        self._client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=self.GROQ_BASE_URL,
        )
        self._model = settings.groq_model

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
        retry=retry_if_exception(_should_retry_groq),
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
        schema_json = json.dumps(pydantic_to_json_schema(schema_model), indent=2)
        full_system = (
            f"{system_prompt}\n\n"
            "Return a single JSON object only (no markdown fences or commentary). "
            "The JSON must satisfy this schema:\n"
            f"{schema_json}"
        )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw_text = strip_json_markdown((response.choices[0].message.content or "").strip())
        if not raw_text:
            raise ValueError("Groq returned an empty structured response")

        try:
            return schema_model.model_validate_json(raw_text)
        except ValidationError as exc:
            raise ValueError(f"Groq response failed schema validation: {exc}") from exc
