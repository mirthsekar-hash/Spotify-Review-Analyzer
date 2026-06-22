"""Themes and theme_reviews junction repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import Theme, ThemeUpsert
from src.db.response_utils import first_row, response_data


class ThemesRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("themes")
        self._junction = self._client.table("theme_reviews")

    def upsert(self, theme: ThemeUpsert) -> Theme:
        payload = theme.to_upsert_dict()
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = self._table.upsert(payload, on_conflict="theme_name").execute()
        row = first_row(response)
        if not row:
            raise RuntimeError("themes upsert returned no row")
        return Theme.from_db(row)

    def get_all(self) -> list[Theme]:
        response = self._table.select("*").order("impact_score", desc=True).execute()
        return [Theme.from_db(row) for row in response_data(response)]

    def get_by_name(self, theme_name: str) -> Theme | None:
        response = self._table.select("*").eq("theme_name", theme_name).limit(1).execute()
        row = first_row(response)
        if not row:
            return None
        return Theme.from_db(row)

    def get_by_id(self, theme_id: UUID) -> Theme | None:
        response = self._table.select("*").eq("id", str(theme_id)).limit(1).execute()
        row = first_row(response)
        if not row:
            return None
        return Theme.from_db(row)

    def count_linked_reviews(self, theme_id: UUID) -> int:
        response = (
            self._junction.select("review_id", count="exact")
            .eq("theme_id", str(theme_id))
            .limit(1)
            .execute()
        )
        if response.count:
            return int(response.count)

        theme = self.get_by_id(theme_id)
        if theme is None:
            return 0
        return len(theme.representative_review_ids)

    def replace_theme_reviews(self, theme_id: UUID, review_ids: list[UUID]) -> None:
        self._junction.delete().eq("theme_id", str(theme_id)).execute()
        if not review_ids:
            return
        rows = [
            {"theme_id": str(theme_id), "review_id": str(review_id)}
            for review_id in review_ids
        ]
        self._junction.insert(rows).execute()

    def get_with_reviews(self, theme_id: UUID) -> dict[str, Any]:
        theme_response = self._table.select("*").eq("id", str(theme_id)).limit(1).execute()
        theme_row = first_row(theme_response)
        if not theme_row:
            raise ValueError(f"Theme not found: {theme_id}")

        links_response = (
            self._junction.select("review_id, reviews(id, source, text, rating)")
            .eq("theme_id", str(theme_id))
            .execute()
        )
        link_rows = response_data(links_response)
        reviews: list[dict[str, Any]] = []
        for link in link_rows:
            review = link.get("reviews")
            if isinstance(review, list):
                review = review[0] if review else None
            if review:
                reviews.append(review)

        return {
            "theme": Theme.from_db(theme_row),
            "review_ids": [UUID(str(link["review_id"])) for link in link_rows],
            "reviews": reviews,
        }
