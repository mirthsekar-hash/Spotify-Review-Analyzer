"""Thin wrapper for Streamlit Cloud and local development."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import clear_settings_cache
from src.deploy.secrets import apply_streamlit_secrets

if apply_streamlit_secrets():
    clear_settings_cache()

from app.main import main

main()
