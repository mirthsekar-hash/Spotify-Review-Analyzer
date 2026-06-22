"""Optional live analysis integration test (requires LLM + embedding API keys)."""

import os
from uuid import uuid4

import pytest

from src.analysis.analysis_pipeline import AnalysisPipeline
from src.db.models import RawRecord
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.embeddings_repo import EmbeddingsRepository
from src.ingestion.service import IngestionService

RUN_LIVE = os.getenv("RUN_LIVE_ANALYSIS", "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.skipif(
    not RUN_LIVE,
    reason="Set RUN_LIVE_ANALYSIS=1 to run live analysis integration tests",
)


@pytest.fixture(scope="module")
def require_services():
    from app.config import get_settings
    from src.db.client import check_connection

    settings = get_settings()
    if settings.llm_provider == "groq" and not settings.groq_api_key.strip():
        pytest.skip("GROQ_API_KEY not configured")
    if settings.llm_provider == "gemini" and not settings.gemini_api_key.strip():
        pytest.skip("GEMINI_API_KEY not configured")
    if settings.llm_provider == "openai" and not settings.openai_api_key.strip():
        pytest.skip("OPENAI_API_KEY not configured")
    if settings.embedding_provider == "gemini" and not settings.gemini_api_key.strip():
        pytest.skip("GEMINI_API_KEY not configured for embeddings")
    if not check_connection():
        pytest.skip("Supabase not available")


def test_live_analyze_single_review(require_services):
    unique_suffix = str(uuid4())[:8]
    record = RawRecord(
        source="playstore",
        text=f"Discover Weekly keeps repeating the same artists {unique_suffix}",
        rating=2,
        metadata={"external_id": f"live_{unique_suffix}"},
    )

    ingest = IngestionService().ingest_raw_records([record])
    assert ingest.stored >= 1

    result = AnalysisPipeline().run(limit=1)
    assert result.analysis.analyzed >= 1
    assert result.embeddings.embedded >= 1
    assert result.processed_review_ids

    review_id = result.processed_review_ids[0]
    assert AnalysisRepository().get_by_review_id(review_id) is not None
    assert EmbeddingsRepository().get_by_review_id(review_id) is not None
