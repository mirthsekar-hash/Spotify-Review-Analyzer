#!/usr/bin/env python
"""Local or deployed smoke test (Phase 4.5.5)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.deploy.secrets import apply_streamlit_secrets
from src.deploy.smoke import run_smoke_test


def main() -> int:
    parser = argparse.ArgumentParser(description="Spotify Review Analyzer deployment smoke test")
    parser.add_argument(
        "--url",
        help="Deployed app base URL (e.g. https://your-app.streamlit.app)",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip Supabase connectivity check",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout for deployed URL checks (seconds)",
    )
    args = parser.parse_args()

    apply_streamlit_secrets()
    result = run_smoke_test(
        base_url=args.url,
        skip_db=args.skip_db,
        timeout=args.timeout,
    )
    print(result.summary())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
