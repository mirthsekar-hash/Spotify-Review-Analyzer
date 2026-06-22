"""Collective intelligence schema validation tests."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas.root_causes import RootCauseOutput
from src.schemas.segments import SegmentationOutput
from src.schemas.themes import ThemeExtractionOutput
from src.schemas.unmet_needs import UnmetNeedsOutput


def _review_ids(count: int) -> list[str]:
    return [str(uuid4()) for _ in range(count)]


def test_theme_extraction_output_valid():
    theme = {
        "theme_name": "Stale Discover Weekly",
        "frequency": 42,
        "representative_review_ids": _review_ids(3),
        "affected_segments": ["Music Explorer", "Casual Listener"],
        "summary": "Users report Discover Weekly playlists feel repetitive week over week.",
    }
    output = ThemeExtractionOutput.model_validate({"themes": [theme] * 5})
    assert len(output.themes) == 5
    assert output.themes[0].theme_name == "Stale Discover Weekly"


def test_theme_extraction_rejects_too_few_themes():
    theme = {
        "theme_name": "Shuffle repetition",
        "frequency": 10,
        "representative_review_ids": _review_ids(3),
        "affected_segments": ["Power User"],
        "summary": "Shuffle plays the same tracks repeatedly.",
    }
    with pytest.raises(ValidationError):
        ThemeExtractionOutput.model_validate({"themes": [theme] * 4})


def test_theme_extraction_rejects_insufficient_evidence_ids():
    with pytest.raises(ValidationError):
        ThemeExtractionOutput.model_validate(
            {
                "themes": [
                    {
                        "theme_name": "Bad recommendations",
                        "frequency": 5,
                        "representative_review_ids": _review_ids(2),
                        "affected_segments": ["Music Explorer"],
                        "summary": "Recommendations miss the mark.",
                    }
                ]
                * 5
            }
        )


def test_segmentation_output_valid():
    segment = {
        "segment_name": "Music Explorer",
        "listening_goals": ["Find new artists", "Expand genres"],
        "discovery_behavior": ["Uses Discover Weekly", "Follows playlists"],
        "top_frustrations": ["Repetitive recommendations", "Filter bubble"],
        "narrative_summary": "Explorers actively seek novelty but feel constrained by algorithmic sameness.",
    }
    output = SegmentationOutput.model_validate({"segments": [segment]})
    assert output.segments[0].segment_name == "Music Explorer"


def test_segmentation_rejects_invalid_segment():
    with pytest.raises(ValidationError):
        SegmentationOutput.model_validate(
            {
                "segments": [
                    {
                        "segment_name": "Super User",
                        "listening_goals": ["Listen"],
                        "discovery_behavior": ["Shuffle"],
                        "top_frustrations": ["Ads"],
                        "narrative_summary": "Invalid segment name.",
                    }
                ]
            }
        )


def test_root_cause_output_valid():
    item = {
        "root_cause": "Collaborative filtering reinforces past taste",
        "frequency": 25,
        "supporting_evidence_ids": _review_ids(2),
        "affected_segments": ["Genre Loyalist", "Music Explorer"],
        "causal_explanation": "The model overweight historical plays, reducing exposure to new artists.",
    }
    output = RootCauseOutput.model_validate({"root_causes": [item] * 5})
    assert len(output.root_causes) == 5


def test_unmet_needs_output_valid():
    item = {
        "need": "Mood-aware discovery",
        "frequency": 18,
        "supporting_review_ids": _review_ids(2),
        "affected_segments": ["Casual Listener"],
        "severity_score": 0.8,
        "suggested_ai_solutions": ["Context-aware playlist generation from listening context"],
    }
    output = UnmetNeedsOutput.model_validate({"unmet_needs": [item] * 5})
    assert output.unmet_needs[0].severity_score == 0.8


def test_unmet_needs_rejects_invalid_severity():
    item = {
        "need": "Guided exploration",
        "frequency": 10,
        "supporting_review_ids": _review_ids(2),
        "affected_segments": ["Playlist-Dependent Listener"],
        "severity_score": 1.5,
        "suggested_ai_solutions": ["Onboarding-style discovery coach"],
    }
    with pytest.raises(ValidationError):
        UnmetNeedsOutput.model_validate({"unmet_needs": [item] * 5})


def test_prompt_files_exist_and_load():
    from src.analysis.prompts import load_prompt

    for filename in (
        "theme_extraction.txt",
        "segmentation.txt",
        "root_cause.txt",
        "unmet_needs.txt",
    ):
        content = load_prompt(filename)
        assert "Base conclusions ONLY" in content or "ONLY on" in content
        assert len(content) > 100
