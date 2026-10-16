import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://satjeet:satjeet@127.0.0.1:5432/rfq_normalizer")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
GIT_SHA = os.getenv("GIT_SHA", "unknown")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
