"""Utilities for converting Pydantic models to provider JSON schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def pydantic_to_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Export a JSON schema suitable for structured LLM outputs."""
    schema = model.model_json_schema()
    return _inline_refs(schema)


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Flatten simple $ref pointers from Pydantic v2 schema output."""
    defs = schema.pop("$defs", {}) or schema.pop("definitions", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_name = node["$ref"].split("/")[-1]
                resolved = resolve(defs.get(ref_name, {}))
                return {**resolved, **{k: v for k, v in node.items() if k != "$ref"}}
            return {key: resolve(value) for key, value in node.items()}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(schema)


def strip_json_markdown(text: str) -> str:
    """Remove optional markdown code fences from LLM JSON output."""
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
