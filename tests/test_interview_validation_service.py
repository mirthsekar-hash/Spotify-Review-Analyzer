"""Interview validation service tests."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.db.models import InterviewInsight, Theme
from src.schemas.interview_insight import InterviewInsightCreate
from src.services.interview_validation_service import (
    InterviewValidationService,
    compute_suggested_confidence,
)


def test_compute_suggested_confidence_blends_validation_and_evidence():
    score = compute_suggested_confidence(80.0, review_count=10)
    assert score is not None
    assert 0.0 <= score <= 1.0
    assert score > compute_suggested_confidence(80.0, review_count=0)


def test_get_validation_data_enriches_theme_evidence():
    theme_id = uuid4()
    insight_id = uuid4()
    theme = Theme(
        id=theme_id,
        theme_name="Stale Discover Weekly",
        frequency=12,
        representative_review_ids=[uuid4(), uuid4(), uuid4()],
    )
    insight = InterviewInsight(
        id=insight_id,
        insight="Participants report repetitive weekly mixes",
        linked_theme_id=theme_id,
        validation_pct=75.0,
        confidence_score=0.7,
    )

    insights_repo = MagicMock()
    insights_repo.get_all.return_value = [insight]
    themes_repo = MagicMock()
    themes_repo.get_all.return_value = [theme]
    themes_repo.count_linked_reviews.return_value = 3

    service = InterviewValidationService(
        insights_repo=insights_repo,
        themes_repo=themes_repo,
    )

    with patch("src.services.interview_validation_service.check_connection", return_value=True):
        data = service.get_validation_data()

    assert data.db_connected is True
    assert len(data.insights) == 1
    assert data.insights[0].linked_theme_name == "Stale Discover Weekly"
    assert data.insights[0].review_evidence_count == 3


def test_create_insight_auto_computes_confidence_when_missing():
    theme_id = uuid4()
    stored_id = uuid4()
    insights_repo = MagicMock()
    insights_repo.insert.return_value = InterviewInsight(
        id=stored_id,
        insight="Shuffle feels repetitive",
        linked_theme_id=theme_id,
        validation_pct=90.0,
        confidence_score=0.81,
    )
    themes_repo = MagicMock()
    themes_repo.get_all.return_value = [
        Theme(id=theme_id, theme_name="Shuffle Repetition", frequency=5)
    ]
    themes_repo.count_linked_reviews.return_value = 8

    service = InterviewValidationService(
        insights_repo=insights_repo,
        themes_repo=themes_repo,
    )
    row = service.create_insight(
        InterviewInsightCreate(
            insight="Shuffle feels repetitive",
            linked_theme_id=theme_id,
            validation_pct=90.0,
        )
    )

    assert row.id == stored_id
    insights_repo.insert.assert_called_once()
    inserted = insights_repo.insert.call_args[0][0]
    assert inserted.confidence_score is not None
