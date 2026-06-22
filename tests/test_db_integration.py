"""Optional live Supabase integration tests.

Run migration first:
  supabase/migrations/001_initial_schema.sql

Then:
  set RUN_DB_INTEGRATION=1
  pytest tests/test_db_integration.py -v
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app.config import get_settings
from src.db.client import check_connection, get_supabase_client
from src.db.models import NormalizedReview, ReviewAnalysisCreate, compute_content_hash
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.embeddings_repo import EmbeddingsRepository
from src.db.repositories.reviews_repo import ReviewsRepository

RUN_INTEGRATION = os.getenv("RUN_DB_INTEGRATION", "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_DB_INTEGRATION=1 to run live Supabase tests",
)


@pytest.fixture(scope="module")
def require_db():
    settings = get_settings()
    if not settings.supabase_url.strip() or not settings.supabase_service_key.strip():
        pytest.skip("Supabase credentials not configured")
    if not check_connection():
        pytest.skip("Supabase unreachable or migration not applied")


def test_live_insert_and_read_review(require_db):
    unique_text = f"Integration test review {uuid4()}"
    review = NormalizedReview(
        source="playstore",
        text=unique_text,
        rating=3,
        review_date=None,
        metadata={"test": True},
        content_hash=compute_content_hash(unique_text, "playstore"),
    )

    reviews_repo = ReviewsRepository()
    result = reviews_repo.upsert_batch([review])
    assert result.stored == 1

    stored = reviews_repo.get_by_id(result.review_ids[0])
    assert stored is not None
    assert stored.text == unique_text

    # Duplicate upsert should not create a second row
    duplicate = reviews_repo.upsert_batch([review])
    assert duplicate.stored == 1
    assert duplicate.review_ids[0] == result.review_ids[0]


def test_live_vector_search(require_db):
    unique_text = f"Vector search test {uuid4()}"
    review = NormalizedReview(
        source="reddit",
        text=unique_text,
        rating=None,
        review_date=None,
        metadata={},
        content_hash=compute_content_hash(unique_text, "reddit"),
    )

    reviews_repo = ReviewsRepository()
    upsert = reviews_repo.upsert_batch([review])
    review_id = upsert.review_ids[0]

    dimensions = get_settings().embedding_dimensions
    embedding = [0.0] * dimensions
    embedding[0] = 1.0

    embeddings_repo = EmbeddingsRepository()
    embeddings_repo.upsert(review_id, embedding, model="test-model")

    results = embeddings_repo.vector_search(embedding, match_count=5)
    assert any(item.review_id == review_id for item in results)


def test_live_analysis_insert(require_db):
    unique_text = f"Analysis test {uuid4()}"
    review = NormalizedReview(
        source="appstore",
        text=unique_text,
        rating=2,
        review_date=None,
        metadata={},
        content_hash=compute_content_hash(unique_text, "appstore"),
    )

    reviews_repo = ReviewsRepository()
    review_id = reviews_repo.upsert_batch([review]).review_ids[0]

    analysis_repo = AnalysisRepository()
    created = analysis_repo.insert(
        ReviewAnalysisCreate(
            review_id=review_id,
            sentiment="negative",
            primary_problem="Repetitive recommendations",
            recommendation_complaint=True,
            confidence_score=0.88,
        )
    )
    assert created.review_id == review_id

    fetched = analysis_repo.get_by_review_id(review_id)
    assert fetched is not None
    assert fetched.sentiment == "negative"

    counts = analysis_repo.aggregate_sentiment()
    assert counts["negative"] >= 1
