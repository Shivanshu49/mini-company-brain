"""API settings. Read from backend/.env locally, from the host's env vars in production. Independent of pipeline/."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path(__file__).parent / ".env")

COGNEE_API_URL = os.environ.get("COGNEE_API_URL", "").rstrip("/")
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY", "")
COGNEE_DATASET = os.environ.get("COGNEE_DATASET", "paynest")
DATA_DIR = ROOT / os.environ.get("DATA_DIR", "paynest_dataset/paynest/data")  # read for source cards only

# Optional: when set, Groq writes the answer from Cognee's retrieved context (one Cognee call instead of two).
# When unset, or if Groq fails, Cognee Cloud's own LLM writes the answer.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

if not COGNEE_API_URL or not COGNEE_API_KEY:
    raise SystemExit("Set COGNEE_API_URL and COGNEE_API_KEY in backend/.env")
