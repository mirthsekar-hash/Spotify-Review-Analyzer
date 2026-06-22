"""Deployment smoke test — Phase 4.5.5."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from src.deploy.secrets import SecretCheckResult, verify_secrets

ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = ROOT / "app" / "pages"
FALLBACK_DIR = ROOT / "data" / "fallback"

EXPECTED_PAGES: tuple[str, ...] = (
    "01_executive_summary.py",
    "02_source_analysis.py",
    "03_discovery_challenges.py",
    "04_theme_explorer.py",
    "05_segment_explorer.py",
    "06_root_cause_analysis.py",
    "07_unmet_needs.py",
    "08_discovery_journey.py",
    "09_interview_validation.py",
)


@dataclass
class SmokeTestResult:
    ok: bool
    checks: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = ["Smoke test " + ("PASSED" if self.ok else "FAILED")]
        for check in self.checks:
            lines.append(f"  [ok] {check}")
        for failure in self.failures:
            lines.append(f"  [fail] {failure}")
        for warning in self.warnings:
            lines.append(f"  [warn] {warning}")
        return "\n".join(lines)


def _check_pages() -> list[str]:
    missing = [name for name in EXPECTED_PAGES if not (PAGES_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing dashboard pages: {', '.join(missing)}")
    return [f"All {len(EXPECTED_PAGES)} dashboard pages present"]


def _check_fallback_csvs() -> list[str]:
    required = ("playstore_sample.csv", "appstore_sample.csv", "reddit_sample.csv")
    missing = [name for name in required if not (FALLBACK_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing fallback CSVs: {', '.join(missing)}")
    return [f"Fallback CSVs bundled ({len(required)} files)"]


def _check_db() -> list[str]:
    from src.db.client import check_connection  # noqa: PLC0415

    if not check_connection():
        raise ConnectionError("Supabase connection failed")
    return ["Supabase connection OK"]


def _check_rag_stack() -> list[str]:
    importlib.import_module("src.rag.retriever")
    importlib.import_module("src.rag.context_builder")
    importlib.import_module("src.rag.research_assistant")
    return ["RAG stack imports OK"]


def _check_deployed_url(base_url: str, timeout: float) -> list[str]:
    url = base_url.rstrip("/")
    health_url = f"{url}/_stcore/health"
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(health_url)
        response.raise_for_status()
        home = client.get(url)
        home.raise_for_status()
    return [f"Deployed app reachable at {url}"]


def run_smoke_test(
    *,
    base_url: str | None = None,
    skip_db: bool = False,
    timeout: float = 15.0,
) -> SmokeTestResult:
    """Run local or post-deploy smoke checks."""
    result = SmokeTestResult(ok=True)

    secret_result: SecretCheckResult = verify_secrets()
    if secret_result.ok:
        result.checks.append("Required secrets configured")
    else:
        result.ok = False
        result.failures.append(secret_result.summary())

    for warning in secret_result.warnings:
        result.warnings.append(warning)

    structural_checks = (
        _check_pages,
        _check_fallback_csvs,
        _check_rag_stack,
    )
    for check in structural_checks:
        try:
            result.checks.extend(check())
        except Exception as exc:
            result.ok = False
            result.failures.append(str(exc))

    if not skip_db:
        try:
            result.checks.extend(_check_db())
        except Exception as exc:
            result.ok = False
            result.failures.append(str(exc))
    else:
        result.warnings.append("Database check skipped")

    if base_url:
        try:
            result.checks.extend(_check_deployed_url(base_url, timeout))
        except Exception as exc:
            result.ok = False
            result.failures.append(f"Deployed URL check failed: {exc}")

    return result
