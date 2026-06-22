"""Interview insights repository tests."""

from unittest.mock import MagicMock
from uuid import uuid4

from src.db.models import InterviewInsight
from src.schemas.interview_insight import InterviewInsightCreate, InterviewInsightUpdate
from src.db.repositories.interview_insights_repo import InterviewInsightsRepository


def _mock_table():
    table = MagicMock()
    client = MagicMock()
    client.table.return_value = table
    return client, table


def test_insert_interview_insight():
    client, table = _mock_table()
    insight_id = uuid4()
    theme_id = uuid4()
    table.insert.return_value.execute.return_value.data = [
        {
            "id": str(insight_id),
            "insight": "Users want fresher playlists",
            "linked_theme_id": str(theme_id),
            "validation_pct": 80.0,
            "confidence_score": 0.75,
            "notes": "5 participants",
        }
    ]

    repo = InterviewInsightsRepository(client=client)
    result = repo.insert(
        InterviewInsightCreate(
            insight="Users want fresher playlists",
            linked_theme_id=theme_id,
            validation_pct=80.0,
            confidence_score=0.75,
            notes="5 participants",
        )
    )

    assert result.id == insight_id
    assert result.validation_pct == 80.0
    table.insert.assert_called_once()


def test_get_all_orders_by_created_at():
    client, table = _mock_table()
    table.select.return_value.order.return_value.execute.return_value.data = [
        {"id": str(uuid4()), "insight": "First"},
        {"id": str(uuid4()), "insight": "Second"},
    ]

    repo = InterviewInsightsRepository(client=client)
    results = repo.get_all()

    assert len(results) == 2
    table.select.assert_called_with("*")


def test_update_interview_insight():
    client, table = _mock_table()
    insight_id = uuid4()
    table.update.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": str(insight_id),
            "insight": "Updated insight",
            "linked_theme_id": None,
            "validation_pct": 60.0,
            "confidence_score": 0.6,
            "notes": None,
        }
    ]

    repo = InterviewInsightsRepository(client=client)
    result = repo.update(
        insight_id,
        InterviewInsightUpdate(insight="Updated insight", validation_pct=60.0, confidence_score=0.6),
    )

    assert result.insight == "Updated insight"
    table.update.assert_called_once()
