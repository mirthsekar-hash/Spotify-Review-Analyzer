"""CLI entry point for live ingestion."""

from __future__ import annotations

import argparse
import logging
import sys

from src.ingestion.exceptions import RedditFetchError, ScrapeError
from src.ingestion.service import IngestionService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scrape Play Store, App Store, and Reddit data into Supabase"
    )
    parser.add_argument(
        "--source",
        choices=["playstore", "appstore", "reddit", "stores", "all"],
        default="stores",
        help=(
            "Which source to scrape: playstore, appstore, reddit, "
            "stores (Play + App only), or all (default: stores)"
        ),
    )
    parser.add_argument(
        "--no-reddit-fallback",
        action="store_true",
        help="Do not load reddit_sample.csv when Reddit JSON fetch fails",
    )
    args = parser.parse_args(argv)

    service = IngestionService()
    try:
        if args.source == "playstore":
            result = service.ingest_playstore()
            _log_result("playstore", result)
        elif args.source == "appstore":
            result = service.ingest_appstore()
            _log_result("appstore", result)
        elif args.source == "reddit":
            result = service.ingest_reddit(allow_fallback=not args.no_reddit_fallback)
            _log_result("reddit", result)
        elif args.source == "all":
            results = service.ingest_all_sources()
            _log_result("playstore", results.playstore)
            _log_result("appstore", results.appstore)
            _log_result("reddit", results.reddit)
        else:
            results = service.ingest_all_stores()
            _log_result("playstore", results.playstore)
            _log_result("appstore", results.appstore)
    except (ScrapeError, RedditFetchError) as exc:
        logger.error("Live scrape failed: %s", exc)
        return 1
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc)
        return 1

    return 0


def _log_result(source: str, result) -> None:
    logger.info(
        "%s — fetched=%s normalized=%s stored=%s skipped=%s",
        source,
        result.fetched,
        result.normalized,
        result.stored,
        result.skipped,
    )


if __name__ == "__main__":
    sys.exit(main())
