"""One-off segment priority analysis from scraped review data."""

from __future__ import annotations

from collections import Counter

from src.deploy.secrets import bootstrap_settings
from src.db.client import check_connection
from src.db.repositories.analysis_repo import EXPECTED_USER_SEGMENTS, AnalysisRepository
from src.db.repositories.reviews_repo import ReviewsRepository
from src.db.repositories.root_causes_repo import RootCausesRepository
from src.db.repositories.segments_repo import SegmentsRepository
from src.db.repositories.themes_repo import ThemesRepository
from src.db.repositories.unmet_needs_repo import UnmetNeedsRepository
from src.services.dashboard_service import compute_most_affected_segment


def main() -> None:
    bootstrap_settings()
    if not check_connection():
        print("DB_NOT_CONNECTED")
        return

    reviews = ReviewsRepository()
    analysis = AnalysisRepository()
    rows = analysis.get_collective_rows()

    print("=== CORPUS ===")
    print(f"Total reviews: {reviews.count_total()}")
    print(f"Analyzed reviews: {reviews.count_analyzed()}")
    print(f"Analysis rows for segment study: {len(rows)}")
    print()

    seg_stats: dict[str, dict] = {}
    for seg in EXPECTED_USER_SEGMENTS:
        seg_rows = [r for r in rows if r.get("user_segment") == seg]
        n = len(seg_rows)
        if n == 0:
            continue
        neg = sum(1 for r in seg_rows if r.get("sentiment") == "negative")
        rec = sum(1 for r in seg_rows if r.get("recommendation_complaint"))
        challenges = Counter(
            str(r.get("discovery_challenge", "")).strip()
            for r in seg_rows
            if r.get("discovery_challenge")
        )
        ratings = [r.get("rating") for r in seg_rows if r.get("rating") is not None]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
        seg_stats[seg] = {
            "size": n,
            "pct_of_analyzed": round(n / len(rows) * 100, 1),
            "negative_pct": round(neg / n * 100, 1),
            "rec_complaint_pct": round(rec / n * 100, 1),
            "avg_rating": avg_rating,
            "top_challenge": challenges.most_common(1)[0] if challenges else ("", 0),
        }

    print("=== SEGMENT METRICS ===")
    for seg, stats in sorted(seg_stats.items(), key=lambda item: -item[1]["size"]):
        challenge, challenge_count = stats["top_challenge"]
        challenge_preview = challenge[:70] + ("..." if len(challenge) > 70 else "")
        print(f"{seg}:")
        print(f"  size={stats['size']} ({stats['pct_of_analyzed']} pct of analyzed)")
        print(f"  negative={stats['negative_pct']} pct, rec_complaint={stats['rec_complaint_pct']} pct")
        print(f"  avg_rating={stats['avg_rating']}, top_challenge={challenge_preview} ({challenge_count})")
    print()

    most_seg, most_rate = compute_most_affected_segment(rows)
    print(f"Most affected segment (exec KPI): {most_seg} ({most_rate} pct negative)")
    print()

    segments = SegmentsRepository().get_all()
    print("=== COLLECTIVE SEGMENTS ===")
    for segment in sorted(segments, key=lambda item: -item.size):
        frustrations = "; ".join(segment.top_frustrations[:2]) if segment.top_frustrations else "n/a"
        print(
            f"{segment.segment_name}: size={segment.size}, trust={segment.recommendation_trust_score}, "
            f"frustrations={frustrations[:100]}"
        )
    print()

    themes = ThemesRepository().get_all()
    print("=== TOP THEMES ===")
    for theme in sorted(themes, key=lambda item: -item.frequency)[:8]:
        affected = ", ".join(theme.affected_segments)
        print(f"{theme.theme_name} (freq={theme.frequency}, impact={theme.impact_score}): {affected}")
    print()

    root_causes = RootCausesRepository().get_all()
    print("=== ROOT CAUSES ===")
    for item in sorted(root_causes, key=lambda row: -row.frequency)[:5]:
        affected = ", ".join(item.affected_segments)
        print(f"{item.root_cause} (freq={item.frequency}): {affected}")
    print()

    unmet = UnmetNeedsRepository().get_all()
    print("=== UNMET NEEDS ===")
    for item in sorted(unmet, key=lambda row: -(row.opportunity_score or 0))[:5]:
        print(f"{item.need} (opp={item.opportunity_score}, freq={item.frequency})")

    # Priority score: size * pain (negative + rec complaint) for product focus
    print()
    print("=== PRIORITY SCORE (size x pain index) ===")
    ranked = []
    for seg, stats in seg_stats.items():
        pain = stats["negative_pct"] + stats["rec_complaint_pct"]
        score = stats["size"] * pain
        ranked.append((seg, score, stats))
    for seg, score, stats in sorted(ranked, key=lambda item: -item[1]):
        print(
            f"{seg}: priority={score:.0f} "
            f"(size={stats['size']}, pain_index={stats['negative_pct'] + stats['rec_complaint_pct']:.1f})"
        )


if __name__ == "__main__":
    main()
