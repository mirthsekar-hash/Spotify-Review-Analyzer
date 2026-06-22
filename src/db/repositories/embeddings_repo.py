"""Embeddings table repository."""

from __future__ import annotations

from uuid import UUID

from supabase import Client

from app.config import get_settings
from src.db.client import get_supabase_client
from src.db.models import EmbeddingRecord, VectorSearchResult, format_vector
from src.db.response_utils import first_insert_row, first_row, response_data


class EmbeddingsRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("embeddings")
        self._dimensions = get_settings().embedding_dimensions

    def upsert(self, review_id: UUID, embedding: list[float], model: str) -> EmbeddingRecord:
        if len(embedding) != self._dimensions:
            raise ValueError(
                f"Embedding length {len(embedding)} does not match EMBEDDING_DIMENSIONS={self._dimensions}"
            )

        payload = {
            "review_id": str(review_id),
            "embedding": format_vector(embedding),
            "model": model,
        }
        response = self._table.upsert(payload, on_conflict="review_id").execute()
        row = first_insert_row(response, context="embeddings upsert")
        return EmbeddingRecord.from_db(row)

    def get_by_review_id(self, review_id: UUID) -> EmbeddingRecord | None:
        response = (
            self._table.select("*")
            .eq("review_id", str(review_id))
            .limit(1)
            .execute()
        )
        row = first_row(response)
        if not row:
            return None
        return EmbeddingRecord.from_db(row)

    def vector_search(
        self,
        query_embedding: list[float],
        match_count: int = 15,
    ) -> list[VectorSearchResult]:
        if len(query_embedding) != self._dimensions:
            raise ValueError(
                f"Query embedding length {len(query_embedding)} does not match EMBEDDING_DIMENSIONS={self._dimensions}"
            )

        response = self._client.rpc(
            "match_reviews",
            {
                "query_embedding": format_vector(query_embedding),
                "match_count": match_count,
            },
        ).execute()

        rows = response_data(response)
        return [
            VectorSearchResult(
                review_id=UUID(row["review_id"]),
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]
