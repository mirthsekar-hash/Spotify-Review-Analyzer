"""Review search repository tests."""

from unittest.mock import MagicMock

from src.db.repositories.reviews_repo import ReviewSearchParams, ReviewsRepository


def test_count_matching_applies_filters():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    chain = MagicMock()
    chain.limit.return_value = chain
    chain.ilike.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = MagicMock(count=12)
    mock_table.select.return_value = chain

    repo = ReviewsRepository(client=mock_client)
    params = ReviewSearchParams(query="shuffle", rating=2, source="playstore")
    count = repo.count_matching(params)

    assert count == 12
    chain.ilike.assert_called_once()
    assert chain.eq.call_count == 2


def test_get_rating_distribution_counts_each_star():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    chain = MagicMock()
    chain.limit.return_value = chain
    chain.ilike.return_value = chain
    chain.eq.return_value = chain
    chain.execute.side_effect = [
        MagicMock(count=5),
        MagicMock(count=4),
        MagicMock(count=3),
        MagicMock(count=2),
        MagicMock(count=1),
    ]
    mock_table.select.return_value = chain

    repo = ReviewsRepository(client=mock_client)
    distribution = repo.get_rating_distribution(ReviewSearchParams(query="ads"))

    assert distribution == {5: 5, 4: 4, 3: 3, 2: 2, 1: 1}
    assert chain.eq.call_count == 5
