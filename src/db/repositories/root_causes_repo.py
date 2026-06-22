"""Root causes repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import RootCause, RootCauseUpsert
from src.db.response_utils import first_row, response_data


class RootCausesRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("root_causes")
        self._reviews = self._client.table("reviews")

    def upsert(self, root_cause: RootCauseUpsert) -> RootCause:
        payload = root_cause.to_upsert_dict()
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = self._table.upsert(payload, on_conflict="root_cause").execute()
        row = first_row(response)
        if not row:
            raise RuntimeError("root_causes upsert returned no row")
        return RootCause.from_db(row)

    def get_all(self) -> list[RootCause]:
        response = self._table.select("*").order("frequency", desc=True).execute()
        return [RootCause.from_db(row) for row in response_data(response)]

    def get_by_text(self, root_cause: str) -> RootCause | None:
        response = self._table.select("*").eq("root_cause", root_cause).limit(1).execute()
        row = first_row(response)
        if not row:
            return None
        return RootCause.from_db(row)

    def get_with_evidence(self, root_cause_id: UUID) -> dict[str, Any]:
        response = self._table.select("*").eq("id", str(root_cause_id)).limit(1).execute()
        row = first_row(response)
        if not row:
            raise ValueError(f"Root cause not found: {root_cause_id}")

        root_cause = RootCause.from_db(row)
        evidence_ids = [str(rid) for rid in root_cause.supporting_evidence_ids]
        reviews: list[dict[str, Any]] = []
        if evidence_ids:
            reviews_response = (
                self._reviews.select("id, source, text, rating")
                .in_("id", evidence_ids)
                .execute()
            )
            reviews = response_data(reviews_response)

        return {
            "root_cause": root_cause,
            "evidence_ids": root_cause.supporting_evidence_ids,
            "reviews": reviews,
        }
