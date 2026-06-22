"""Schema validation tests."""

import pytest
from pydantic import ValidationError

from src.schemas.review_analysis import ReviewAnalysisOutput


def test_valid_review_analysis_output():
    output = ReviewAnalysisOutput.model_validate(
        {
            "sentiment": "negative",
            "primary_problem": "Repetitive recommendations",
            "recommendation_complaint": True,
            "user_goal": "Discover new music",
            "listening_behavior": "Relies on Discover Weekly",
            "user_segment": "Music Explorer",
            "discovery_challenge": "Recommendations feel stale",
            "confidence_score": 0.91,
        }
    )
    assert output.sentiment == "negative"
    assert output.user_segment == "Music Explorer"


def test_invalid_sentiment_rejected():
    with pytest.raises(ValidationError):
        ReviewAnalysisOutput.model_validate(
            {
                "sentiment": "angry",
                "primary_problem": "Bad algo",
                "recommendation_complaint": True,
                "user_goal": "Find new music",
                "listening_behavior": "Shuffle only",
                "user_segment": "Music Explorer",
                "discovery_challenge": "Same songs",
                "confidence_score": 0.5,
            }
        )


def test_invalid_segment_rejected():
    with pytest.raises(ValidationError):
        ReviewAnalysisOutput.model_validate(
            {
                "sentiment": "negative",
                "primary_problem": "Bad algo",
                "recommendation_complaint": True,
                "user_goal": "Find new music",
                "listening_behavior": "Shuffle only",
                "user_segment": "Super User",
                "discovery_challenge": "Same songs",
                "confidence_score": 0.5,
            }
        )


def test_confidence_score_bounds():
    with pytest.raises(ValidationError):
        ReviewAnalysisOutput.model_validate(
            {
                "sentiment": "neutral",
                "primary_problem": "Average experience",
                "recommendation_complaint": False,
                "user_goal": "Background listening",
                "listening_behavior": "Playlist replay",
                "user_segment": "Casual Listener",
                "discovery_challenge": "No time to explore",
                "confidence_score": 1.5,
            }
        )
