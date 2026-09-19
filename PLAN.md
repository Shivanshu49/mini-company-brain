# Company Mini Brain — Implementation Plan

Ingest company data (tickets, meetings, Slack, docs) into **Cognee Cloud** and let people ask questions about it, with answers that cite their source documents.

> Cognee Cloud API details (auth, source metadata in search results, system prompt support) are **unverified**; Step 0 checks them before we build on them.

## Architecture

```
   ┌──────────────┐
   │ Streamlit UI │  chat + sources
   └──────┬───────┘
          │ HTTP
   ┌──────▼───────┐                                 ┌──────────────────────┐
   │ FastAPI API  │                                 │ Ingestion worker     │ (1 replica)
   │ /ask         │                                 │ loop: ingest, sleep N│
   └──────┬───────┘                                 │ state.db (SQLite)    │
          │ search only                             └──────────┬───────────┘
          │                                                    │ add + cognify
          └──────────────────►  Cognee Cloud  ◄────────────────┘
                           (graph, vectors, LLM, embeddings)
                                                               ▲ reads
                                     watched folder: paynest_dataset/paynest/data/
```

The API and the worker never talk to each other. Cognee Cloud is the only thing they share.

- **API**: stateless; only calls `search`. Can run any number of replicas.
- **Worker**: a dumb loop — run ingestion, sleep `INGEST_INTERVAL_SECONDS`, repeat. No HTTP endpoints. A plain loop can't overlap itself, and running exactly 1 replica means no two workers ingest the same files.
- **State table (`state.db`)**: per file: path, content hash, Cognee `data_id`, last ingested time. Local SQLite is safe because only the single worker opens it. Each run: scan folder → skip unchanged hashes → `add` new/changed files → one `cognify` for the batch (skipped if nothing changed). Logs a one-line summary (added / skipped).
- **Eval file** `paynest_dataset/paynest/eval/eval_questions.txt` is never ingested; the worker reads only `data/`.

## Answers and citations

- **Answer**: `search` with `GRAPH_COMPLETION` (the eval questions are multi-hop, which is what the graph is for).
- **Sources**: a second `CHUNKS` search on the same question returns matching chunks, mapped back to file names (`PAY-231`, `RFC-014`, …). Files already carry `ID:` / `SOURCE_TYPE:` headers. Also extract doc IDs mentioned in the answer text.
- **Unanswerable questions** (eval Q11, Q12): pass a system prompt — "Answer only from the company knowledge; otherwise reply 'Not found in company knowledge.'" Fallback if unsupported: return "Not found" when no relevant chunks come back.

## Code layout

```
app/config.py          env: COGNEE_API_URL, COGNEE_API_KEY, DATASET, DATA_DIR, INGEST_INTERVAL_SECONDS
app/cognee_client.py   small httpx wrapper for /api/v1/add, /cognify, /search (only file that knows Cognee's API)
api/main.py            FastAPI: /ask
worker/main.py         loop: run_ingestion(); sleep(INGEST_INTERVAL_SECONDS). `--once` flag runs a single pass and exits
worker/ingest.py       run_ingestion(): scan → hash → add changed → cognify → update state.db
ui/app.py              Streamlit chat page
scripts/spike.py       Step 0
scripts/eval.py        runs the 12 eval questions, checks expected sources were cited
Procfile               `honcho start` runs api + worker + ui with one command
```

We call the REST API directly with httpx rather than `cognee-sdk`: that PyPI package looks unofficial (its project links point to a `github.com/your-org` placeholder).

## Build order

0. **Cognee Cloud spike** (`scripts/spike.py`, ~30 min): add 3 files, cognify, search. Confirm:
   - how authentication works
   - whether search results identify the source file
   - whether search accepts a system prompt
   - how long cognify takes, and whether it is synchronous
   - that Cognee Cloud handles the LLM and embeddings (if so, Groq drops out)
1. **Worker**: `run_ingestion()`, state table, the loop. Ingest all 23 files.
2. **API**: `/ask` returning answer + sources.
3. **UI**: Streamlit chat, source cards labelled by type (ticket / meeting / Slack / doc).
4. **Eval script**: runs Q1–Q12, prints each answer next to its expected sources.
5. **Demo polish**: README, one-command start, a prepared file to drop in during the demo.

## Demo script

Run the worker with a short interval for the demo (e.g. `INGEST_INTERVAL_SECONDS=60`), with its log visible in a terminal.

1. Ask Q1 (why refund-service retries with backoff, who to contact): answer traces PAY-231 → MTG-2026-08-12 → RFC-014 → Rahul Verma, with source cards.
2. Ask Q2 (current max retries): answer is 5 and flags that RFC-014 is outdated.
3. Drop a prepared new file into the folder (e.g. `SLACK-2026-09-19_payments-eng.txt`: max retries now 7) → the worker log shows "1 added, 23 skipped" on its next pass → ask again; answer cites the new file. (Cognify time from Step 0 decides whether this is live or pre-recorded.)
4. Ask Q11 (cloud provider): "Not found in company knowledge."

## Out of scope / later

- Deletes
- Authentication and per-user permissions
- Connectors beyond the watched folder
- Non-text files
- Triggering ingestion from the UI (the worker runs on its schedule only)
- **Edited files**: a changed file is re-added, but its old version is not yet removed from Cognee. The old `data_id` is kept in the state table so removing it later is a small change.
