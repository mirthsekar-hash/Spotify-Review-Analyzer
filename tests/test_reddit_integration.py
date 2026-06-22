"""Reddit ingestion integration tests."""

import os
from unittest.mock import patch

import pytest

from app.config import Settings
from src.ingestion.exceptions import RedditFetchError
from src.ingestion.reddit_json_scraper import RedditJsonScraper, RedditRateLimitError
from src.ingestion.service import IngestionService

RUN_INTEGRATION = os.getenv("RUN_DB_INTEGRATION", "").lower() in {"1", "true", "yes"}
RUN_LIVE_REDDIT = os.getenv("RUN_LIVE_REDDIT", "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_DB_INTEGRATION=1 for Reddit ingestion integration tests",
)


@pytest.fixture(scope="module")
def require_db():
    from src.db.client import check_connection

    if not check_connection():
        pytest.skip("Supabase not available")


def test_ingest_reddit_fallback_csv(require_db):
    service = IngestionService()
    result = service.ingest_reddit_fallback_csv()

    assert result.fetched >= 200
    assert result.normalized >= 200
    assert result.stored >= 1


def test_ingest_reddit_falls_back_on_rate_limit(require_db):
    settings = Settings(
        reddit_user_agent="spotify-review-engine/1.0 (test)",
        min_reviews_reddit=200,
    )
    service = IngestionService(settings=settings)

    with patch.object(
        RedditJsonScraper,
        "fetch",
        side_effect=RedditRateLimitError("Reddit rate limited (429)"),
    ):
        result = service.ingest_reddit()

    assert result.fetched >= 200
    assert result.stored >= 1


def test_ingest_reddit_no_fallback_raises(require_db):
    settings = Settings(
        reddit_user_agent="spotify-review-engine/1.0 (test)",
        min_reviews_reddit=200,
    )
    service = IngestionService(settings=settings)

    with patch.object(
        RedditJsonScraper,
        "fetch",
        side_effect=RedditFetchError("blocked"),
    ):
        with pytest.raises(RedditFetchError):
            service.ingest_reddit(allow_fallback=False)


@pytest.mark.skipif(
    not RUN_LIVE_REDDIT,
    reason="Set RUN_LIVE_REDDIT=1 to run live Reddit scrape test",
)
def test_live_reddit_scraper_fetches_records(require_db):
    records = RedditJsonScraper().fetch()
    unique_ids = {
        record.metadata.get("external_id")
        for record in records
        if record.metadata.get("external_id")
    }

    assert len(records) >= 50, (
        f"Expected at least 50 Reddit records; got {len(records)}. "
        "Retry later if rate-limited."
    )
    assert len(unique_ids) == len(records)


@pytest.mark.skipif(
    not RUN_LIVE_REDDIT,
    reason="Set RUN_LIVE_REDDIT=1 to run live Reddit ingest test",
)
def test_live_ingest_reddit(require_db):
    from src.db.repositories.reviews_repo import ReviewsRepository

    before = ReviewsRepository().count_by_source().get("reddit", 0)
    result = IngestionService().ingest_reddit(allow_fallback=False)
    after = ReviewsRepository().count_by_source().get("reddit", 0)

    assert result.fetched >= 200
    assert after >= before
