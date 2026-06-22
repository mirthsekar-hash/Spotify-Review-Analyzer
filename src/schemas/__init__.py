"""Structured output schemas."""

from src.schemas.executive_summary import ExecutiveSummaryOutput
from src.schemas.interview_insight import InterviewInsightCreate, InterviewInsightUpdate
from src.schemas.research_assistant import ResearchAssistantOutput, SupportingEvidence
from src.schemas.review_analysis import ReviewAnalysisOutput, UserSegmentOutput
from src.schemas.root_causes import RootCauseItem, RootCauseOutput
from src.schemas.segments import SegmentSummary, SegmentationOutput
from src.schemas.themes import ThemeExtractionOutput, ThemeItem
from src.schemas.unmet_needs import UnmetNeedItem, UnmetNeedsOutput

__all__ = [
    "ExecutiveSummaryOutput",
    "InterviewInsightCreate",
    "InterviewInsightUpdate",
    "ResearchAssistantOutput",
    "SupportingEvidence",
    "ReviewAnalysisOutput",
    "UserSegmentOutput",
    "ThemeItem",
    "ThemeExtractionOutput",
    "SegmentSummary",
    "SegmentationOutput",
    "RootCauseItem",
    "RootCauseOutput",
    "UnmetNeedItem",
    "UnmetNeedsOutput",
]
