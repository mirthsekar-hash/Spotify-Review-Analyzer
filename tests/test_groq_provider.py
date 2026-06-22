"""Groq provider tests with mocked OpenAI client."""

import json
from unittest.mock import MagicMock, patch

from app.config import Settings
from src.llm.groq_provider import GroqProvider
from src.schemas.review_analysis import ReviewAnalysisOutput


def _sample_output() -> ReviewAnalysisOutput:
    return ReviewAnalysisOutput(
        sentiment="negative",
        primary_problem="Repetitive recommendations",
        recommendation_complaint=True,
        user_goal="Discover new artists",
        listening_behavior="Uses Discover Weekly weekly",
        user_segment="Music Explorer",
        discovery_challenge="Recommendations lack variety",
        confidence_score=0.88,
    )


@patch("openai.OpenAI")
def test_groq_structured_completion_validates_json(mock_openai_cls):
    settings = Settings(
        llm_provider="groq",
        groq_api_key="test-key",
        groq_model="llama-3.3-70b-versatile",
        _env_file=None,
    )
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(_sample_output().model_dump())
    mock_client.chat.completions.create.return_value = mock_response

    provider = GroqProvider(settings)
    result = provider.structured_completion(
        "Analyze reviews.",
        "Source: playstore\nRating: 2\nReview text:\nBad recommendations.",
        ReviewAnalysisOutput,
    )

    assert result.sentiment == "negative"
    assert result.user_segment == "Music Explorer"
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "llama-3.3-70b-versatile"
    assert call_kwargs["response_format"] == {"type": "json_object"}
