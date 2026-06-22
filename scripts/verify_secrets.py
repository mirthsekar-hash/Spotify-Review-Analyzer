#!/usr/bin/env python
"""Verify production secrets (Phase 4.5.4)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.deploy.secrets import apply_streamlit_secrets, verify_secrets


def main() -> int:
    applied = apply_streamlit_secrets()
    if applied:
        print(f"Applied {applied} key(s) from Streamlit secrets.")

    result = verify_secrets()
    print(result.summary())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
