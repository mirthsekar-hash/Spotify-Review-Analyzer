"""Unmet needs repository."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import UnmetNeed, UnmetNeedUpsert
from src.db.response_utils import first_row, response_data


class UnmetNeedsRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("unmet_needs")

    def upsert(self, unmet_need: UnmetNeedUpsert) -> UnmetNeed:
        payload = unmet_need.to_upsert_dict()
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = self._table.upsert(payload, on_conflict="need").execute()
        row = first_row(response)
        if not row:
            raise RuntimeError("unmet_needs upsert returned no row")
        return UnmetNeed.from_db(row)

    def get_all(self) -> list[UnmetNeed]:
        response = self._table.select("*").order("opportunity_score", desc=True).execute()
        return [UnmetNeed.from_db(row) for row in response_data(response)]

    def get_top_by_opportunity(self, limit: int = 10) -> list[UnmetNeed]:
        response = (
            self._table.select("*")
            .order("opportunity_score", desc=True)
            .limit(limit)
            .execute()
        )
        return [UnmetNeed.from_db(row) for row in response_data(response)]

    def get_by_need(self, need: str) -> UnmetNeed | None:
        response = self._table.select("*").eq("need", need).limit(1).execute()
        row = first_row(response)
        if not row:
            return None
        return UnmetNeed.from_db(row)
