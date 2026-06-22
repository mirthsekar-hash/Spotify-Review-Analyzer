"""OpenAI LLM provider (optional swap via LLM_PROVIDER=openai)."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from src.llm.schema_utils import pydantic_to_json_schema


class OpenAIProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
    def structured_completion(
        self,
        system_prompt: str,
        user_content: str,
        schema_model: type[BaseModel],
    ) -> BaseModel:
        schema = pydantic_to_json_schema(schema_model)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_model.__name__,
                    "schema": schema,
                    "strict": True,
                },
            },
        )

        raw_text = (response.choices[0].message.content or "").strip()
        if not raw_text:
            raise ValueError("OpenAI returned an empty structured response")

        try:
            return schema_model.model_validate_json(raw_text)
        except ValidationError as exc:
            raise ValueError(f"OpenAI response failed schema validation: {exc}") from exc
