"""Thin wrapper for Streamlit Cloud and local development."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.deploy.secrets import bootstrap_settings

bootstrap_settings()

from app.main import main

main()
