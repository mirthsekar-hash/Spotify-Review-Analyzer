"""Apple App Store review scraper with iTunes RSS fallback."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.config import Settings, get_settings
from src.db.models import RawRecord, ReviewSource, compute_content_hash, normalize_text
from src.ingestion.base import IngestConfig, SourceAdapter

logger = logging.getLogger(__name__)

RSS_SORT_ORDERS = ("mostrecent", "mosthelpful", "favorable", "critical")
RSS_COUNTRIES = (
    "us",
    "gb",
    "in",
    "nz",
    "ie",
    "sg",
    "nl",
    "se",
    "no",
    "dk",
    "it",
    "es",
    "ca",
    "au",
    "br",
    "mx",
    "fr",
    "de",
    "jp",
)
RSS_MAX_PAGES = 10
RSS_REQUEST_TIMEOUT = 30.0
RSS_USER_AGENT = (
    "Mozilla/5.0 (compatible; SpotifyReviewEngine/1.0; +https://github.com/mirthsekar-hash/Spotify-Review-Analyzer)"
)


def _record_key(record: RawRecord) -> str:
    external_id = record.metadata.get("external_id")
    if external_id:
        return str(external_id)
    return compute_content_hash(normalize_text(record.text), record.source)


class AppStoreScraper(SourceAdapter):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def source_name(self) -> ReviewSource:
        return "appstore"

    def fetch(self, config: IngestConfig | None = None) -> list[RawRecord]:
        cfg = config or IngestConfig(
            app_id=self._settings.spotify_app_store_app_id,
            target_count=self._settings.min_reviews_appstore,
        )

        collected: dict[str, RawRecord] = {}

        if self._settings.app_store_use_library:
            try:
                self._fetch_via_library(cfg, collected)
            except Exception as exc:
                logger.warning(
                    "App Store library scraper unavailable or failed, using RSS: %s",
                    exc,
                )

        if len(collected) < cfg.target_count:
            self._fetch_via_rss(cfg, collected)

        keyword_records = self._fetch_keyword_filtered(cfg, collected)
        for record in keyword_records:
            collected[_record_key(record)] = record

        logger.info("App Store fetch collected %s unique reviews", len(collected))
        return list(collected.values())

    def _fetch_via_library(self, config: IngestConfig, collected: dict[str, RawRecord]) -> None:
        try:
            from app_store_scraper import AppStore
        except ImportError as exc:
            raise RuntimeError("app-store-scraper package not installed") from exc

        store = AppStore(
            country=config.country,
            app_name="spotify",
            app_id=config.app_id,
        )
        store.review(how_many=config.target_count)

        for item in store.reviews:
            record = self._library_item_to_record(item)
            if record.text.strip():
                collected[_record_key(record)] = record

    def _fetch_via_rss(self, config: IngestConfig, collected: dict[str, RawRecord]) -> None:
        for country in RSS_COUNTRIES:
            if len(collected) >= config.target_count:
                break

            for sort_order in RSS_SORT_ORDERS:
                if len(collected) >= config.target_count:
                    break

                for page in range(1, RSS_MAX_PAGES + 1):
                    if len(collected) >= config.target_count:
                        break

                    entries = self._fetch_rss_page(country, config.app_id, page, sort_order)
                    if not entries:
                        break

                    for entry in entries:
                        record = self._rss_entry_to_record(
                            entry,
                            sort_order=sort_order,
                            country=country,
                        )
                        if record and record.text.strip():
                            collected[_record_key(record)] = record

                    time.sleep(0.3)

    def _fetch_rss_page(
        self,
        country: str,
        app_id: str,
        page: int,
        sort_order: str,
    ) -> list[dict[str, Any]]:
        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews/"
            f"page={page}/id={app_id}/sortby={sort_order}/json"
        )
        headers = {"User-Agent": RSS_USER_AGENT}
        for attempt in range(3):
            try:
                response = httpx.get(
                    url,
                    timeout=RSS_REQUEST_TIMEOUT,
                    follow_redirects=True,
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    logger.warning(
                        "RSS server error for %s sort %s page %s — skipping sort",
                        country,
                        sort_order,
                        page,
                    )
                    return []
                logger.warning(
                    "RSS fetch failed for %s page %s sort %s (attempt %s): %s",
                    country,
                    page,
                    sort_order,
                    attempt + 1,
                    exc,
                )
                time.sleep(1.5 * (attempt + 1))
                continue
            except Exception as exc:
                logger.warning(
                    "RSS fetch failed for %s page %s sort %s (attempt %s): %s",
                    country,
                    page,
                    sort_order,
                    attempt + 1,
                    exc,
                )
                time.sleep(1.5 * (attempt + 1))
                continue

            feed = payload.get("feed", {})
            entries = feed.get("entry", [])
            if isinstance(entries, dict):
                return [entries]
            if entries:
                return entries
            time.sleep(1.5 * (attempt + 1))

        return []

    def _fetch_keyword_filtered(
        self,
        config: IngestConfig,
        existing: dict[str, RawRecord],
    ) -> list[RawRecord]:
        if len(existing) >= config.target_count:
            return []

        keyword_hits: list[RawRecord] = []
        seen_ids = {record.metadata.get("external_id") for record in existing.values()}
        lowered_keywords = [keyword.lower() for keyword in config.keywords]

        for country in RSS_COUNTRIES:
            if len(existing) + len(keyword_hits) >= config.target_count:
                break

            for sort_order in RSS_SORT_ORDERS:
                if len(existing) + len(keyword_hits) >= config.target_count:
                    break

                for page in range(1, RSS_MAX_PAGES + 1):
                    entries = self._fetch_rss_page(country, config.app_id, page, sort_order)
                    if not entries:
                        break

                    for entry in entries:
                        record = self._rss_entry_to_record(
                            entry,
                            sort_order=sort_order,
                            country=country,
                        )
                        if not record or not record.text.strip():
                            continue

                        content = record.text.lower()
                        if not any(keyword in content for keyword in lowered_keywords):
                            continue

                        external_id = record.metadata.get("external_id")
                        if external_id in seen_ids:
                            continue

                        keyword_hits.append(record)
                        seen_ids.add(external_id)
                        if len(existing) + len(keyword_hits) >= config.target_count:
                            return keyword_hits

                    time.sleep(0.2)

        return keyword_hits

    def _library_item_to_record(self, item: dict[str, Any]) -> RawRecord:
        title = (item.get("title") or "").strip()
        body = (item.get("review") or "").strip()
        text = f"{title}\n{body}".strip() if title and title != body else body or title

        review_date = item.get("date")
        if isinstance(review_date, datetime) and review_date.tzinfo is None:
            review_date = review_date.replace(tzinfo=timezone.utc)

        return RawRecord(
            source="appstore",
            text=text,
            rating=item.get("rating"),
            review_date=review_date,
            metadata={
                "reviewer_name": item.get("userName"),
                "external_id": self._external_id_from_review(item),
                "title": title,
                "fetch_method": "app_store_scraper",
            },
        )

    def _rss_entry_to_record(
        self,
        entry: dict[str, Any],
        *,
        sort_order: str,
        country: str = "us",
    ) -> RawRecord | None:
        rating_label = entry.get("im:rating", {}).get("label")
        if not rating_label:
            return None

        title = entry.get("title", {}).get("label", "").strip()
        content = entry.get("content", {}).get("label") or entry.get("summary", {}).get("label", "")
        text = f"{title}\n{content}".strip() if title and title != content else content.strip()
        if not text:
            return None

        review_date = self._parse_rss_date(entry.get("updated", {}).get("label"))
        external_id = entry.get("id", {}).get("label")

        return RawRecord(
            source="appstore",
            text=text,
            rating=int(rating_label),
            review_date=review_date,
            metadata={
                "reviewer_name": entry.get("author", {}).get("name", {}).get("label"),
                "external_id": external_id,
                "title": title,
                "fetch_method": "itunes_rss",
                "rss_sort": sort_order,
                "country": country,
            },
        )

    @staticmethod
    def _parse_rss_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _external_id_from_review(item: dict[str, Any]) -> str | None:
        for key in ("reviewId", "id"):
            value = item.get(key)
            if value:
                return str(value)

        user_name = item.get("userName")
        review_date = item.get("date")
        review_text = item.get("review")
        if user_name and review_date and review_text:
            return f"{user_name}:{review_date}:{hash(review_text)}"
        return None
