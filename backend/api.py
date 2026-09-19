"""FastAPI server: POST /ask, GET /health. Run from the repo root: uvicorn backend.api:app --port 8000"""
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints

from backend.brain import _index, ask

app = FastAPI(title="PayNest Brain")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Question(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


@app.post("/ask")
def ask_endpoint(body: Question):
    q = body.question
    try:
        return ask(q)
    except Exception:
        try:  # one retry: Cognee Cloud timeouts and LLM hiccups are usually transient
            return ask(q)
        except Exception as e:
            raise HTTPException(503, f"Knowledge base unavailable: {type(e).__name__}") from e


@app.get("/health")
def health():
    return {"status": "ok", "sources": len(_index())}
