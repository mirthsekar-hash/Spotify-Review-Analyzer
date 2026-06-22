"""Interview insights repository (Phase 4.4)."""

from __future__ import annotations

from uuid import UUID

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import InterviewInsight
from src.schemas.interview_insight import InterviewInsightCreate, InterviewInsightUpdate
from src.db.response_utils import first_insert_row, first_row, response_data


class InterviewInsightsRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("interview_insights")

    def insert(self, insight: InterviewInsightCreate) -> InterviewInsight:
        response = self._table.insert(insight.to_insert_dict()).execute()
        row = first_insert_row(response, context="interview_insights insert")
        return InterviewInsight.from_db(row)

    def update(self, insight_id: UUID, insight: InterviewInsightUpdate) -> InterviewInsight:
        payload = insight.to_update_dict()
        if not payload:
            existing = self.get_by_id(insight_id)
            if existing is None:
                raise ValueError(f"Interview insight not found: {insight_id}")
            return existing

        response = self._table.update(payload).eq("id", str(insight_id)).execute()
        row = first_row(response)
        if not row:
            raise ValueError(f"Interview insight not found: {insight_id}")
        return InterviewInsight.from_db(row)

    def delete(self, insight_id: UUID) -> None:
        self._table.delete().eq("id", str(insight_id)).execute()

    def get_all(self) -> list[InterviewInsight]:
        response = self._table.select("*").order("created_at", desc=True).execute()
        return [InterviewInsight.from_db(row) for row in response_data(response)]

    def get_by_id(self, insight_id: UUID) -> InterviewInsight | None:
        response = self._table.select("*").eq("id", str(insight_id)).limit(1).execute()
        row = first_row(response)
        if not row:
            return None
        return InterviewInsight.from_db(row)
