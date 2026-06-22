"""CSV fallback importer."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.models import RawRecord, ReviewSource, VALID_SOURCES
from src.ingestion.base import SourceAdapter

MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB

TEXT_COLUMNS = ("text", "review_text", "body", "content")
DATE_COLUMNS = ("review_date", "date", "created_at", "timestamp")
RATING_COLUMNS = ("rating", "score", "stars")
NAME_COLUMNS = ("reviewer_name", "author", "user", "username")
SOURCE_COLUMNS = ("source",)
TITLE_COLUMNS = ("title", "headline")
METADATA_COLUMNS = (
    "subreddit",
    "upvotes",
    "external_id",
    "review_id",
    "helpful_count",
)


class CSVImportError(ValueError):
    """Raised when CSV content is invalid."""


class CSVImporter(SourceAdapter):
    def __init__(self, file_path: Path | None = None, file_bytes: bytes | None = None) -> None:
        self._file_path = file_path
        self._file_bytes = file_bytes

    def source_name(self) -> ReviewSource:
        return "playstore"

    def fetch(self, config: Any = None) -> list[RawRecord]:
        if self._file_bytes is not None:
            if len(self._file_bytes) > MAX_CSV_BYTES:
                raise CSVImportError(f"CSV exceeds maximum size of {MAX_CSV_BYTES // (1024 * 1024)} MB")
            return parse_csv_bytes(self._file_bytes)

        if self._file_path is None:
            raise CSVImportError("No CSV file path or bytes provided")

        data = self._file_path.read_bytes()
        if len(data) > MAX_CSV_BYTES:
            raise CSVImportError(f"CSV exceeds maximum size of {MAX_CSV_BYTES // (1024 * 1024)} MB")
        return parse_csv_bytes(data)


def parse_csv_bytes(data: bytes) -> list[RawRecord]:
    try:
        dataframe = pd.read_csv(io.BytesIO(data))
    except Exception as exc:
        raise CSVImportError(f"Failed to parse CSV: {exc}") from exc

    if dataframe.empty:
        raise CSVImportError("CSV file is empty")

    return parse_dataframe(dataframe)


def parse_dataframe(dataframe: pd.DataFrame) -> list[RawRecord]:
    columns = {col.lower().strip(): col for col in dataframe.columns}

    text_col = _find_column(columns, TEXT_COLUMNS)
    source_col = _find_column(columns, SOURCE_COLUMNS)

    if not text_col:
        raise CSVImportError(f"CSV must include a text column: {', '.join(TEXT_COLUMNS)}")
    if not source_col:
        raise CSVImportError("CSV must include a 'source' column (playstore, appstore, reddit)")

    date_col = _find_column(columns, DATE_COLUMNS)
    rating_col = _find_column(columns, RATING_COLUMNS)
    name_col = _find_column(columns, NAME_COLUMNS)

    records: list[RawRecord] = []
    for _, row in dataframe.iterrows():
        source = str(row[source_col]).strip().lower()
        if source not in VALID_SOURCES:
            continue

        text = str(row[text_col]).strip()
        if not text or text.lower() == "nan":
            continue

        metadata: dict[str, Any] = {}
        if name_col and pd.notna(row[name_col]):
            metadata["reviewer_name"] = str(row[name_col]).strip()

        for meta_key in METADATA_COLUMNS:
            col = columns.get(meta_key)
            if col and pd.notna(row[col]):
                metadata[meta_key] = row[col]

        for title_col in TITLE_COLUMNS:
            col = columns.get(title_col)
            if col and pd.notna(row[col]):
                metadata["title"] = str(row[col]).strip()
                break

        rating = None
        if rating_col and pd.notna(row[rating_col]):
            try:
                rating = int(float(row[rating_col]))
                if rating < 1 or rating > 5:
                    rating = None
            except (TypeError, ValueError):
                rating = None

        review_date = None
        if date_col and pd.notna(row[date_col]):
            review_date = _parse_date(row[date_col])

        records.append(
            RawRecord(
                source=source,  # type: ignore[arg-type]
                text=text,
                rating=rating,
                review_date=review_date,
                metadata=metadata,
            )
        )

    if not records:
        raise CSVImportError("No valid rows found in CSV")

    return records


def _find_column(columns: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    return None


def _parse_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime()
    except Exception:
        return None
