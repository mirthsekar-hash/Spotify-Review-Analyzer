"""Pipeline runs repository tests."""

from unittest.mock import MagicMock

from src.db.repositories.pipeline_runs_repo import PipelineRunsRepository


def test_get_latest_returns_none_when_table_empty():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    chain = MagicMock()
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = None
    mock_table.select.return_value = chain

    repo = PipelineRunsRepository(client=mock_client)
    assert repo.get_latest() is None


def test_get_latest_returns_first_row():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    row = {"id": "abc", "status": "success", "stats": {}}
    chain = MagicMock()
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(data=[row])
    mock_table.select.return_value = chain

    repo = PipelineRunsRepository(client=mock_client)
    assert repo.get_latest() == row


def test_get_latest_collective_run_uses_contains_filter():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    row = {"id": "abc", "status": "success", "stats": {"run_type": "collective_analysis"}}
    chain = MagicMock()
    chain.contains.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(data=[row])
    mock_table.select.return_value = chain

    repo = PipelineRunsRepository(client=mock_client)
    assert repo.get_latest_collective_run() == row
    chain.contains.assert_called_once_with("stats", {"run_type": "collective_analysis"})
