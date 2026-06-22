"""Reddit public JSON API scraper (no OAuth)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from src.db.models import RawRecord, ReviewSource
from src.ingestion.base import IngestConfig, SourceAdapter
from src.ingestion.exceptions import RedditFetchError

logger = logging.getLogger(__name__)

REDDIT_BASE_URL = "https://www.reddit.com"
REDDIT_SUBREDDITS = ("spotify", "truespotify", "music", "listentothis")
REDDIT_SEARCH_TERMS = (
    "Spotify recommendations",
    "Spotify discover weekly",
    "Spotify smart shuffle",
    "Spotify algorithm",
    "Spotify music discovery",
    "Spotify playlist recommendations",
    "Spotify suggested songs",
)
TOP_POSTS_FOR_COMMENTS = 5
MAX_TEXT_LENGTH = 4000
REQUEST_TIMEOUT = 30.0


class RedditRateLimitError(RedditFetchError):
    """Raised when Reddit returns 429 or 403."""


def _record_key(record: RawRecord) -> str:
    external_id = record.metadata.get("external_id")
    if external_id:
        return str(external_id)
    return f"{record.source}:{hash(record.text)}"


def truncate_reddit_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 3].rstrip()}..."


class RedditJsonScraper(SourceAdapter):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.reddit_user_agent.strip():
            raise RedditFetchError("REDDIT_USER_AGENT is not configured")

    def source_name(self) -> ReviewSource:
        return "reddit"

    def fetch(self, config: IngestConfig | None = None) -> list[RawRecord]:
        target_count = (
            config.target_count if config else self._settings.min_reviews_reddit
        )
        collected: dict[str, RawRecord] = {}
        posts_by_subreddit: dict[str, list[RawRecord]] = {
            subreddit: [] for subreddit in REDDIT_SUBREDDITS
        }

        for subreddit in REDDIT_SUBREDDITS:
            if len(collected) >= target_count:
                break

            for record in self._fetch_hot_posts(subreddit):
                self._store_record(collected, posts_by_subreddit, subreddit, record)
                if len(collected) >= target_count:
                    break

            for term in REDDIT_SEARCH_TERMS:
                if len(collected) >= target_count:
                    break
                for record in self._fetch_search_posts(subreddit, term):
                    self._store_record(collected, posts_by_subreddit, subreddit, record)
                    if len(collected) >= target_count:
                        break

        for subreddit, posts in posts_by_subreddit.items():
            if len(collected) >= target_count:
                break
            top_posts = sorted(
                posts,
                key=lambda item: item.metadata.get("upvotes", 0),
                reverse=True,
            )[:TOP_POSTS_FOR_COMMENTS]
            for post in top_posts:
                post_id = self._post_id_from_external_id(post.metadata.get("external_id"))
                if not post_id:
                    continue
                for record in self._fetch_post_comments(subreddit, post_id):
                    self._store_record(collected, posts_by_subreddit, subreddit, record)
                    if len(collected) >= target_count:
                        break

        logger.info("Reddit fetch collected %s unique records", len(collected))
        return list(collected.values())

    def _store_record(
        self,
        collected: dict[str, RawRecord],
        posts_by_subreddit: dict[str, list[RawRecord]],
        subreddit: str,
        record: RawRecord,
    ) -> None:
        key = _record_key(record)
        if key in collected:
            return
        collected[key] = record
        if record.metadata.get("content_type") == "post":
            posts_by_subreddit[subreddit].append(record)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._settings.reddit_user_agent}

    def _sleep_between_requests(self) -> None:
        time.sleep(self._settings.reddit_request_delay_seconds)

    @retry(
        retry=retry_if_exception_type(RedditRateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        reraise=True,
    )
    def _get_json(self, url: str) -> dict[str, Any]:
        try:
            response = httpx.get(
                url,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            raise RedditFetchError(f"Reddit request failed: {exc}") from exc

        if response.status_code in {429, 403}:
            raise RedditRateLimitError(
                f"Reddit rate limited ({response.status_code}) for {url}"
            )
        if response.status_code >= 400:
            raise RedditFetchError(
                f"Reddit request failed ({response.status_code}) for {url}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RedditFetchError(f"Invalid JSON from Reddit: {url}") from exc

    def _request_listing(self, url: str) -> list[dict[str, Any]]:
        payload = self._get_json(url)
        children = payload.get("data", {}).get("children", [])
        self._sleep_between_requests()
        return children

    def _fetch_hot_posts(self, subreddit: str) -> list[RawRecord]:
        url = f"{REDDIT_BASE_URL}/r/{subreddit}/hot.json?limit=100"
        return self._children_to_records(subreddit, self._request_listing(url), "post")

    def _fetch_search_posts(self, subreddit: str, term: str) -> list[RawRecord]:
        query = quote_plus(term)
        url = (
            f"{REDDIT_BASE_URL}/r/{subreddit}/search.json"
            f"?q={query}&restrict_sr=on&limit=100&sort=relevance"
        )
        return self._children_to_records(subreddit, self._request_listing(url), "post")

    def _fetch_post_comments(self, subreddit: str, post_id: str) -> list[RawRecord]:
        url = f"{REDDIT_BASE_URL}/r/{subreddit}/comments/{post_id}.json"
        try:
            payload = self._get_json(url)
        except RedditFetchError as exc:
            logger.warning("Failed to fetch comments for %s: %s", post_id, exc)
            return []

        self._sleep_between_requests()

        if not isinstance(payload, list) or len(payload) < 2:
            return []

        comment_children = payload[1].get("data", {}).get("children", [])
        return self._children_to_records(subreddit, comment_children, "comment")

    def _children_to_records(
        self,
        subreddit: str,
        children: list[dict[str, Any]],
        content_type: str,
    ) -> list[RawRecord]:
        records: list[RawRecord] = []
        for child in children:
            record = self._child_to_record(subreddit, child, content_type)
            if record:
                records.append(record)
        return records

    def _child_to_record(
        self,
        subreddit: str,
        child: dict[str, Any],
        content_type: str,
    ) -> RawRecord | None:
        kind = child.get("kind")
        if kind == "more":
            return None

        data = child.get("data", {})
        if kind == "t3" or content_type == "post":
            return self._post_to_record(subreddit, data)
        if kind == "t1" or content_type == "comment":
            return self._comment_to_record(subreddit, data)
        return None

    def _post_to_record(self, subreddit: str, data: dict[str, Any]) -> RawRecord | None:
        title = (data.get("title") or "").strip()
        body = (data.get("selftext") or "").strip()
        if body in {"", "[removed]", "[deleted]"}:
            text = title
        else:
            text = f"{title}\n{body}".strip() if title and title != body else body or title

        text = truncate_reddit_text(text)
        if not text:
            return None

        return RawRecord(
            source="reddit",
            text=text,
            rating=None,
            review_date=self._parse_created_utc(data.get("created_utc")),
            metadata={
                "external_id": data.get("name"),
                "subreddit": subreddit,
                "upvotes": data.get("score", 0),
                "author": data.get("author"),
                "permalink": data.get("permalink"),
                "content_type": "post",
                "fetch_method": "reddit_json",
            },
        )

    def _comment_to_record(self, subreddit: str, data: dict[str, Any]) -> RawRecord | None:
        body = (data.get("body") or "").strip()
        if not body or body in {"[removed]", "[deleted]"}:
            return None

        text = truncate_reddit_text(body)
        if not text:
            return None

        return RawRecord(
            source="reddit",
            text=text,
            rating=None,
            review_date=self._parse_created_utc(data.get("created_utc")),
            metadata={
                "external_id": data.get("name"),
                "subreddit": subreddit,
                "upvotes": data.get("score", 0),
                "author": data.get("author"),
                "parent_id": data.get("parent_id"),
                "permalink": data.get("permalink"),
                "content_type": "comment",
                "fetch_method": "reddit_json",
            },
        )

    @staticmethod
    def _parse_created_utc(value: Any) -> datetime | None:
        if value is None:
            return None
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _post_id_from_external_id(external_id: str | None) -> str | None:
        if not external_id:
            return None
        if external_id.startswith("t3_"):
            return external_id.removeprefix("t3_")
        return external_id
