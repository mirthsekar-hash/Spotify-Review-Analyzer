"""Helpers for Supabase PostgREST responses."""

from __future__ import annotations

from typing import Any


def response_data(response: Any) -> list[dict[str, Any]]:
    """Return rows from a Supabase response, or [] if missing."""
    if response is None:
        return []
    return response.data or []


def first_row(response: Any) -> dict[str, Any] | None:
    """Return the first row from a select response, or None if empty."""
    rows = response_data(response)
    return rows[0] if rows else None


def first_insert_row(response: Any, *, context: str = "insert") -> dict[str, Any]:
    """Return the first row from an insert/upsert response."""
    row = first_row(response)
    if row is None:
        raise RuntimeError(f"Supabase {context} returned no rows")
    return row
