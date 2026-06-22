"""CLI entry point for the full ingestion + analysis pipeline."""

from __future__ import annotations

import argparse
import logging
import sys

from src.pipeline.orchestrator import PipelineOrchestrator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run full pipeline: parallel ingest → analyze → embed",
    )
    args = parser.parse_args(argv)

    try:
        result = PipelineOrchestrator().run_full_pipeline_sync()
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        return 1

    for source, source_result in result.sources.items():
        if source_result.error:
            logger.warning(
                "%s failed: %s",
                source,
                source_result.error,
            )
        else:
            logger.info(
                "%s — fetched=%s stored=%s new=%s skipped=%s fallback=%s",
                source,
                source_result.fetched,
                source_result.stored,
                source_result.new,
                source_result.skipped,
                source_result.used_fallback,
            )

    logger.info(
        "Pipeline %s — new=%s analyzed=%s embedded=%s duration=%.1fs run_id=%s",
        result.status,
        len(result.new_review_ids),
        result.analyzed_count,
        result.embedded_count,
        result.duration_seconds,
        result.run_id,
    )

    return 0 if result.status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
