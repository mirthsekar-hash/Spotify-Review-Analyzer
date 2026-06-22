"""Pipeline runs table repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import PipelineStatus
from src.db.response_utils import first_insert_row, response_data


class PipelineRunsRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("pipeline_runs")

    def create_run(self, stats: dict[str, Any] | None = None) -> UUID:
        payload = {
            "status": "running",
            "stats": stats or {},
        }
        response = self._table.insert(payload).execute()
        row = first_insert_row(response, context="pipeline_runs insert")
        return UUID(row["id"])

    def finish_run(
        self,
        run_id: UUID,
        status: PipelineStatus,
        stats: dict[str, Any],
    ) -> None:
        self._table.update(
            {
                "status": status,
                "stats": stats,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", str(run_id)).execute()

    def get_latest(self) -> dict[str, Any] | None:
        response = (
            self._table.select("*")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if response is None:
            return None
        rows = response_data(response)
        return rows[0] if rows else None

    def get_latest_collective_run(self) -> dict[str, Any] | None:
        response = (
            self._table.select("*")
            .contains("stats", {"run_type": "collective_analysis"})
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if response is None:
            return None
        rows = response_data(response)
        return rows[0] if rows else None
