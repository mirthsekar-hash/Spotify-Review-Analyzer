"""Discovery journey chain builder from per-review analysis."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from src.db.client import check_connection
from src.db.repositories.analysis_repo import AnalysisRepository

JOURNEY_STAGES = ("goal", "behavior", "challenge", "workaround", "outcome")
STAGE_LABELS = {
    "goal": "User goal",
    "behavior": "Listening behavior",
    "challenge": "Discovery challenge",
    "workaround": "Workaround",
    "outcome": "Desired outcome",
}
MAX_STEP_LENGTH = 60


@dataclass
class JourneyPath:
    steps: tuple[str, str, str, str, str]
    frequency: int
    review_ids: list[UUID] = field(default_factory=list)
    negative_count: int = 0

    @property
    def negative_pct(self) -> float:
        if self.frequency == 0:
            return 0.0
        return round(self.negative_count / self.frequency * 100, 1)

    @property
    def summary(self) -> str:
        return " → ".join(self.steps)


@dataclass
class JourneyExplorerData:
    paths: list[JourneyPath] = field(default_factory=list)
    total_analyzed: int = 0
    chain_count: int = 0
    db_connected: bool = False


@dataclass
class SankeyDiagramData:
    labels: list[str] = field(default_factory=list)
    sources: list[int] = field(default_factory=list)
    targets: list[int] = field(default_factory=list)
    values: list[int] = field(default_factory=list)
    link_labels: list[str] = field(default_factory=list)


def normalize_step(value: str, *, max_length: int = MAX_STEP_LENGTH) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip())
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 1].rstrip() + "…"


def infer_desired_outcome(user_goal: str) -> str:
    goal = user_goal.strip().lower()
    if any(token in goal for token in ("discover", "new artist", "explore", "variety", "fresh")):
        return "Find fresh music"
    if any(token in goal for token in ("mood", "relax", "focus", "workout", "study")):
        return "Music that fits the moment"
    if any(token in goal for token in ("playlist", "mix", "party", "share")):
        return "Better curated listening"
    if any(token in goal for token in ("genre", "artist", "album")):
        return "Deeper catalog exploration"
    return normalize_step(user_goal, max_length=40) or "Better discovery experience"


def build_chain_from_row(row: dict) -> tuple[str, str, str, str, str] | None:
    goal = row.get("user_goal")
    behavior = row.get("listening_behavior")
    challenge = row.get("discovery_challenge")
    workaround = row.get("primary_problem")
    if not all(value and str(value).strip() for value in (goal, behavior, challenge, workaround)):
        return None

    return (
        normalize_step(str(goal)),
        normalize_step(str(behavior)),
        normalize_step(str(challenge)),
        normalize_step(str(workaround)),
        infer_desired_outcome(str(goal)),
    )


def aggregate_journey_paths(
    rows: list[dict],
    *,
    limit: int = 5,
) -> list[JourneyPath]:
    grouped: dict[tuple[str, str, str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        chain = build_chain_from_row(row)
        if not chain:
            continue
        grouped[chain].append(row)

    paths: list[JourneyPath] = []
    for steps, matching_rows in grouped.items():
        review_ids = [UUID(str(row["review_id"])) for row in matching_rows if row.get("review_id")]
        negative_count = sum(1 for row in matching_rows if row.get("sentiment") == "negative")
        paths.append(
            JourneyPath(
                steps=steps,
                frequency=len(matching_rows),
                review_ids=review_ids,
                negative_count=negative_count,
            )
        )

    paths.sort(key=lambda item: (-item.frequency, item.summary))
    return paths[:limit]


def build_sankey_diagram(paths: list[JourneyPath]) -> SankeyDiagramData:
    if not paths:
        return SankeyDiagramData()

    link_counter: Counter[tuple[str, str]] = Counter()
    for path in paths:
        for index in range(len(path.steps) - 1):
            source = f"{STAGE_LABELS[JOURNEY_STAGES[index]]}: {path.steps[index]}"
            target = f"{STAGE_LABELS[JOURNEY_STAGES[index + 1]]}: {path.steps[index + 1]}"
            link_counter[(source, target)] += path.frequency

    labels = list(
        dict.fromkeys(
            label
            for source, target in link_counter
            for label in (source, target)
        )
    )
    label_to_index = {label: index for index, label in enumerate(labels)}

    sources: list[int] = []
    targets: list[int] = []
    values: list[int] = []
    link_labels: list[str] = []
    for (source, target), value in link_counter.items():
        sources.append(label_to_index[source])
        targets.append(label_to_index[target])
        values.append(value)
        link_labels.append(f"{source.split(': ', 1)[-1]} → {target.split(': ', 1)[-1]}")

    return SankeyDiagramData(
        labels=labels,
        sources=sources,
        targets=targets,
        values=values,
        link_labels=link_labels,
    )


class JourneyService:
    def __init__(self, analysis_repo: AnalysisRepository | None = None) -> None:
        self._analysis_repo = analysis_repo or AnalysisRepository()

    def get_journey_paths(self, *, limit: int = 5) -> JourneyExplorerData:
        if not check_connection():
            return JourneyExplorerData(db_connected=False)

        rows = self._analysis_repo.get_collective_rows()
        paths = aggregate_journey_paths(rows, limit=limit)
        return JourneyExplorerData(
            paths=paths,
            total_analyzed=len(rows),
            chain_count=sum(path.frequency for path in paths),
            db_connected=True,
        )
