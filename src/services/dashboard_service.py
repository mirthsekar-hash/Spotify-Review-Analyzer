"""Dashboard KPI queries and aggregations for Streamlit pages."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.analysis.prompts import load_prompt
from src.db.client import check_connection
from src.db.models import ReviewSource, RootCause, Segment, Sentiment, Theme, UnmetNeed
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.pipeline_runs_repo import PipelineRunsRepository
from src.db.repositories.reviews_repo import ReviewsRepository
from src.db.repositories.root_causes_repo import RootCausesRepository
from src.db.repositories.segments_repo import SegmentsRepository
from src.db.repositories.themes_repo import ThemesRepository
from src.db.repositories.unmet_needs_repo import UnmetNeedsRepository
from src.llm.structured import structured_completion
from src.schemas.executive_summary import ExecutiveSummaryOutput, format_executive_summary_markdown

SENTIMENTS: tuple[Sentiment, ...] = ("positive", "negative", "neutral", "mixed")
SOURCES: tuple[ReviewSource, ...] = ("playstore", "appstore", "reddit")
SENTIMENT_SCORES: dict[Sentiment, float] = {
    "positive": 1.0,
    "mixed": 0.25,
    "neutral": 0.0,
    "negative": -1.0,
}
SOURCE_LABELS = {
    "playstore": "Play Store",
    "appstore": "App Store",
    "reddit": "Reddit",
}


@dataclass
class SentimentBreakdown:
    counts: dict[Sentiment, int] = field(
        default_factory=lambda: {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    )
    total: int = 0
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0
    mixed_pct: float = 0.0


@dataclass
class PipelineRunSummary:
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutiveSummaryData:
    total_reviews: int = 0
    total_analyzed: int = 0
    pending_analysis: int = 0
    top_discovery_challenge: str | None = None
    top_discovery_challenge_count: int = 0
    most_affected_segment: str | None = None
    segment_negative_rate: float | None = None
    recommendation_trust_score: float | None = None
    sentiment: SentimentBreakdown = field(default_factory=SentimentBreakdown)
    db_connected: bool = False
    last_pipeline_run: PipelineRunSummary | None = None


@dataclass
class SourceMetrics:
    source: ReviewSource
    review_count: int = 0
    analyzed_count: int = 0
    avg_rating: float | None = None
    rec_complaint_pct: float | None = None
    avg_sentiment_score: float | None = None
    sentiment: SentimentBreakdown = field(default_factory=SentimentBreakdown)
    top_complaints: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class SourceAnalysisData:
    sources: dict[ReviewSource, SourceMetrics] = field(default_factory=dict)
    db_connected: bool = False
    total_reviews: int = 0
    total_analyzed: int = 0


@dataclass
class DiscoveryChallengeStats:
    challenge: str
    frequency: int
    negative_pct: float
    affected_segments: list[str] = field(default_factory=list)
    avg_sentiment_score: float | None = None


@dataclass
class ExecutiveAiSummaryResult:
    output: ExecutiveSummaryOutput | None = None
    theme_count: int = 0
    segment_count: int = 0
    root_cause_count: int = 0
    unmet_need_count: int = 0
    available: bool = True
    reason: str | None = None


@dataclass
class DiscoveryChallengesData:
    challenges: list[DiscoveryChallengeStats] = field(default_factory=list)
    db_connected: bool = False
    total_analyzed: int = 0


def compute_sentiment_breakdown(rows: list[dict[str, Any]]) -> SentimentBreakdown:
    counts: dict[Sentiment, int] = {key: 0 for key in SENTIMENTS}
    for row in rows:
        sentiment = row.get("sentiment")
        if sentiment in counts:
            counts[sentiment] += 1

    total = sum(counts.values())
    if total == 0:
        return SentimentBreakdown(counts=counts, total=0)

    return SentimentBreakdown(
        counts=counts,
        total=total,
        positive_pct=round(counts["positive"] / total * 100, 1),
        negative_pct=round(counts["negative"] / total * 100, 1),
        neutral_pct=round(counts["neutral"] / total * 100, 1),
        mixed_pct=round(counts["mixed"] / total * 100, 1),
    )


def compute_top_discovery_challenge(rows: list[dict[str, Any]]) -> tuple[str | None, int]:
    challenges = [
        str(row["discovery_challenge"]).strip()
        for row in rows
        if row.get("discovery_challenge") and str(row["discovery_challenge"]).strip()
    ]
    if not challenges:
        return None, 0

    counter = Counter(challenges)
    challenge, count = counter.most_common(1)[0]
    return challenge, count


def compute_most_affected_segment(rows: list[dict[str, Any]]) -> tuple[str | None, float | None]:
    segment_totals: dict[str, int] = {}
    segment_negatives: dict[str, int] = {}

    for row in rows:
        segment = row.get("user_segment")
        if not segment:
            continue
        segment_totals[segment] = segment_totals.get(segment, 0) + 1
        if row.get("sentiment") == "negative":
            segment_negatives[segment] = segment_negatives.get(segment, 0) + 1

    if not segment_totals:
        return None, None

    best_segment: str | None = None
    best_rate = -1.0
    for segment, total in segment_totals.items():
        negative_rate = segment_negatives.get(segment, 0) / total
        if negative_rate > best_rate:
            best_rate = negative_rate
            best_segment = segment

    return best_segment, round(best_rate * 100, 1)


def compute_recommendation_trust_score(rows: list[dict[str, Any]]) -> float | None:
    negative_rows = [row for row in rows if row.get("sentiment") == "negative"]
    if not negative_rows:
        return None

    complaint_count = sum(1 for row in negative_rows if row.get("recommendation_complaint"))
    complaint_rate = complaint_count / len(negative_rows)
    return round((1 - complaint_rate) * 100, 1)


def compute_avg_sentiment_score(rows: list[dict[str, Any]]) -> float | None:
    scores = [
        SENTIMENT_SCORES[sentiment]
        for row in rows
        if (sentiment := row.get("sentiment")) in SENTIMENT_SCORES
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)


def compute_rec_complaint_pct(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    complaints = sum(1 for row in rows if row.get("recommendation_complaint"))
    return round(complaints / len(rows) * 100, 1)


def compute_avg_rating(rows: list[dict[str, Any]]) -> float | None:
    ratings = [row["rating"] for row in rows if row.get("rating") is not None]
    if not ratings:
        return None
    return round(sum(ratings) / len(ratings), 2)


def compute_top_complaints(
    rows: list[dict[str, Any]],
    limit: int = 5,
) -> list[tuple[str, int]]:
    problems = [
        str(row["primary_problem"]).strip()
        for row in rows
        if row.get("primary_problem") and str(row["primary_problem"]).strip()
    ]
    if not problems:
        return []
    return Counter(problems).most_common(limit)


def compute_source_metrics(
    source: ReviewSource,
    review_count: int,
    analyzed_rows: list[dict[str, Any]],
) -> SourceMetrics:
    return SourceMetrics(
        source=source,
        review_count=review_count,
        analyzed_count=len(analyzed_rows),
        avg_rating=compute_avg_rating(analyzed_rows),
        rec_complaint_pct=compute_rec_complaint_pct(analyzed_rows),
        avg_sentiment_score=compute_avg_sentiment_score(analyzed_rows),
        sentiment=compute_sentiment_breakdown(analyzed_rows),
        top_complaints=compute_top_complaints(analyzed_rows),
    )


def compute_top_discovery_challenges(
    rows: list[dict[str, Any]],
    limit: int = 10,
) -> list[DiscoveryChallengeStats]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        challenge = row.get("discovery_challenge")
        if not challenge or not str(challenge).strip():
            continue
        key = str(challenge).strip()
        grouped.setdefault(key, []).append(row)

    stats: list[DiscoveryChallengeStats] = []
    for challenge, challenge_rows in grouped.items():
        negative_count = sum(1 for row in challenge_rows if row.get("sentiment") == "negative")
        segment_counter = Counter(
            str(row["user_segment"]).strip()
            for row in challenge_rows
            if row.get("user_segment") and str(row["user_segment"]).strip()
        )
        stats.append(
            DiscoveryChallengeStats(
                challenge=challenge,
                frequency=len(challenge_rows),
                negative_pct=round(negative_count / len(challenge_rows) * 100, 1),
                affected_segments=[name for name, _ in segment_counter.most_common(3)],
                avg_sentiment_score=compute_avg_sentiment_score(challenge_rows),
            )
        )

    stats.sort(key=lambda item: (-item.frequency, item.challenge))
    return stats[:limit]


def group_rows_by_source(rows: list[dict[str, Any]]) -> dict[ReviewSource, list[dict[str, Any]]]:
    grouped: dict[ReviewSource, list[dict[str, Any]]] = {source: [] for source in SOURCES}
    for row in rows:
        source = row.get("source")
        if source in grouped:
            grouped[source].append(row)
    return grouped


def _format_themes_for_prompt(themes: list[Theme]) -> str:
    if not themes:
        return "No themes available."
    lines = []
    for theme in themes[:8]:
        segments = ", ".join(theme.affected_segments) or "n/a"
        impact = f"{theme.impact_score:.0f}" if theme.impact_score is not None else "n/a"
        lines.append(
            f"- {theme.theme_name} (frequency={theme.frequency}, impact={impact}, "
            f"segments={segments})"
        )
    return "\n".join(lines)


def _format_segments_for_prompt(segments: list[Segment]) -> str:
    if not segments:
        return "No segments available."
    lines = []
    for segment in segments:
        frustrations = "; ".join(segment.top_frustrations[:3]) or "n/a"
        lines.append(
            f"- {segment.segment_name} (size={segment.size}, frustrations={frustrations})"
        )
    return "\n".join(lines)


def _format_root_causes_for_prompt(root_causes: list[RootCause]) -> str:
    if not root_causes:
        return "No root causes available."
    lines = []
    for item in root_causes[:5]:
        segments = ", ".join(item.affected_segments) or "n/a"
        lines.append(f"- {item.root_cause} (frequency={item.frequency}, segments={segments})")
    return "\n".join(lines)


def _format_unmet_needs_for_prompt(needs: list[UnmetNeed]) -> str:
    if not needs:
        return "No unmet needs available."
    lines = []
    for need in needs[:5]:
        score = f"{need.opportunity_score:.2f}" if need.opportunity_score is not None else "n/a"
        lines.append(f"- {need.need} (frequency={need.frequency}, opportunity={score})")
    return "\n".join(lines)


def build_executive_summary_user_content(
    kpis: ExecutiveSummaryData,
    themes: list[Theme],
    segments: list[Segment],
    root_causes: list[RootCause],
    unmet_needs: list[UnmetNeed],
) -> str:
    sentiment = kpis.sentiment
    trust = (
        f"{kpis.recommendation_trust_score:.0f}/100"
        if kpis.recommendation_trust_score is not None
        else "n/a"
    )
    segment_label = kpis.most_affected_segment or "n/a"
    segment_rate = (
        f"{kpis.segment_negative_rate}% negative"
        if kpis.segment_negative_rate is not None
        else "n/a"
    )
    return (
        f"REVIEW KPIs:\n"
        f"- Total reviews: {kpis.total_reviews}\n"
        f"- Analyzed reviews: {kpis.total_analyzed}\n"
        f"- Sentiment: positive {sentiment.positive_pct}%, negative {sentiment.negative_pct}%, "
        f"neutral {sentiment.neutral_pct}%, mixed {sentiment.mixed_pct}%\n"
        f"- Top discovery challenge: {kpis.top_discovery_challenge or 'n/a'} "
        f"({kpis.top_discovery_challenge_count} reviews)\n"
        f"- Most affected segment: {segment_label} ({segment_rate})\n"
        f"- Recommendation trust score: {trust}\n\n"
        f"THEMES:\n{_format_themes_for_prompt(themes)}\n\n"
        f"SEGMENTS:\n{_format_segments_for_prompt(segments)}\n\n"
        f"ROOT CAUSES:\n{_format_root_causes_for_prompt(root_causes)}\n\n"
        f"UNMET NEEDS:\n{_format_unmet_needs_for_prompt(unmet_needs)}"
    )


def references_collective_data(
    output: ExecutiveSummaryOutput,
    theme_names: set[str],
    segment_names: set[str],
) -> bool:
    corpus = " ".join([output.summary, output.top_opportunity, *output.key_findings]).lower()
    if theme_names and any(name.lower() in corpus for name in theme_names):
        return True
    if segment_names and any(name.lower() in corpus for name in segment_names):
        return True
    return not theme_names and not segment_names


class DashboardService:
    def __init__(
        self,
        reviews_repo: ReviewsRepository | None = None,
        analysis_repo: AnalysisRepository | None = None,
        pipeline_runs_repo: PipelineRunsRepository | None = None,
        themes_repo: ThemesRepository | None = None,
        segments_repo: SegmentsRepository | None = None,
        root_causes_repo: RootCausesRepository | None = None,
        unmet_needs_repo: UnmetNeedsRepository | None = None,
    ) -> None:
        self._reviews_repo = reviews_repo or ReviewsRepository()
        self._analysis_repo = analysis_repo or AnalysisRepository()
        self._pipeline_runs_repo = pipeline_runs_repo or PipelineRunsRepository()
        self._themes_repo = themes_repo or ThemesRepository()
        self._segments_repo = segments_repo or SegmentsRepository()
        self._root_causes_repo = root_causes_repo or RootCausesRepository()
        self._unmet_needs_repo = unmet_needs_repo or UnmetNeedsRepository()
        self._executive_prompt = load_prompt("executive_summary.txt")

    def get_executive_summary(self) -> ExecutiveSummaryData:
        db_connected = check_connection()
        if not db_connected:
            return ExecutiveSummaryData(db_connected=False)

        total_reviews = self._reviews_repo.count_total()
        total_analyzed = self._reviews_repo.count_analyzed()
        analysis_rows = self._analysis_repo.get_dashboard_fields()
        sentiment = compute_sentiment_breakdown(analysis_rows)
        top_challenge, top_count = compute_top_discovery_challenge(analysis_rows)
        segment, segment_rate = compute_most_affected_segment(analysis_rows)
        trust_score = compute_recommendation_trust_score(analysis_rows)
        last_run_row = self._pipeline_runs_repo.get_latest()
        last_run = _to_pipeline_run_summary(last_run_row) if last_run_row else None

        return ExecutiveSummaryData(
            total_reviews=total_reviews,
            total_analyzed=total_analyzed,
            pending_analysis=max(total_reviews - total_analyzed, 0),
            top_discovery_challenge=top_challenge,
            top_discovery_challenge_count=top_count,
            most_affected_segment=segment,
            segment_negative_rate=segment_rate,
            recommendation_trust_score=trust_score,
            sentiment=sentiment,
            db_connected=True,
            last_pipeline_run=last_run,
        )

    def generate_executive_summary(self) -> ExecutiveAiSummaryResult | None:
        if not check_connection():
            return None

        kpis = self.get_executive_summary()
        if not kpis.db_connected or kpis.total_analyzed == 0:
            return None

        themes = self._themes_repo.get_all()
        segments = self._segments_repo.get_all()
        root_causes = self._root_causes_repo.get_all()
        unmet_needs = self._unmet_needs_repo.get_all()

        if not themes and not segments:
            return ExecutiveAiSummaryResult(
                available=False,
                reason="Collective analysis has not produced themes or segments yet.",
            )

        user_content = build_executive_summary_user_content(
            kpis,
            themes,
            segments,
            root_causes,
            unmet_needs,
        )
        raw_output = structured_completion(
            system_prompt=self._executive_prompt,
            user_content=user_content,
            schema_model=ExecutiveSummaryOutput,
        )
        if not isinstance(raw_output, ExecutiveSummaryOutput):
            raise TypeError("structured_completion returned unexpected type")

        theme_names = {theme.theme_name for theme in themes}
        segment_names = {segment.segment_name for segment in segments}
        if not references_collective_data(raw_output, theme_names, segment_names):
            raise ValueError(
                "Executive summary did not reference themes or segments from the database"
            )

        return ExecutiveAiSummaryResult(
            output=raw_output,
            theme_count=len(themes),
            segment_count=len(segments),
            root_cause_count=len(root_causes),
            unmet_need_count=len(unmet_needs),
            available=True,
        )

    def get_source_analysis(self) -> SourceAnalysisData:
        db_connected = check_connection()
        if not db_connected:
            return SourceAnalysisData(db_connected=False)

        review_counts = self._reviews_repo.count_by_source()
        analysis_rows = self._analysis_repo.get_source_analysis_rows()
        grouped = group_rows_by_source(analysis_rows)

        sources = {
            source: compute_source_metrics(source, review_counts.get(source, 0), grouped[source])
            for source in SOURCES
        }

        return SourceAnalysisData(
            sources=sources,
            db_connected=True,
            total_reviews=sum(review_counts.values()),
            total_analyzed=len(analysis_rows),
        )

    def get_top_discovery_challenges(self, limit: int = 10) -> DiscoveryChallengesData:
        db_connected = check_connection()
        if not db_connected:
            return DiscoveryChallengesData(db_connected=False)

        analysis_rows = self._analysis_repo.get_dashboard_fields()
        challenges = compute_top_discovery_challenges(analysis_rows, limit=limit)

        return DiscoveryChallengesData(
            challenges=challenges,
            db_connected=True,
            total_analyzed=self._analysis_repo.count_total(),
        )


def _to_pipeline_run_summary(row: dict[str, Any]) -> PipelineRunSummary:
    return PipelineRunSummary(
        status=row["status"],
        started_at=row.get("started_at"),
        finished_at=row.get("finished_at"),
        stats=row.get("stats") or {},
    )
