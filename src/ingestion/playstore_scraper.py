"""Google Play Store review scraper."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from google_play_scraper import Sort, reviews
from google_play_scraper.exceptions import NotFoundError

from app.config import Settings, get_settings
from src.db.models import RawRecord, ReviewSource, compute_content_hash, normalize_text
from src.ingestion.base import IngestConfig, SourceAdapter

logger = logging.getLogger(__name__)


def _record_key(record: RawRecord) -> str:
    external_id = record.metadata.get("external_id")
    if external_id:
        return str(external_id)
    return compute_content_hash(normalize_text(record.text), record.source)


class PlayStoreScraper(SourceAdapter):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def source_name(self) -> ReviewSource:
        return "playstore"

    def fetch(self, config: IngestConfig | None = None) -> list[RawRecord]:
        cfg = config or IngestConfig(
            app_id=self._settings.spotify_play_store_app_id,
            target_count=self._settings.min_reviews_playstore,
        )

        collected: dict[str, RawRecord] = {}
        sort_orders = [Sort.NEWEST, Sort.MOST_RELEVANT, Sort.RATING]

        for sort_order in sort_orders:
            try:
                self._fetch_sorted(cfg, sort_order, collected)
            except NotFoundError as exc:
                logger.error("Play Store app not found: %s", exc)
                break
            except Exception as exc:
                logger.warning("Play Store fetch failed for sort %s: %s", sort_order, exc)

            if len(collected) >= cfg.target_count:
                break

        keyword_records = self._fetch_keyword_filtered(cfg, collected)
        for record in keyword_records:
            collected[_record_key(record)] = record

        return list(collected.values())

    def _fetch_sorted(
        self,
        config: IngestConfig,
        sort_order: Sort,
        collected: dict[str, RawRecord],
    ) -> None:
        continuation_token = None
        batch_size = 200

        while len(collected) < config.target_count:
            kwargs: dict[str, Any] = {
                "app_id": config.app_id,
                "lang": config.language,
                "country": config.country,
                "sort": sort_order,
                "count": batch_size,
            }
            if continuation_token:
                kwargs["continuation_token"] = continuation_token

            batch, continuation_token = reviews(**kwargs)
            if not batch:
                break

            for item in batch:
                record = self._to_raw_record(item)
                if record.text.strip():
                    collected[_record_key(record)] = record

            if not continuation_token:
                break

    def _fetch_keyword_filtered(
        self,
        config: IngestConfig,
        existing: dict[str, RawRecord],
    ) -> list[RawRecord]:
        """Supplement with reviews matching discovery-related keywords."""
        if len(existing) >= config.target_count:
            return []

        keyword_hits: list[RawRecord] = []
        seen_ids = {r.metadata.get("external_id") for r in existing.values()}

        try:
            batch, _ = reviews(
                app_id=config.app_id,
                lang=config.language,
                country=config.country,
                sort=Sort.NEWEST,
                count=min(500, config.target_count * 2),
            )
        except Exception as exc:
            logger.warning("Keyword filter fetch failed: %s", exc)
            return []

        lowered_keywords = [kw.lower() for kw in config.keywords]
        for item in batch:
            content = (item.get("content") or "").lower()
            if not any(keyword in content for keyword in lowered_keywords):
                continue
            record = self._to_raw_record(item)
            external_id = record.metadata.get("external_id")
            if external_id in seen_ids:
                continue
            keyword_hits.append(record)
            if len(existing) + len(keyword_hits) >= config.target_count:
                break

        return keyword_hits

    def _to_raw_record(self, item: dict[str, Any]) -> RawRecord:
        review_date = item.get("at")
        if isinstance(review_date, datetime) and review_date.tzinfo is None:
            review_date = review_date.replace(tzinfo=timezone.utc)

        return RawRecord(
            source="playstore",
            text=item.get("content") or "",
            rating=item.get("score"),
            review_date=review_date,
            metadata={
                "reviewer_name": item.get("userName"),
                "external_id": item.get("reviewId"),
                "helpful_count": item.get("thumbsUpCount", 0),
                "review_created_version": item.get("reviewCreatedVersion"),
                "fetch_method": "google_play_scraper",
                "raw": {
                    "reply_content": item.get("replyContent"),
                    "replied_at": str(item.get("repliedAt")) if item.get("repliedAt") else None,
                },
            },
        )
