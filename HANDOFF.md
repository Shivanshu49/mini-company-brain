# Handoff: Company Mini Brain (Cognee) — Planning Thread

Paste or reference this file in a new thread to resume. Hackathon rules are in `CLAUDE.md` and `.claude/skills/hackathon/SKILL.md` (no TDD, tight scope, working demo first).

## Problem statement
Build a "company mini brain" using **cognee**: ingest company data and let people ask questions about it.

## Architecture (agreed so far)

Two workflows, separate in the code:

**Ingestion:** company data source → text-based ingestor → `cognee.add()` + `cognee.cognify()`
- Runs as a scheduled job at a set interval; also exposed as an "Ingest now" endpoint/button for the demo.
- Picks up only new or changed data (see below).

**Access:** UI → Python backend (FastAPI) → `cognee.search()` → answer + source docs back to the UI

```
UI  ──►  FastAPI backend  ──►  cognee.search()  ──►  Groq (LLM)
                  │
                  └── scheduler job ──► connector ──► cognee.add() + cognee.cognify()
```

## Key facts and decisions
- **LLM = Groq (groq.com inference API).** It is only the LLM; its playground can't serve as our UI.
- **We build our own small UI:** one chat page (Streamlit, or a simple React/HTML page) showing the answer plus source documents.
- **Cognee is a Python library that runs inside our backend**, not a separate service. By default it stores data in local files: SQLite (relational), LanceDB (vectors), Kuzu (graph).
- **Groq has no embeddings API**, so we need a separate embedding model: fastembed locally (free, no key) or OpenAI/Gemini embeddings. Set this up on day one.
- **Groq free-tier rate limits:** `cognify` makes many LLM calls, so keep the demo dataset small (tens of docs).
- **`cognify` is slow.** Run it only in the ingestion job, never in the request path. The UI calls only `search`.
- **Show sources in answers:** store the source path or URL as metadata when calling `add`.
- **Only new or changed data:**
  - At the source: a small state table recording, per source, a watermark (last `modified_at` or ID) and a content hash per document. Skip unchanged hashes; this also catches edits.
  - In cognee: it deduplicates by content, and re-running `cognify` may only process new data in recent versions. Verify this against the installed version.
  - Deletes are **out of scope**.
- **Out of scope:** authentication, per-user permissions, multiple tenants, deletes, non-text files.

## Open decision: where ingestion runs
The user wants ingestion separate from the API, with a single worker to avoid races between ingestion jobs. The remaining problem: **Kuzu is embedded**, so while the worker holds it open for writing, the API process probably can't open it to run searches (verify with the installed version). Options:

| Option | Setup | Trade-off |
|---|---|---|
| **A. Same process** (APScheduler inside FastAPI) | No infra, cognee's defaults | Separated in code only; one deployable |
| **B. Separate worker + server databases** | docker-compose with Postgres + pgvector and Neo4j; cognee supports both through config | True separation; about an hour of extra setup and one more thing that can break |

**Recommendation: A.** Put ingestion in an `ingestion/` module with a `run_ingestion()` entry point, so moving it to a separate worker later only means changing which process calls it. **The user hasn't chosen yet.**

## Open questions for the user
1. Option A or B for ingestion?
2. Which data sources? Recommended: a watched folder of `.md`/`.txt` files, plus at most one real connector (Notion, Slack export or Google Docs).
3. Which embedding provider (fastembed local vs OpenAI/Gemini)?
4. UI choice (Streamlit vs a simple React/HTML page)?

## Build order
1. Script: `add` + `cognify` on 5 sample docs, then `search`, with Groq and embeddings configured. **Get this working first.** *(Next step; offered to scaffold.)*
2. FastAPI with `/ask` and `/ingest`.
3. Folder connector plus the state table for new/changed docs, plus the scheduler job (per the A/B decision).
4. Chat UI with sources shown.
5. Realistic seed data (fake company handbook, meeting notes, product docs).
6. Optional: a second connector.

## Demo moment
Drop a new file into the watched folder → click "Ingest now" → ask about it → the answer comes back with a citation to that file.

## Current state of the repo
- `CLAUDE.md`: tells Claude to always use the hackathon skill.
- `.claude/skills/hackathon/SKILL.md`: hackathon rules.
- `SKILL.md` at the root: empty and unused; safe to delete.
- No code written yet.
