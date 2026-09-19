"""FastAPI server: POST /ask, GET /health. Run: uvicorn api:app --port 8000"""
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from brain import ROOT, SOURCES, ask

app = FastAPI(title="PayNest Brain")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ponytail: answers cached to a JSON file so demo questions are instant and survive LLM hiccups.
# Delete cache.json after re-ingesting; swap for a real cache if this ever serves more than a demo.
CACHE_FILE = ROOT / "cache.json"
CACHE: dict = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.post("/ask")
async def ask_endpoint(body: Question):
    q = body.question.strip()
    if q in CACHE:
        return CACHE[q]
    try:
        result = await ask(q)
    except Exception:
        try:  # one retry: Groq rate limits and timeouts are usually transient
            result = await ask(q)
        except Exception as e:
            raise HTTPException(503, f"Knowledge base unavailable: {type(e).__name__}") from e
    CACHE[q] = result
    CACHE_FILE.write_text(json.dumps(CACHE, indent=2))
    return result


@app.get("/health")
def health():
    return {"status": "ok", "sources": len(SOURCES)}
