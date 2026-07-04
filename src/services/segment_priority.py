"""Segment priority ranking for Executive Summary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.db.models import Segment


@dataclass
class SegmentPriorityItem:
    segment_name: str
    rank: int
    size: int
    pct_of_analyzed: float
    negative_pct: float
    rec_complaint_pct: float
    pain_index: float
    priority_score: float
    trust_score: float | None = None
    top_frustration: str | None = None
    is_recommended: bool = False
    low_sample: bool = False


@dataclass
class SegmentPriorityData:
    items: list[SegmentPriorityItem] = field(default_factory=list)
    recommended_segment: str | None = None
    recommended_rationale: str | None = None
    total_analyzed: int = 0
    db_connected: bool = False


def compute_segment_priorities(
    rows: list[dict[str, Any]],
    segments: list[Segment] | None = None,
    *,
    min_recommended_sample: int = 5,
) -> SegmentPriorityData:
    """Rank segments by size × pain (negative % + rec-complaint %)."""
    if not rows:
        return SegmentPriorityData(total_analyzed=0)

    segment_lookup = {segment.segment_name: segment for segment in (segments or [])}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        segment = row.get("user_segment")
        if not segment:
            continue
        grouped.setdefault(str(segment), []).append(row)

    if not grouped:
        return SegmentPriorityData(total_analyzed=len(rows))

    total_analyzed = len(rows)
    ranked: list[dict[str, Any]] = []
    for segment_name, segment_rows in grouped.items():
        size = len(segment_rows)
        negative_count = sum(1 for row in segment_rows if row.get("sentiment") == "negative")
        rec_count = sum(1 for row in segment_rows if row.get("recommendation_complaint"))
        negative_pct = round(negative_count / size * 100, 1)
        rec_complaint_pct = round(rec_count / size * 100, 1)
        pain_index = round(negative_pct + rec_complaint_pct, 1)
        priority_score = round(size * pain_index, 1)

        collective = segment_lookup.get(segment_name)
        trust_score = collective.recommendation_trust_score if collective else None
        top_frustration = (
            collective.top_frustrations[0]
            if collective and collective.top_frustrations
            else None
        )

        ranked.append(
            {
                "segment_name": segment_name,
                "size": size,
                "pct_of_analyzed": round(size / total_analyzed * 100, 1),
                "negative_pct": negative_pct,
                "rec_complaint_pct": rec_complaint_pct,
                "pain_index": pain_index,
                "priority_score": priority_score,
                "trust_score": trust_score,
                "top_frustration": top_frustration,
            }
        )

    ranked.sort(key=lambda item: (-item["priority_score"], -item["size"], item["segment_name"]))

    recommended_raw: dict[str, Any] | None = None
    for item in ranked:
        if item["size"] >= min_recommended_sample:
            recommended_raw = item
            break
    if recommended_raw is None and ranked:
        recommended_raw = ranked[0]

    items: list[SegmentPriorityItem] = []
    for index, item in enumerate(ranked, start=1):
        is_recommended = (
            recommended_raw is not None
            and item["segment_name"] == recommended_raw["segment_name"]
        )
        items.append(
            SegmentPriorityItem(
                segment_name=item["segment_name"],
                rank=index,
                size=item["size"],
                pct_of_analyzed=item["pct_of_analyzed"],
                negative_pct=item["negative_pct"],
                rec_complaint_pct=item["rec_complaint_pct"],
                pain_index=item["pain_index"],
                priority_score=item["priority_score"],
                trust_score=item["trust_score"],
                top_frustration=item["top_frustration"],
                is_recommended=is_recommended,
                low_sample=is_recommended and item["size"] < min_recommended_sample,
            )
        )

    rationale: str | None = None
    recommended_name: str | None = None
    if recommended_raw:
        recommended_name = recommended_raw["segment_name"]
        frustration = recommended_raw["top_frustration"]
        frustration_text = f' Top frustration: "{frustration}".' if frustration else ""
        rationale = (
            f"Largest impact opportunity — {recommended_raw['size']} analyzed reviews "
            f"({recommended_raw['pct_of_analyzed']}% of sample), "
            f"{recommended_raw['negative_pct']}% negative sentiment, "
            f"{recommended_raw['rec_complaint_pct']}% recommendation complaints."
            f"{frustration_text}"
        )

    return SegmentPriorityData(
        items=items,
        recommended_segment=recommended_name,
        recommended_rationale=rationale,
        total_analyzed=total_analyzed,
    )
