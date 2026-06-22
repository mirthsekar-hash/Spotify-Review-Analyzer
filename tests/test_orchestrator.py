"""Pipeline orchestrator unit tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.analysis.analysis_pipeline import AnalysisPipelineResult
from src.analysis.embedding_service import EmbeddingBatchResult
from src.analysis.review_analyzer import ReviewAnalysisBatchResult
from src.db.models import UpsertReviewsResult
from src.ingestion.service import IngestionResult
from src.pipeline.orchestrator import PipelineOrchestrator, _to_source_result


def _ingestion_result(fetched: int, new_count: int, *, used_fallback: bool = False) -> IngestionResult:
    new_ids = [uuid4() for _ in range(new_count)]
    return IngestionResult(
        fetched=fetched,
        normalized=fetched,
        stored=fetched,
        skipped=0,
        upsert=UpsertReviewsResult(
            attempted=fetched,
            stored=fetched,
            review_ids=new_ids,
            new_review_ids=new_ids,
        ),
        used_fallback=used_fallback,
        new_review_ids=new_ids,
    )


def test_to_source_result_maps_fields():
    result = _ingestion_result(100, 5, used_fallback=True)
    source = _to_source_result(result)

    assert source.fetched == 100
    assert source.stored == 100
    assert source.new == 5
    assert source.used_fallback is True
    assert source.error is None


def test_compute_status_success():
    from src.pipeline.orchestrator import SourceResult

    sources = {
        "playstore": SourceResult(fetched=1),
        "appstore": SourceResult(fetched=1),
        "reddit": SourceResult(fetched=1),
    }
    assert PipelineOrchestrator._compute_status(sources) == "success"


def test_compute_status_partial():
    from src.pipeline.orchestrator import SourceResult

    sources = {
        "playstore": SourceResult(fetched=1),
        "appstore": SourceResult(error="blocked"),
        "reddit": SourceResult(fetched=1),
    }
    assert PipelineOrchestrator._compute_status(sources) == "partial"


def test_compute_status_failed():
    from src.pipeline.orchestrator import SourceResult

    sources = {
        "playstore": SourceResult(error="blocked"),
        "appstore": SourceResult(error="blocked"),
        "reddit": SourceResult(error="blocked"),
    }
    assert PipelineOrchestrator._compute_status(sources) == "failed"


def test_run_full_pipeline_partial_failure_still_analyzes_new_reviews():
    run_id = uuid4()
    new_review_id = uuid4()

    ingestion = MagicMock()
    ingestion.ingest_playstore.return_value = IngestionResult(
        fetched=10,
        normalized=10,
        stored=10,
        skipped=0,
        upsert=UpsertReviewsResult(
            attempted=10,
            stored=10,
            review_ids=[new_review_id],
            new_review_ids=[new_review_id],
        ),
        new_review_ids=[new_review_id],
    )
    ingestion.ingest_appstore.side_effect = RuntimeError("App Store blocked")
    ingestion.ingest_reddit.return_value = IngestionResult(
        fetched=0,
        normalized=0,
        stored=0,
        skipped=0,
        upsert=UpsertReviewsResult(attempted=0, stored=0, review_ids=[], new_review_ids=[]),
        new_review_ids=[],
    )

    analysis_pipeline = MagicMock()
    analysis_pipeline.run_for_review_ids.return_value = AnalysisPipelineResult(
        reviews_fetched=1,
        analysis=ReviewAnalysisBatchResult(analyzed=1),
        embeddings=EmbeddingBatchResult(embedded=1),
        marked_analyzed=1,
        processed_review_ids=[new_review_id],
    )

    pipeline_runs_repo = MagicMock()
    pipeline_runs_repo.create_run.return_value = run_id

    orchestrator = PipelineOrchestrator(
        ingestion_service=ingestion,
        analysis_pipeline=analysis_pipeline,
        pipeline_runs_repo=pipeline_runs_repo,
    )

    with patch.object(
        orchestrator,
        "_ingest_source",
        new_callable=AsyncMock,
    ) as mock_ingest:
        mock_ingest.side_effect = [
            ingestion.ingest_playstore.return_value,
            RuntimeError("App Store blocked"),
            ingestion.ingest_reddit.return_value,
        ]
        result = asyncio.run(orchestrator.run_full_pipeline())

    assert result.status == "partial"
    assert result.sources["playstore"].new == 1
    assert result.sources["appstore"].error == "App Store blocked"
    assert result.analyzed_count == 1
    analysis_pipeline.run_for_review_ids.assert_called_once()
    pipeline_runs_repo.finish_run.assert_called_once()
    finish_args = pipeline_runs_repo.finish_run.call_args[0]
    assert finish_args[0] == run_id
    assert finish_args[1] == "partial"


def test_should_run_collective_false_when_below_minimum():
    analysis_repo = MagicMock()
    analysis_repo.count_total.return_value = 30
    pipeline_runs_repo = MagicMock()

    orchestrator = PipelineOrchestrator(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=analysis_repo,
        pipeline_runs_repo=pipeline_runs_repo,
    )

    assert orchestrator.should_run_collective() is False


def test_should_run_collective_true_on_first_run():
    analysis_repo = MagicMock()
    analysis_repo.count_total.return_value = 120
    pipeline_runs_repo = MagicMock()
    pipeline_runs_repo.get_latest_collective_run.return_value = None

    orchestrator = PipelineOrchestrator(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=analysis_repo,
        pipeline_runs_repo=pipeline_runs_repo,
    )

    assert orchestrator.should_run_collective() is True


def test_should_run_collective_true_when_enough_new_reviews():
    analysis_repo = MagicMock()
    analysis_repo.count_total.return_value = 160
    pipeline_runs_repo = MagicMock()
    pipeline_runs_repo.get_latest_collective_run.return_value = {
        "stats": {"analyzed_review_count": 100},
    }

    orchestrator = PipelineOrchestrator(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=analysis_repo,
        pipeline_runs_repo=pipeline_runs_repo,
    )

    assert orchestrator.should_run_collective() is True


def test_should_run_collective_false_when_not_enough_new_reviews():
    analysis_repo = MagicMock()
    analysis_repo.count_total.return_value = 130
    pipeline_runs_repo = MagicMock()
    pipeline_runs_repo.get_latest_collective_run.return_value = {
        "stats": {"analyzed_review_count": 100},
    }

    orchestrator = PipelineOrchestrator(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=analysis_repo,
        pipeline_runs_repo=pipeline_runs_repo,
    )

    assert orchestrator.should_run_collective() is False


def test_run_collective_analysis_runs_all_engines():
    run_id = uuid4()
    pipeline_runs_repo = MagicMock()
    pipeline_runs_repo.create_run.return_value = run_id

    theme_extractor = MagicMock()
    theme_extractor.run.return_value = MagicMock(themes_written=5)
    segment_engine = MagicMock()
    segment_engine.run.return_value = MagicMock(segments_written=5)
    root_cause_engine = MagicMock()
    root_cause_engine.run.return_value = MagicMock(root_causes_written=5)
    unmet_need_detector = MagicMock()
    unmet_need_detector.run.return_value = MagicMock(unmet_needs_written=5)

    analysis_repo = MagicMock()
    analysis_repo.count_total.return_value = 100

    orchestrator = PipelineOrchestrator(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=analysis_repo,
        pipeline_runs_repo=pipeline_runs_repo,
        theme_extractor=theme_extractor,
        segment_engine=segment_engine,
        root_cause_engine=root_cause_engine,
        unmet_need_detector=unmet_need_detector,
    )

    result = orchestrator.run_collective_analysis(force=True)

    assert result.status == "success"
    assert result.engines.themes_written == 5
    assert result.engines.segments_written == 5
    assert result.engines.root_causes_written == 5
    assert result.engines.unmet_needs_written == 5
    theme_extractor.run.assert_called_once()
    segment_engine.run.assert_called_once()
    root_cause_engine.run.assert_called_once()
    unmet_need_detector.run.assert_called_once()
    pipeline_runs_repo.finish_run.assert_called_once()
    finish_stats = pipeline_runs_repo.finish_run.call_args[0][2]
    assert finish_stats["run_type"] == "collective_analysis"
    assert finish_stats["analyzed_review_count"] == 100


def test_run_full_pipeline_triggers_collective_when_threshold_met():
    run_id = uuid4()
    new_review_id = uuid4()

    ingestion = MagicMock()
    ingestion.ingest_playstore.return_value = IngestionResult(
        fetched=10,
        normalized=10,
        stored=10,
        skipped=0,
        upsert=UpsertReviewsResult(
            attempted=10,
            stored=10,
            review_ids=[new_review_id],
            new_review_ids=[new_review_id],
        ),
        new_review_ids=[new_review_id],
    )
    ingestion.ingest_appstore.return_value = IngestionResult(
        fetched=0,
        normalized=0,
        stored=0,
        skipped=0,
        upsert=UpsertReviewsResult(attempted=0, stored=0, review_ids=[], new_review_ids=[]),
        new_review_ids=[],
    )
    ingestion.ingest_reddit.return_value = IngestionResult(
        fetched=0,
        normalized=0,
        stored=0,
        skipped=0,
        upsert=UpsertReviewsResult(attempted=0, stored=0, review_ids=[], new_review_ids=[]),
        new_review_ids=[],
    )

    analysis_pipeline = MagicMock()
    analysis_pipeline.run_for_review_ids.return_value = AnalysisPipelineResult(
        reviews_fetched=1,
        analysis=ReviewAnalysisBatchResult(analyzed=1),
        embeddings=EmbeddingBatchResult(embedded=1),
        marked_analyzed=1,
        processed_review_ids=[new_review_id],
    )

    pipeline_runs_repo = MagicMock()
    pipeline_runs_repo.create_run.return_value = run_id

    collective_run_id = uuid4()
    collective_result = MagicMock()
    collective_result.skipped = False
    collective_result.run_id = collective_run_id
    collective_result.status = "success"
    collective_result.duration_seconds = 12.5
    collective_result.engines = MagicMock(
        themes_written=5,
        segments_written=5,
        root_causes_written=5,
        unmet_needs_written=5,
        errors=[],
    )

    orchestrator = PipelineOrchestrator(
        settings=MagicMock(collective_analysis_threshold=50),
        ingestion_service=ingestion,
        analysis_pipeline=analysis_pipeline,
        pipeline_runs_repo=pipeline_runs_repo,
    )

    with patch.object(orchestrator, "should_run_collective", return_value=True), patch.object(
        orchestrator,
        "run_collective_analysis",
        return_value=collective_result,
    ) as mock_collective:
        with patch.object(
            orchestrator,
            "_ingest_source",
            new_callable=AsyncMock,
        ) as mock_ingest:
            mock_ingest.side_effect = [
                ingestion.ingest_playstore.return_value,
                ingestion.ingest_appstore.return_value,
                ingestion.ingest_reddit.return_value,
            ]
            result = asyncio.run(orchestrator.run_full_pipeline())

    assert result.collective is collective_result
    mock_collective.assert_called_once()
    finish_stats = pipeline_runs_repo.finish_run.call_args[0][2]
    assert finish_stats["collective_analysis"]["themes_written"] == 5


def test_run_full_pipeline_all_sources_fail_skips_analysis():
    run_id = uuid4()
    pipeline_runs_repo = MagicMock()
    pipeline_runs_repo.create_run.return_value = run_id
    analysis_pipeline = MagicMock()

    orchestrator = PipelineOrchestrator(
        analysis_pipeline=analysis_pipeline,
        pipeline_runs_repo=pipeline_runs_repo,
    )

    with patch.object(
        orchestrator,
        "_ingest_source",
        new_callable=AsyncMock,
        side_effect=[
            RuntimeError("playstore failed"),
            RuntimeError("appstore failed"),
            RuntimeError("reddit failed"),
        ],
    ):
        result = asyncio.run(orchestrator.run_full_pipeline())

    assert result.status == "failed"
    assert result.analyzed_count == 0
    analysis_pipeline.run_for_review_ids.assert_not_called()
