"""Configuration management and environment variable loading for Google Gemini."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root if present
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
