"""Ingestion orchestration: normalize, dedupe, persist."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from app.config import Settings, get_settings
from src.db.models import RawRecord, ReviewSource, UpsertReviewsResult
from src.db.repositories.reviews_repo import ReviewsRepository
from src.ingestion.appstore_scraper import AppStoreScraper
from src.ingestion.csv_importer import CSVImporter
from src.ingestion.exceptions import RedditFetchError, ScrapeError
from src.ingestion.normalizer import Normalizer
from src.ingestion.playstore_scraper import PlayStoreScraper
from src.ingestion.reddit_json_scraper import RedditJsonScraper

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    fetched: int
    normalized: int
    stored: int
    skipped: int
    upsert: UpsertReviewsResult
    used_fallback: bool = False
    new_review_ids: list[UUID] = field(default_factory=list)


@dataclass
class StoreIngestionResult:
    playstore: IngestionResult
    appstore: IngestionResult


@dataclass
class AllSourcesIngestionResult:
    playstore: IngestionResult
    appstore: IngestionResult
    reddit: IngestionResult


class IngestionService:
    def __init__(
        self,
        reviews_repo: ReviewsRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._reviews_repo = reviews_repo or ReviewsRepository()
        self._settings = settings or get_settings()

    def ingest_raw_records(self, records: list[RawRecord]) -> IngestionResult:
        normalizer = Normalizer()
        normalized = normalizer.normalize_batch(records)
        upsert = self._reviews_repo.upsert_batch(normalized)
        return IngestionResult(
            fetched=len(records),
            normalized=len(normalized),
            stored=upsert.stored,
            skipped=len(records) - len(normalized),
            upsert=upsert,
            new_review_ids=upsert.new_review_ids,
        )

    def ingest_csv_bytes(self, data: bytes) -> IngestionResult:
        records = CSVImporter(file_bytes=data).fetch()
        return self.ingest_raw_records(records)

    def ingest_csv_file(self, path: Path) -> IngestionResult:
        records = CSVImporter(file_path=path).fetch()
        return self.ingest_raw_records(records)

    def ingest_playstore(self) -> IngestionResult:
        records = self._fetch_live_records(
            source="playstore",
            minimum=self._settings.min_reviews_playstore,
            fetcher=PlayStoreScraper(self._settings).fetch,
        )
        return self.ingest_raw_records(records)

    def ingest_appstore(self) -> IngestionResult:
        records = self._fetch_live_records(
            source="appstore",
            minimum=self._settings.min_reviews_appstore,
            fetcher=AppStoreScraper(self._settings).fetch,
        )
        return self.ingest_raw_records(records)

    def ingest_reddit(self, *, allow_fallback: bool = True) -> IngestionResult:
        try:
            records = self._fetch_live_records(
                source="reddit",
                minimum=self._settings.min_reviews_reddit,
                fetcher=RedditJsonScraper(self._settings).fetch,
            )
            return self.ingest_raw_records(records)
        except RedditFetchError as exc:
            if not allow_fallback:
                raise
            logger.warning("Reddit live fetch failed (%s); loading fallback CSV", exc)
            result = self.ingest_reddit_fallback_csv()
            result.used_fallback = True
            return result

    def ingest_all_stores(self) -> StoreIngestionResult:
        results: dict[str, IngestionResult] = {}
        errors: dict[str, Exception] = {}

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(self.ingest_playstore): "playstore",
                executor.submit(self.ingest_appstore): "appstore",
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    results[source] = future.result()
                except Exception as exc:
                    errors[source] = exc
                    logger.error("%s ingestion failed: %s", source, exc)

        if errors and len(results) == 0:
            raise ScrapeError(
                "All store ingestion failed: "
                + "; ".join(f"{name}={error}" for name, error in errors.items())
            )
        if "playstore" not in results:
            raise ScrapeError(f"Play Store ingestion failed: {errors.get('playstore')}")
        if "appstore" not in results:
            raise ScrapeError(f"App Store ingestion failed: {errors.get('appstore')}")

        return StoreIngestionResult(
            playstore=results["playstore"],
            appstore=results["appstore"],
        )

    def ingest_all_sources(self) -> AllSourcesIngestionResult:
        results: dict[str, IngestionResult] = {}
        errors: dict[str, Exception] = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.ingest_playstore): "playstore",
                executor.submit(self.ingest_appstore): "appstore",
                executor.submit(self.ingest_reddit): "reddit",
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    results[source] = future.result()
                except Exception as exc:
                    errors[source] = exc
                    logger.error("%s ingestion failed: %s", source, exc)

        if errors and len(results) == 0:
            raise ScrapeError(
                "All source ingestion failed: "
                + "; ".join(f"{name}={error}" for name, error in errors.items())
            )

        if "playstore" not in results:
            raise ScrapeError(f"Play Store ingestion failed: {errors.get('playstore')}")
        if "appstore" not in results:
            raise ScrapeError(f"App Store ingestion failed: {errors.get('appstore')}")
        if "reddit" not in results:
            raise ScrapeError(f"Reddit ingestion failed: {errors.get('reddit')}")

        return AllSourcesIngestionResult(
            playstore=results["playstore"],
            appstore=results["appstore"],
            reddit=results["reddit"],
        )

    def ingest_fallback_csv(self) -> IngestionResult:
        fallback = Path(__file__).resolve().parents[2] / "data" / "fallback" / "playstore_sample.csv"
        if not fallback.exists():
            raise FileNotFoundError(f"Fallback CSV not found: {fallback}")
        return self.ingest_csv_file(fallback)

    def ingest_appstore_fallback_csv(self) -> IngestionResult:
        fallback = Path(__file__).resolve().parents[2] / "data" / "fallback" / "appstore_sample.csv"
        if not fallback.exists():
            raise FileNotFoundError(f"Fallback CSV not found: {fallback}")
        return self.ingest_csv_file(fallback)

    def ingest_reddit_fallback_csv(self) -> IngestionResult:
        fallback = Path(__file__).resolve().parents[2] / "data" / "fallback" / "reddit_sample.csv"
        if not fallback.exists():
            raise FileNotFoundError(f"Fallback CSV not found: {fallback}")
        return self.ingest_csv_file(fallback)

    @staticmethod
    def _fetch_live_records(
        source: ReviewSource,
        minimum: int,
        fetcher,
    ) -> list[RawRecord]:
        records = fetcher()
        live_records = [
            record
            for record in records
            if record.metadata.get("fetch_method")
            not in {None, "csv_import", "csv_fallback"}
        ]
        if not live_records:
            live_records = records

        if not live_records:
            raise ScrapeError(f"{source}: live scrape returned no reviews")

        if len(live_records) < minimum:
            raise ScrapeError(
                f"{source}: live scrape returned {len(live_records)} reviews "
                f"(minimum required: {minimum})"
            )

        return live_records
