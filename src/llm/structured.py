"""Provider-agnostic structured LLM completion."""

from __future__ import annotations

from pydantic import BaseModel

from src.llm.factory import get_llm_provider


def structured_completion(
    system_prompt: str,
    user_content: str,
    schema_model: type[BaseModel],
) -> BaseModel:
    """Call the configured LLM provider and return a validated Pydantic model."""
    provider = get_llm_provider()
    return provider.structured_completion(system_prompt, user_content, schema_model)
