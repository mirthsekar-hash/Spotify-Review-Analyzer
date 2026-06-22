"""Research assistant schema tests."""

import pytest
from pydantic import ValidationError

from src.schemas.research_assistant import ResearchAssistantOutput, SupportingEvidence


def test_valid_research_assistant_output():
    output = ResearchAssistantOutput.model_validate(
        {
            "summary": "Users report repetitive recommendations in Discover Weekly.",
            "key_themes": ["Stale Discover Weekly"],
            "root_causes": ["Algorithm overfits listening history"],
            "affected_segments": ["Music Explorer"],
            "supporting_evidence": [
                {
                    "review_id": "550e8400-e29b-41d4-a716-446655440000",
                    "excerpt": "Discover Weekly is the same every week.",
                    "source": "playstore",
                    "rating": 2,
                }
            ],
            "product_opportunities": ["Refresh discovery mixes weekly"],
            "confidence": 0.82,
        }
    )
    assert output.confidence == 0.82
    assert len(output.supporting_evidence) == 1


def test_supporting_evidence_excerpt_max_length():
    with pytest.raises(ValidationError):
        SupportingEvidence.model_validate(
            {
                "review_id": "550e8400-e29b-41d4-a716-446655440000",
                "excerpt": "x" * 201,
                "source": "reddit",
                "rating": 3,
            }
        )


def test_empty_supporting_evidence_rejected():
    with pytest.raises(ValidationError):
        ResearchAssistantOutput.model_validate(
            {
                "summary": "Insufficient evidence.",
                "key_themes": [],
                "root_causes": [],
                "affected_segments": [],
                "supporting_evidence": [],
                "product_opportunities": [],
                "confidence": 0.2,
            }
        )
