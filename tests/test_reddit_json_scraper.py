"""Reddit JSON scraper unit tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from src.db.models import RawRecord
from src.ingestion.exceptions import RedditFetchError
from src.ingestion.reddit_json_scraper import (
    RedditJsonScraper,
    RedditRateLimitError,
    truncate_reddit_text,
    _record_key,
)


def _settings() -> Settings:
    return Settings(
        reddit_user_agent="spotify-review-engine/1.0 (test)",
        reddit_request_delay_seconds=0,
        min_reviews_reddit=5,
    )


def test_source_name():
    assert RedditJsonScraper(settings=_settings()).source_name() == "reddit"


def test_missing_user_agent_raises():
    with pytest.raises(RedditFetchError, match="REDDIT_USER_AGENT"):
        RedditJsonScraper(settings=Settings(reddit_user_agent=""))


def test_truncate_reddit_text_short_unchanged():
    text = "Short complaint about recommendations"
    assert truncate_reddit_text(text) == text


def test_truncate_reddit_text_long_adds_ellipsis():
    text = "x" * 5000
    result = truncate_reddit_text(text)
    assert len(result) == 4000
    assert result.endswith("...")


def test_record_key_uses_external_id():
    record = RawRecord(
        source="reddit",
        text="test",
        metadata={"external_id": "t3_abc"},
    )
    assert _record_key(record) == "t3_abc"


def test_post_to_record_parses_title_and_body():
    scraper = RedditJsonScraper(settings=_settings())
    record = scraper._post_to_record(
        "spotify",
        {
            "name": "t3_xyz",
            "title": "Discover Weekly is stale",
            "selftext": "Same artists every week.",
            "created_utc": 1704067200,
            "score": 42,
            "author": "tester",
            "permalink": "/r/spotify/comments/xyz/",
        },
    )

    assert record is not None
    assert record.source == "reddit"
    assert "Discover Weekly" in record.text
    assert record.metadata["external_id"] == "t3_xyz"
    assert record.metadata["subreddit"] == "spotify"
    assert record.metadata["upvotes"] == 42
    assert record.metadata["content_type"] == "post"
    assert record.metadata["fetch_method"] == "reddit_json"


def test_comment_to_record_skips_removed():
    scraper = RedditJsonScraper(settings=_settings())
    assert (
        scraper._comment_to_record(
            "spotify",
            {"body": "[removed]", "name": "t1_abc"},
        )
        is None
    )


def test_get_json_raises_rate_limit_on_429():
    scraper = RedditJsonScraper(settings=_settings())
    response = MagicMock()
    response.status_code = 429
    response.json.return_value = {}

    with patch("httpx.get", return_value=response):
        with pytest.raises(RedditRateLimitError):
            scraper._get_json("https://www.reddit.com/r/spotify/hot.json")


def test_get_json_sends_user_agent_header():
    scraper = RedditJsonScraper(settings=_settings())
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"data": {"children": []}}

    with patch("httpx.get", return_value=response) as mock_get:
        scraper._get_json("https://www.reddit.com/r/spotify/hot.json")

    mock_get.assert_called_once()
    headers = mock_get.call_args.kwargs["headers"]
    assert headers["User-Agent"] == "spotify-review-engine/1.0 (test)"


@patch.object(RedditJsonScraper, "_sleep_between_requests")
@patch.object(RedditJsonScraper, "_fetch_post_comments", return_value=[])
@patch.object(RedditJsonScraper, "_fetch_search_posts", return_value=[])
@patch.object(RedditJsonScraper, "_fetch_hot_posts")
def test_fetch_collects_hot_posts(mock_hot, _mock_search, _mock_comments, _mock_sleep):
    post = RawRecord(
        source="reddit",
        text="Algorithm keeps suggesting the same playlist",
        metadata={
            "external_id": "t3_post1",
            "content_type": "post",
            "upvotes": 10,
            "fetch_method": "reddit_json",
        },
    )
    mock_hot.return_value = [post]

    records = RedditJsonScraper(settings=_settings()).fetch()

    assert len(records) == 1
    assert records[0].metadata["external_id"] == "t3_post1"


@patch.object(RedditJsonScraper, "_sleep_between_requests")
@patch.object(RedditJsonScraper, "_fetch_post_comments")
@patch.object(RedditJsonScraper, "_fetch_search_posts", return_value=[])
@patch.object(RedditJsonScraper, "_fetch_hot_posts")
def test_fetch_deduplicates_by_external_id(
    mock_hot, _mock_search, mock_comments, _mock_sleep
):
    duplicate = RawRecord(
        source="reddit",
        text="Same post",
        metadata={"external_id": "t3_dup", "content_type": "post", "upvotes": 5},
    )
    comment = RawRecord(
        source="reddit",
        text="Same comment",
        metadata={"external_id": "t1_dup", "content_type": "comment", "upvotes": 2},
    )
    mock_hot.return_value = [duplicate, duplicate]
    mock_comments.return_value = [comment]

    records = RedditJsonScraper(settings=_settings()).fetch()

    assert len(records) == 2
    ids = {record.metadata["external_id"] for record in records}
    assert ids == {"t3_dup", "t1_dup"}


def test_parse_created_utc():
    parsed = RedditJsonScraper._parse_created_utc(1704067200)
    assert parsed == datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
