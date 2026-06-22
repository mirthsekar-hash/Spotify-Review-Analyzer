"""Ingestion service integration test."""

import os
from uuid import uuid4

import pytest

from src.db.models import RawRecord
from src.ingestion.service import IngestionService

RUN_INTEGRATION = os.getenv("RUN_DB_INTEGRATION", "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_DB_INTEGRATION=1 for live ingestion tests",
)


@pytest.fixture(scope="module")
def require_db():
    from src.db.client import check_connection

    if not check_connection():
        pytest.skip("Supabase not available")


def test_ingest_csv_bytes_matches_scraper_path(require_db):
    unique_suffix = str(uuid4())[:8]
    csv_data = (
        "source,text,rating,review_date,reviewer_name,external_id\n"
        f"playstore,CSV ingestion test {unique_suffix},3,2024-06-01,tester,csv_{unique_suffix}\n"
    ).encode("utf-8")

    service = IngestionService()
    result = service.ingest_csv_bytes(csv_data)

    assert result.fetched == 1
    assert result.stored >= 1
    assert result.normalized == 1


def test_ingest_fallback_csv(require_db):
    service = IngestionService()
    result = service.ingest_fallback_csv()
    assert result.fetched >= 50
    assert result.stored >= 1
