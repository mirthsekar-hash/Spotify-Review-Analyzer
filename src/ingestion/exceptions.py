"""Ingestion-specific exceptions."""


class ScrapeError(RuntimeError):
    """Raised when a live scrape fails or returns insufficient data."""


class RedditFetchError(RuntimeError):
    """Raised when Reddit JSON API access fails after retries."""
