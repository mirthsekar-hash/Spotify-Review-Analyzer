"""User segments repository."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import Segment, SegmentUpsert
from src.db.response_utils import first_row, response_data


class SegmentsRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("segments")

    def upsert(self, segment: SegmentUpsert) -> Segment:
        payload = segment.to_upsert_dict()
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = self._table.upsert(payload, on_conflict="segment_name").execute()
        row = first_row(response)
        if not row:
            raise RuntimeError("segments upsert returned no row")
        return Segment.from_db(row)

    def get_all(self) -> list[Segment]:
        response = self._table.select("*").order("size", desc=True).execute()
        return [Segment.from_db(row) for row in response_data(response)]

    def get_by_name(self, segment_name: str) -> Segment | None:
        response = (
            self._table.select("*").eq("segment_name", segment_name).limit(1).execute()
        )
        row = first_row(response)
        if not row:
            return None
        return Segment.from_db(row)
