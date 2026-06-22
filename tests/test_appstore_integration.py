"""App Store ingestion integration tests."""

import os

import pytest

from src.db.repositories.reviews_repo import ReviewsRepository
from src.ingestion.appstore_scraper import AppStoreScraper
from src.ingestion.service import IngestionService

RUN_INTEGRATION = os.getenv("RUN_DB_INTEGRATION", "").lower() in {"1", "true", "yes"}
RUN_LIVE_APPSTORE = os.getenv("RUN_LIVE_APPSTORE", "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_DB_INTEGRATION=1 for live App Store ingestion tests",
)


@pytest.fixture(scope="module")
def require_db():
    from src.db.client import check_connection

    if not check_connection():
        pytest.skip("Supabase not available")


def test_ingest_appstore_fallback_csv(require_db):
    service = IngestionService()
    result = service.ingest_appstore_fallback_csv()

    assert result.fetched >= 50
    assert result.stored >= 1
    assert result.normalized >= 50


@pytest.mark.skipif(
    not RUN_LIVE_APPSTORE,
    reason="Set RUN_LIVE_APPSTORE=1 to run live App Store scrape test",
)
def test_live_appstore_scraper_fetches_unique_reviews(require_db):
    records = AppStoreScraper().fetch()
    unique_texts = {record.text for record in records}

    assert len(records) >= 50, (
        f"Expected at least 50 App Store reviews (target 300 when Apple RSS is available); "
        f"got {len(records)}. Retry later if rate-limited."
    )
    assert len(unique_texts) == len(records)


@pytest.mark.skipif(
    not RUN_LIVE_APPSTORE,
    reason="Set RUN_LIVE_APPSTORE=1 to run live App Store ingest test",
)
def test_live_ingest_appstore_reviews(require_db):
    before = ReviewsRepository().count_by_source().get("appstore", 0)
    result = IngestionService().ingest_appstore()
    after = ReviewsRepository().count_by_source().get("appstore", 0)

    assert result.fetched >= 50
    assert after >= before
