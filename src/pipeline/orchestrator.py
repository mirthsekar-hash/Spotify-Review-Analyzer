"""Full pipeline orchestrator: ingest → analyze → embed → collective analysis."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from app.config import Settings, get_settings
from src.analysis.analysis_pipeline import AnalysisPipeline, AnalysisPipelineResult
from src.analysis.root_cause_engine import RootCauseEngine
from src.analysis.segment_engine import SegmentEngine
from src.analysis.theme_extractor import ThemeExtractor
from src.analysis.unmet_need_detector import UnmetNeedDetector
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.pipeline_runs_repo import PipelineRunsRepository
from src.ingestion.service import IngestionResult, IngestionService

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]


@dataclass
class SourceResult:
    fetched: int = 0
    stored: int = 0
    skipped: int = 0
    new: int = 0
    error: str | None = None
    used_fallback: bool = False


@dataclass
class CollectiveEngineStats:
    themes_written: int = 0
    segments_written: int = 0
    root_causes_written: int = 0
    unmet_needs_written: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class CollectiveAnalysisResult:
    run_id: UUID | None = None
    status: Literal["success", "partial", "failed"] = "failed"
    engines: CollectiveEngineStats = field(default_factory=CollectiveEngineStats)
    duration_seconds: float = 0.0
    analyzed_review_count: int = 0
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class PipelineResult:
    run_id: UUID
    sources: dict[str, SourceResult] = field(default_factory=dict)
    analyzed_count: int = 0
    embedded_count: int = 0
    duration_seconds: float = 0.0
    status: Literal["success", "partial", "failed"] = "failed"
    new_review_ids: list[UUID] = field(default_factory=list)
    analysis: AnalysisPipelineResult | None = None
    collective: CollectiveAnalysisResult | None = None


class PipelineOrchestrator:
    SOURCE_ORDER = ("playstore", "appstore", "reddit")

    def __init__(
        self,
        settings: Settings | None = None,
        ingestion_service: IngestionService | None = None,
        analysis_pipeline: AnalysisPipeline | None = None,
        pipeline_runs_repo: PipelineRunsRepository | None = None,
        analysis_repo: AnalysisRepository | None = None,
        theme_extractor: ThemeExtractor | None = None,
        segment_engine: SegmentEngine | None = None,
        root_cause_engine: RootCauseEngine | None = None,
        unmet_need_detector: UnmetNeedDetector | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ingestion = ingestion_service or IngestionService(settings=self._settings)
        self._analysis = analysis_pipeline or AnalysisPipeline(settings=self._settings)
        self._pipeline_runs_repo = pipeline_runs_repo or PipelineRunsRepository()
        self._analysis_repo = analysis_repo or AnalysisRepository()
        self._theme_extractor = theme_extractor or ThemeExtractor(settings=self._settings)
        self._segment_engine = segment_engine or SegmentEngine(settings=self._settings)
        self._root_cause_engine = root_cause_engine or RootCauseEngine(settings=self._settings)
        self._unmet_need_detector = unmet_need_detector or UnmetNeedDetector(settings=self._settings)

    def run_full_pipeline_sync(
        self,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult:
        return asyncio.run(self.run_full_pipeline(progress_callback=progress_callback))

    async def run_stores_ingestion(
        self,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult:
        """Parallel Play Store + App Store ingest only (no analysis)."""
        return await self._run_ingestion_only(
            sources=("playstore", "appstore"),
            run_type="stores_ingest",
            progress_callback=progress_callback,
        )

    def run_stores_ingestion_sync(
        self,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult:
        return asyncio.run(
            self.run_stores_ingestion(progress_callback=progress_callback)
        )

    async def run_full_pipeline(
        self,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult:
        started = time.perf_counter()
        run_id = self._pipeline_runs_repo.create_run()
        self._report(progress_callback, "Starting pipeline run…")

        source_results, new_review_ids = await self._ingest_sources_parallel(
            self.SOURCE_ORDER,
            progress_callback,
        )
        status = self._compute_status(source_results)

        analysis_result: AnalysisPipelineResult | None = None
        analyzed_count = 0
        embedded_count = 0

        if status != "failed" and new_review_ids:
            self._report(
                progress_callback,
                f"Analyzing {len(new_review_ids)} new reviews…",
            )
            analysis_result = await asyncio.to_thread(
                self._analysis.run_for_review_ids,
                new_review_ids,
            )
            analyzed_count = analysis_result.analysis.analyzed
            embedded_count = analysis_result.embeddings.embedded
        elif status != "failed":
            self._report(progress_callback, "No new reviews to analyze")

        collective_result: CollectiveAnalysisResult | None = None
        if status != "failed" and self.should_run_collective():
            collective_result = await asyncio.to_thread(
                self.run_collective_analysis,
                force=False,
                progress_callback=progress_callback,
            )
        elif status != "failed":
            self._report(progress_callback, "Collective analysis threshold not met — skipping")

        duration_seconds = time.perf_counter() - started
        result = PipelineResult(
            run_id=run_id,
            sources=source_results,
            analyzed_count=analyzed_count,
            embedded_count=embedded_count,
            duration_seconds=duration_seconds,
            status=status,
            new_review_ids=new_review_ids,
            analysis=analysis_result,
            collective=collective_result,
        )

        stats = self._build_stats(result, run_type="full_pipeline")
        self._pipeline_runs_repo.finish_run(run_id, status, stats)
        self._report(progress_callback, f"Pipeline finished with status: {status}")
        return result

    def run_collective_analysis_sync(
        self,
        *,
        force: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> CollectiveAnalysisResult:
        return self.run_collective_analysis(force=force, progress_callback=progress_callback)

    def run_collective_analysis(
        self,
        *,
        force: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> CollectiveAnalysisResult:
        analyzed_review_count = self._analysis_repo.count_total()
        if not force and not self.should_run_collective():
            return CollectiveAnalysisResult(
                status="success",
                analyzed_review_count=analyzed_review_count,
                skipped=True,
                skip_reason="Collective analysis threshold not met",
            )

        if analyzed_review_count < self._settings.collective_analysis_threshold:
            raise ValueError(
                f"Need at least {self._settings.collective_analysis_threshold} analyzed reviews "
                f"for collective analysis; found {analyzed_review_count}"
            )

        started = time.perf_counter()
        run_id = self._pipeline_runs_repo.create_run(
            stats={"run_type": "collective_analysis"},
        )
        self._report(progress_callback, "Starting collective analysis…")

        engine_stats = CollectiveEngineStats()
        engine_steps = (
            ("themes", self._theme_extractor.run),
            ("segments", self._segment_engine.run),
            ("root causes", self._root_cause_engine.run),
            ("unmet needs", self._unmet_need_detector.run),
        )

        for label, engine_run in engine_steps:
            self._report(progress_callback, f"Running {label} engine…")
            try:
                result = engine_run()
                if label == "themes":
                    engine_stats.themes_written = result.themes_written
                elif label == "segments":
                    engine_stats.segments_written = result.segments_written
                elif label == "root causes":
                    engine_stats.root_causes_written = result.root_causes_written
                elif label == "unmet needs":
                    engine_stats.unmet_needs_written = result.unmet_needs_written
            except Exception as exc:
                message = f"{label} engine failed: {exc}"
                logger.error(message)
                engine_stats.errors.append(message)
                self._report(progress_callback, message)

        duration_seconds = time.perf_counter() - started
        status = self._compute_collective_status(engine_stats)
        collective_result = CollectiveAnalysisResult(
            run_id=run_id,
            status=status,
            engines=engine_stats,
            duration_seconds=duration_seconds,
            analyzed_review_count=analyzed_review_count,
        )

        stats = self._build_collective_stats(collective_result)
        self._pipeline_runs_repo.finish_run(run_id, status, stats)
        self._report(progress_callback, f"Collective analysis finished with status: {status}")
        return collective_result

    async def _run_ingestion_only(
        self,
        *,
        sources: tuple[str, ...],
        run_type: str,
        progress_callback: ProgressCallback | None,
    ) -> PipelineResult:
        started = time.perf_counter()
        run_id = self._pipeline_runs_repo.create_run(stats={"run_type": run_type})
        self._report(progress_callback, f"Starting {run_type}…")

        source_results, new_review_ids = await self._ingest_sources_parallel(
            sources,
            progress_callback,
        )
        status = self._compute_status(source_results)
        duration_seconds = time.perf_counter() - started

        result = PipelineResult(
            run_id=run_id,
            sources=source_results,
            duration_seconds=duration_seconds,
            status=status,
            new_review_ids=new_review_ids,
        )
        stats = self._build_stats(result, run_type=run_type)
        self._pipeline_runs_repo.finish_run(run_id, status, stats)
        self._report(progress_callback, f"Ingestion finished with status: {status}")
        return result

    async def _ingest_sources_parallel(
        self,
        sources: tuple[str, ...],
        progress_callback: ProgressCallback | None,
    ) -> tuple[dict[str, SourceResult], list[UUID]]:
        tasks = {
            source: asyncio.create_task(
                self._ingest_source(source, progress_callback),
            )
            for source in sources
        }

        outcomes = await asyncio.gather(*tasks.values(), return_exceptions=True)
        source_results: dict[str, SourceResult] = {}
        new_review_ids: list[UUID] = []

        for source, outcome in zip(tasks.keys(), outcomes, strict=True):
            if isinstance(outcome, Exception):
                logger.error("%s ingestion failed: %s", source, outcome)
                source_results[source] = SourceResult(error=str(outcome))
                continue

            source_results[source] = _to_source_result(outcome)
            new_review_ids.extend(outcome.new_review_ids)

        return source_results, new_review_ids

    async def _ingest_all_parallel(
        self,
        progress_callback: ProgressCallback | None,
    ) -> tuple[dict[str, SourceResult], list[UUID]]:
        return await self._ingest_sources_parallel(self.SOURCE_ORDER, progress_callback)

    async def _ingest_source(
        self,
        source: str,
        progress_callback: ProgressCallback | None,
    ) -> IngestionResult:
        self._report(progress_callback, f"Fetching {source}…")
        ingest_fn = {
            "playstore": self._ingestion.ingest_playstore,
            "appstore": self._ingestion.ingest_appstore,
            "reddit": self._ingestion.ingest_reddit,
        }[source]
        return await asyncio.to_thread(ingest_fn)

    @staticmethod
    def _compute_status(sources: dict[str, SourceResult]) -> Literal["success", "partial", "failed"]:
        successes = sum(1 for item in sources.values() if item.error is None)
        if successes == len(sources):
            return "success"
        if successes == 0:
            return "failed"
        return "partial"

    @staticmethod
    def _build_stats(result: PipelineResult, *, run_type: str = "full_pipeline") -> dict[str, Any]:
        stats: dict[str, Any] = {
            "run_type": run_type,
            "sources": {
                name: {
                    "fetched": source.fetched,
                    "stored": source.stored,
                    "skipped": source.skipped,
                    "new": source.new,
                    "error": source.error,
                    "used_fallback": source.used_fallback,
                }
                for name, source in result.sources.items()
            },
            "analyzed_count": result.analyzed_count,
            "embedded_count": result.embedded_count,
            "new_review_count": len(result.new_review_ids),
            "duration_seconds": round(result.duration_seconds, 2),
        }
        if result.collective and not result.collective.skipped:
            stats["collective_analysis"] = {
                "run_id": str(result.collective.run_id),
                "status": result.collective.status,
                "themes_written": result.collective.engines.themes_written,
                "segments_written": result.collective.engines.segments_written,
                "root_causes_written": result.collective.engines.root_causes_written,
                "unmet_needs_written": result.collective.engines.unmet_needs_written,
                "duration_seconds": round(result.collective.duration_seconds, 2),
            }
        return stats

    @staticmethod
    def _build_collective_stats(result: CollectiveAnalysisResult) -> dict[str, Any]:
        return {
            "run_type": "collective_analysis",
            "themes_written": result.engines.themes_written,
            "segments_written": result.engines.segments_written,
            "root_causes_written": result.engines.root_causes_written,
            "unmet_needs_written": result.engines.unmet_needs_written,
            "analyzed_review_count": result.analyzed_review_count,
            "duration_seconds": round(result.duration_seconds, 2),
            "engine_errors": result.engines.errors,
        }

    @staticmethod
    def _compute_collective_status(
        engines: CollectiveEngineStats,
    ) -> Literal["success", "partial", "failed"]:
        written = [
            engines.themes_written,
            engines.segments_written,
            engines.root_causes_written,
            engines.unmet_needs_written,
        ]
        successes = sum(1 for count in written if count > 0)
        if successes == 4 and not engines.errors:
            return "success"
        if successes == 0:
            return "failed"
        return "partial"

    @staticmethod
    def _report(callback: ProgressCallback | None, message: str) -> None:
        logger.info(message)
        if callback:
            callback(message)

    def should_run_collective(self) -> bool:
        """Return True when enough new analyzed reviews exist since the last collective run."""
        threshold = self._settings.collective_analysis_threshold
        analyzed_count = self._analysis_repo.count_total()
        if analyzed_count < threshold:
            return False

        last_collective = self._pipeline_runs_repo.get_latest_collective_run()
        if last_collective is None:
            return True

        last_stats = last_collective.get("stats") or {}
        baseline = int(last_stats.get("analyzed_review_count", 0))
        return (analyzed_count - baseline) >= threshold


def _to_source_result(result: IngestionResult) -> SourceResult:
    return SourceResult(
        fetched=result.fetched,
        stored=result.stored,
        skipped=result.skipped,
        new=len(result.new_review_ids),
        used_fallback=result.used_fallback,
    )
