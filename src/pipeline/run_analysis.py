"""CLI entry point for per-review analysis pipeline."""

from __future__ import annotations

import argparse
import logging
import sys

from src.analysis.analysis_pipeline import AnalysisPipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run per-review AI analysis and embeddings")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of unanalyzed reviews to process",
    )
    args = parser.parse_args(argv)

    try:
        result = AnalysisPipeline().run(limit=args.limit)
    except Exception as exc:
        logger.error("Analysis pipeline failed: %s", exc)
        return 1

    logger.info("Reviews fetched: %s", result.reviews_fetched)
    logger.info(
        "Analysis — attempted=%s analyzed=%s skipped=%s failed=%s",
        result.analysis.attempted,
        result.analysis.analyzed,
        result.analysis.skipped,
        result.analysis.failed,
    )
    logger.info(
        "Embeddings — attempted=%s embedded=%s skipped=%s failed=%s",
        result.embeddings.attempted,
        result.embeddings.embedded,
        result.embeddings.skipped,
        result.embeddings.failed,
    )
    logger.info("Marked analyzed: %s", result.marked_analyzed)

    if result.analysis.failed or result.embeddings.failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
