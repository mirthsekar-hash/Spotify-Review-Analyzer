"""CSV importer tests."""

from pathlib import Path

import pytest

from src.ingestion.csv_importer import CSVImportError, CSVImporter, parse_csv_bytes


SAMPLE_CSV = """source,text,rating,review_date,reviewer_name,external_id
playstore,Discover Weekly is repetitive,2,2024-01-15,user1,ps_1
playstore,Love the suggested songs feature,5,2024-02-20,user2,ps_2
appstore,Algorithm keeps repeating artists,1,2024-03-10,user3,as_1
invalid_source,Should be skipped,3,2024-03-11,user4,x1
"""


def test_parse_csv_bytes():
    records = parse_csv_bytes(SAMPLE_CSV.encode("utf-8"))
    assert len(records) == 3
    assert records[0].source == "playstore"
    assert records[0].text == "Discover Weekly is repetitive"
    assert records[0].rating == 2
    assert records[0].metadata["reviewer_name"] == "user1"
    assert records[0].metadata["external_id"] == "ps_1"


def test_csv_importer_from_file():
    path = Path("data/fallback/playstore_sample.csv")
    if not path.exists():
        pytest.skip("Sample CSV not generated")

    records = CSVImporter(file_path=path).fetch()
    assert len(records) >= 50
    assert all(record.source == "playstore" for record in records)


def test_missing_text_column_raises():
    bad_csv = b"source,rating\nplaystore,5\n"
    with pytest.raises(CSVImportError, match="text column"):
        parse_csv_bytes(bad_csv)


def test_empty_csv_raises():
    with pytest.raises(CSVImportError):
        parse_csv_bytes(b"source,text\n")
