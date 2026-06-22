"""Review Discovery service unit tests."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.db.models import Review
from src.db.repositories.reviews_repo import ReviewSearchParams
from src.services.review_discovery_service import (
    RatingDistribution,
    ReviewDiscoveryService,
    compute_total_pages,
)


def _review(text: str = "Great app") -> Review:
    return Review(
        id=uuid4(),
        source="playstore",
        text=text,
        rating=4,
        review_date=None,
        metadata={},
        content_hash="hash",
    )


def test_rating_distribution_average():
    distribution = RatingDistribution(counts={5: 10, 4: 5, 3: 2, 2: 1, 1: 2})
    assert distribution.total_with_rating == 20
    assert distribution.average_rating() == 4.0


def test_compute_total_pages():
    assert compute_total_pages(0, 40) == 1
    assert compute_total_pages(40, 40) == 1
    assert compute_total_pages(41, 40) == 2


@patch("src.services.review_discovery_service.check_connection", return_value=True)
def test_search_returns_paginated_results(mock_check):
    reviews_repo = MagicMock()
    reviews_repo.count_total.return_value = 100
    reviews_repo.count_matching.return_value = 80
    reviews_repo.get_rating_distribution.return_value = {5: 40, 4: 20, 3: 10, 2: 5, 1: 5}
    reviews_repo.search_reviews.return_value = [_review()]

    service = ReviewDiscoveryService(reviews_repo=reviews_repo)
    params = ReviewSearchParams(query="shuffle")
    data = service.search(params, page=2, page_size=40)

    assert data.db_connected is True
    assert data.corpus_total == 100
    assert data.matching_count == 80
    assert data.page == 2
    assert data.total_pages == 2
    assert len(data.reviews) == 1
    assert data.avg_rating == 4.06
    reviews_repo.search_reviews.assert_called_once_with(params, offset=40, limit=40)


@patch("src.services.review_discovery_service.check_connection", return_value=False)
def test_search_disconnected(mock_check):
    data = ReviewDiscoveryService().search(ReviewSearchParams())
    assert data.db_connected is False
    assert data.reviews == []
