"""Structured output schema for AI-generated executive summary."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExecutiveSummaryOutput(BaseModel):
    """Validated LLM response for the executive summary panel."""

    summary: str = Field(
        min_length=1,
        max_length=1200,
        description="2–4 sentence executive overview for product leadership",
    )
    key_findings: list[str] = Field(
        min_length=2,
        max_length=6,
        description="Bullet-ready findings grounded in themes, segments, and review evidence",
    )
    top_opportunity: str = Field(
        min_length=1,
        max_length=500,
        description="Single highest-impact product opportunity",
    )


def format_executive_summary_markdown(output: ExecutiveSummaryOutput) -> str:
    findings = "\n".join(f"- {finding}" for finding in output.key_findings)
    return (
        f"{output.summary}\n\n"
        f"### Key Findings\n"
        f"{findings}\n\n"
        f"### Top Opportunity\n"
        f"{output.top_opportunity}"
    )
