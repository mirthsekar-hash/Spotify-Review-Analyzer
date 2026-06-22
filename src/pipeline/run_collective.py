"""CLI entry point for collective analysis engines."""

from __future__ import annotations

import argparse
import logging
import sys

from src.analysis.root_cause_engine import RootCauseEngine
from src.analysis.segment_engine import SegmentEngine
from src.analysis.theme_extractor import ThemeExtractor
from src.analysis.unmet_need_detector import UnmetNeedDetector

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STEPS = ("themes", "segments", "root-causes", "unmet-needs", "both", "all")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run collective analysis engines")
    parser.add_argument(
        "--step",
        choices=STEPS,
        default="all",
        help="Which collective engine(s) to run",
    )
    args = parser.parse_args(argv)

    run_themes = args.step in ("themes", "both", "all")
    run_segments = args.step in ("segments", "both", "all")
    run_root_causes = args.step in ("root-causes", "all")
    run_unmet_needs = args.step in ("unmet-needs", "all")

    try:
        if run_themes:
            theme_result = ThemeExtractor().run()
            logger.info(
                "Themes — written=%s from %s analyzed reviews: %s",
                theme_result.themes_written,
                theme_result.analyzed_review_count,
                ", ".join(theme_result.theme_names),
            )

        if run_segments:
            segment_result = SegmentEngine().run()
            logger.info(
                "Segments — written=%s from %s analyzed reviews: %s",
                segment_result.segments_written,
                segment_result.analyzed_review_count,
                ", ".join(segment_result.segment_names),
            )

        if run_root_causes:
            root_cause_result = RootCauseEngine().run()
            logger.info(
                "Root causes — written=%s using %s themes: %s",
                root_cause_result.root_causes_written,
                root_cause_result.themes_used,
                ", ".join(root_cause_result.root_cause_names),
            )

        if run_unmet_needs:
            unmet_need_result = UnmetNeedDetector().run()
            logger.info(
                "Unmet needs — written=%s from %s gap pairs: %s",
                unmet_need_result.needs_written,
                unmet_need_result.gap_pairs_used,
                ", ".join(unmet_need_result.need_names),
            )
    except Exception as exc:
        logger.error("Collective analysis failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
