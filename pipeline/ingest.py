"""One ingestion pass: scan folder -> add new files / update changed ones -> cognify -> record state."""

import hashlib
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pipeline import cognee_client as cognee
from pipeline import config

log = logging.getLogger("pipeline")

# Steers Cognee's entity extraction so graph nodes use the record IDs and names the answers cite.
EXTRACTION_PROMPT = """Extract a knowledge graph from this PayNest company record.
Entity types: Person, Team, Service, Ticket, Decision, Meeting, Document, SlackThread, Rule, Bank, PullRequest, Incident.
- Use the record's ID exactly as written (e.g. PAY-231, RFC-014, MTG-2026-08-12, SLACK-2026-08-20, INC-017, DOC-004) as the name of the record's own node, and keep its DATE.
- Use people's full names (e.g. Priya Sharma) and service names as written (e.g. refund-service).
- Capture who decided, proposed, approved, owns, implemented, reported, is assigned or is blocked by what,
  which records reference or supersede other records, and which settings a decision sets (e.g. max retries 3 or 5)."""


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(config.STATE_DB)
    db.execute(
        "CREATE TABLE IF NOT EXISTS documents ("
        " path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, data_id TEXT, ingested_at TEXT NOT NULL)"
    )
    return db


def _scan() -> dict[str, Path]:
    return {
        str(p.relative_to(config.DATA_DIR)): p
        for p in sorted(config.DATA_DIR.rglob("*"))
        if p.is_file() and p.suffix in config.FILE_EXTENSIONS
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metadata(rel: str, path: Path) -> dict:
    # First line of every dataset file is "SOURCE_TYPE: <type>".
    first = path.read_text(errors="ignore").splitlines()[:1]
    source_type = first[0].split(":", 1)[1].strip() if first and first[0].startswith("SOURCE_TYPE:") else "unknown"
    return {"source_path": rel, "doc_id": path.stem, "source_type": source_type}


def run_ingestion() -> dict:
    db = _db()
    known = {row[0]: (row[1], row[2]) for row in db.execute("SELECT path, sha256, data_id FROM documents")}
    files = _scan()

    new, changed, skipped = [], [], 0
    for rel, path in files.items():
        digest = _sha256(path)
        if rel not in known:
            new.append((rel, path, digest))
        elif known[rel][0] != digest:
            changed.append((rel, path, digest))
        else:
            skipped += 1

    summary = {"new": len(new), "changed": len(changed), "skipped": skipped}
    if not new and not changed:
        log.info("nothing to do: %s", summary)
        return summary

    dataset = config.COGNEE_DATASET
    dataset_id = cognee.get_dataset_id(dataset)
    now = datetime.now(timezone.utc).isoformat()

    # Changed files: PATCH /update re-processes the document in place, no separate cognify needed.
    to_add = list(new)
    for rel, path, digest in changed:
        data_id = known[rel][1]
        if not (data_id and dataset_id):
            to_add.append((rel, path, digest))  # never got an id; fall back to add
            continue
        log.info("updating %s", rel)
        cognee.update_file(path, data_id, dataset_id)
        db.execute("UPDATE documents SET sha256=?, ingested_at=? WHERE path=?", (digest, now, rel))
        db.commit()

    if to_add:
        for rel, path, _ in to_add:
            log.info("adding %s", rel)
            try:
                cognee.add_file(path, dataset, _metadata(rel, path), node_set=[path.parent.name])
            except cognee.Conflict:
                # Exists remotely with different content (e.g. state.db was wiped): update it instead.
                dataset_id = dataset_id or cognee.get_dataset_id(dataset)
                remote = next((d for d in cognee.list_data(dataset_id) if _matches(d, path)), None)
                if not remote:
                    raise
                log.info("already in cognee with different content, updating %s", rel)
                cognee.update_file(path, remote["id"], dataset_id)

        dataset_id = dataset_id or cognee.get_dataset_id(dataset)
        log.info("cognify started for %d file(s)", len(to_add))
        cognee.cognify(dataset, dataset_id, custom_prompt=EXTRACTION_PROMPT)
        log.info("cognify completed")

        # Record state only after cognify succeeds, so a failed run is retried next pass.
        ids = {d.get("name"): d.get("id") for d in cognee.list_data(dataset_id)}
        for rel, path, digest in to_add:
            data_id = ids.get(path.stem) or ids.get(path.name)
            db.execute(
                "INSERT INTO documents (path, sha256, data_id, ingested_at) VALUES (?, ?, ?, ?)"
                " ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256, data_id=excluded.data_id,"
                " ingested_at=excluded.ingested_at",
                (rel, digest, data_id, now),
            )
        db.commit()

    log.info("done: %s", summary)
    return summary


def _matches(remote: dict, path: Path) -> bool:
    return remote.get("name") in (path.stem, path.name)
