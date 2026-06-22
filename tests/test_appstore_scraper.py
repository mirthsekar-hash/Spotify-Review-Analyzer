"""App Store scraper unit tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from src.db.models import RawRecord
from src.ingestion.appstore_scraper import AppStoreScraper, _record_key
from src.ingestion.base import IngestConfig

RSS_REVIEW_ENTRY = {
    "author": {"name": {"label": "ios_reviewer"}},
    "im:rating": {"label": "2"},
    "title": {"label": "Stale recommendations"},
    "content": {"label": "Discover Weekly playlist feels repetitive every week."},
    "updated": {"label": "Mon, 03 Jun 2024 12:00:00 GMT"},
    "id": {"label": "https://itunes.apple.com/us/review?id=324684580&type=Purple%20Software"},
}

def _scraper_with_library(enabled: bool = True) -> AppStoreScraper:
    settings = Settings(
        spotify_app_store_app_id="324684580",
        min_reviews_appstore=300,
        app_store_use_library=enabled,
    )
    return AppStoreScraper(settings=settings)


RSS_APP_ENTRY = {
    "title": {"label": "Spotify: Music and Podcasts"},
    "id": {"label": "https://itunes.apple.com/us/app/spotify/id324684580"},
}


def test_source_name():
    assert AppStoreScraper().source_name() == "appstore"


def test_rss_entry_to_record_parses_review():
    scraper = AppStoreScraper()
    record = scraper._rss_entry_to_record(RSS_REVIEW_ENTRY, sort_order="mostrecent", country="us")

    assert record is not None
    assert record.source == "appstore"
    assert record.rating == 2
    assert "Discover Weekly" in record.text
    assert record.metadata["fetch_method"] == "itunes_rss"
    assert record.metadata["external_id"].startswith("https://itunes.apple.com")


def test_rss_entry_to_record_skips_app_metadata():
    scraper = AppStoreScraper()
    assert scraper._rss_entry_to_record(RSS_APP_ENTRY, sort_order="mostrecent", country="us") is None


def test_library_item_to_record_combines_title_and_body():
    scraper = AppStoreScraper()
    record = scraper._library_item_to_record(
        {
            "title": "Great but repetitive",
            "review": "Recommendations repeat the same artists.",
            "rating": 3,
            "userName": "tester",
            "date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "reviewId": "abc123",
        }
    )

    assert "Great but repetitive" in record.text
    assert record.metadata["external_id"] == "abc123"


@patch.object(AppStoreScraper, "_fetch_via_library", side_effect=RuntimeError("blocked"))
@patch.object(AppStoreScraper, "_fetch_via_rss")
@patch.object(AppStoreScraper, "_fetch_keyword_filtered", return_value=[])
def test_fetch_falls_back_to_rss_when_library_fails(mock_keywords, mock_rss, mock_library):
    review = RawRecord(
        source="appstore",
        text="Shuffle keeps repeating playlist songs",
        rating=2,
        metadata={"external_id": "rss_1"},
    )

    def populate_rss(config, collected):
        collected["rss_1"] = review

    mock_rss.side_effect = populate_rss

    records = _scraper_with_library(enabled=True).fetch(
        IngestConfig(app_id="324684580", target_count=10)
    )
    assert len(records) == 1
    assert records[0].source == "appstore"
    mock_library.assert_called_once()
    mock_rss.assert_called_once()


@patch("src.ingestion.appstore_scraper.httpx.get")
def test_fetch_rss_page_parses_entries(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"feed": {"entry": [RSS_APP_ENTRY, RSS_REVIEW_ENTRY]}}
    mock_get.return_value = mock_response

    entries = AppStoreScraper()._fetch_rss_page("us", "324684580", 1, "mostrecent")
    assert len(entries) == 2


@patch.object(AppStoreScraper, "_fetch_via_library")
@patch.object(AppStoreScraper, "_fetch_via_rss")
@patch.object(AppStoreScraper, "_fetch_keyword_filtered", return_value=[])
def test_fetch_returns_unique_records(mock_keywords, mock_rss, mock_library):
    review_a = RawRecord(
        source="appstore",
        text="Discover playlist recommendations are stale",
        rating=2,
        metadata={"external_id": "dup"},
    )
    review_b = RawRecord(
        source="appstore",
        text="Discover playlist recommendations are stale copy",
        rating=1,
        metadata={"external_id": "dup"},
    )

    def populate_library(config, collected):
        collected[_record_key(review_a)] = review_a
        collected[_record_key(review_b)] = review_b

    mock_library.side_effect = populate_library

    records = _scraper_with_library(enabled=True).fetch(
        IngestConfig(app_id="324684580", target_count=5)
    )
    assert len(records) == 1
