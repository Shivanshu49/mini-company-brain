import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path(__file__).parent / ".env")

COGNEE_API_URL = os.environ.get("COGNEE_API_URL", "").rstrip("/")
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY", "")
COGNEE_DATASET = os.environ.get("COGNEE_DATASET", "paynest")
DATA_DIR = ROOT / os.environ.get("DATA_DIR", "paynest_dataset/paynest/data")
STATE_DB = ROOT / os.environ.get("STATE_DB", "pipeline/state.db")
INGEST_INTERVAL_SECONDS = int(os.environ.get("INGEST_INTERVAL_SECONDS", "300"))
FILE_EXTENSIONS = {".txt", ".md"}

if not COGNEE_API_URL or not COGNEE_API_KEY:
    raise SystemExit("Set COGNEE_API_URL and COGNEE_API_KEY in pipeline/.env")
