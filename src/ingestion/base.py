"""Source adapter protocol and ingestion config."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from src.db.models import RawRecord, ReviewSource


@dataclass
class IngestConfig:
    app_id: str = "com.spotify.music"
    country: str = "us"
    language: str = "en"
    target_count: int = 500
    keywords: list[str] = field(
        default_factory=lambda: [
            "recommend",
            "playlist",
            "discover",
            "shuffle",
            "suggested",
            "algorithm",
            "weekly",
        ]
    )


class SourceAdapter(Protocol):
    def source_name(self) -> ReviewSource: ...

    def fetch(self, config: IngestConfig | None = None) -> list[RawRecord]: ...
