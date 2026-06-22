"""Review Discovery browse/search service for the corpus explorer page."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.db.client import check_connection
from src.db.models import Review
from src.db.repositories.reviews_repo import ReviewSearchParams, ReviewsRepository


@dataclass
class RatingDistribution:
    counts: dict[int, int] = field(default_factory=lambda: {5: 0, 4: 0, 3: 0, 2: 0, 1: 0})

    @property
    def total_with_rating(self) -> int:
        return sum(self.counts.values())

    def average_rating(self) -> float | None:
        total = self.total_with_rating
        if total == 0:
            return None
        weighted = sum(star * count for star, count in self.counts.items())
        return round(weighted / total, 2)


@dataclass
class ReviewDiscoveryData:
    reviews: list[Review] = field(default_factory=list)
    matching_count: int = 0
    corpus_total: int = 0
    avg_rating: float | None = None
    rating_distribution: RatingDistribution = field(default_factory=RatingDistribution)
    db_connected: bool = False
    page: int = 1
    page_size: int = 40
    total_pages: int = 1


def compute_total_pages(matching_count: int, page_size: int) -> int:
    if matching_count <= 0:
        return 1
    return max(1, (matching_count + page_size - 1) // page_size)


class ReviewDiscoveryService:
    DEFAULT_PAGE_SIZE = 40

    def __init__(self, reviews_repo: ReviewsRepository | None = None) -> None:
        self._reviews_repo = reviews_repo or ReviewsRepository()

    def search(
        self,
        params: ReviewSearchParams,
        *,
        page: int = 1,
        page_size: int | None = None,
    ) -> ReviewDiscoveryData:
        if not check_connection():
            return ReviewDiscoveryData(db_connected=False)

        size = page_size or self.DEFAULT_PAGE_SIZE
        page = max(page, 1)
        corpus_total = self._reviews_repo.count_total()
        matching_count = self._reviews_repo.count_matching(params)
        total_pages = compute_total_pages(matching_count, size)
        page = min(page, total_pages)

        distribution_params = ReviewSearchParams(
            query=params.query,
            rating=None,
            source=params.source,
            sort_by=params.sort_by,
        )
        distribution_counts = self._reviews_repo.get_rating_distribution(distribution_params)
        distribution = RatingDistribution(counts=distribution_counts)

        offset = (page - 1) * size
        reviews = self._reviews_repo.search_reviews(params, offset=offset, limit=size)

        return ReviewDiscoveryData(
            reviews=reviews,
            matching_count=matching_count,
            corpus_total=corpus_total,
            avg_rating=distribution.average_rating(),
            rating_distribution=distribution,
            db_connected=True,
            page=page,
            page_size=size,
            total_pages=total_pages,
        )
