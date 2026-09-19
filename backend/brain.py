"""Cognee setup + grounded Q&A. ask(question) -> {answer, sources, path, conflicts}"""
import asyncio
import json
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env", override=True)

import cognee  # noqa: E402  (must import after .env is loaded)
from cognee import SearchType  # noqa: E402

cognee.config.data_root_directory(str(ROOT / ".data_storage"))
cognee.config.system_root_directory(str(ROOT / ".cognee_system"))

DATA = ROOT.parent / "paynest_dataset/paynest/data"  # eval/ is a sibling, never ingested
DATASET = "paynest"
ID = re.compile(r"\b((?:DOC|RFC|PAY|INC)-\d{3}|(?:MTG|SLACK)-\d{4}-\d{2}-\d{2})\b")
TYPES = {"docs": "document", "tickets": "ticket", "meetings": "meeting", "slack": "slack"}
REFUSAL = "Not found in company knowledge."

SYSTEM_PROMPT = f"""You are PayNest Brain, the company knowledge assistant for PayNest.
Answer ONLY from the provided context. Never use outside knowledge and never guess.
- After each fact, cite its source ID in parentheses, e.g. (PAY-231), (RFC-014), (MTG-2026-09-04), (SLACK-2026-09-10).
- Use people's full names. When asked who to contact, give the service owner and backup (DOC-004).
- If sources disagree, trust the one with the newest date, give that answer, and say the older source is outdated by its ID.
  Then add a final line exactly in this form:
  OUTDATED: <older ID> | <newer ID> | <one sentence on what changed>
- If the context does not answer the question, reply exactly: {REFUSAL}
Keep the answer under 130 words, in plain sentences."""


def _index() -> dict[str, dict]:
    """Source metadata from the file headers: id -> {id, type, title, date, body}."""
    idx = {}
    for f in sorted(DATA.glob("*/*.txt")):
        text = f.read_text()
        if f.parent.name == "tickets":  # JSON under a SOURCE_TYPE line
            j = json.loads(text.split("\n", 1)[1])
            meta = {"id": j["id"], "title": j["title"], "date": j.get("created") or j["started"][:10]}
            fields = ("description", "impact", "resolution", "root_cause", "blocked_by")
            body = [str(j[k]) for k in fields if k in j] + [c["text"] for c in j.get("comments", [])]
        else:
            head, _, rest = text.partition("\n\n")
            h = dict(re.findall(r"^(\w+): (.+)$", head, re.M))
            meta = {"id": h["ID"], "title": h.get("TITLE") or h.get("CHANNEL", ""), "date": h["DATE"]}
            body = [rest]
        idx[meta["id"]] = {**meta, "type": TYPES[f.parent.name], "body": "\n".join(body)}
    return idx


SOURCES = _index()


def _words(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", s.lower()))


def _snippet(body: str, text: str) -> str:
    """The two sentences of a source that overlap most with the question + answer."""
    want = _words(text)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if len(s.strip()) > 20]
    top = sorted(sents, key=lambda s: len(want & _words(s)), reverse=True)[:2]
    return " ".join(s for s in sents if s in top)[:320]


def _edges(context: str) -> list[dict]:
    """Parse Cognee graph context lines like 'A --[relation]--> B' into edges."""
    edges = []
    for a, rel, b in re.findall(r"^\s*(.+?)\s*--\[?(.+?)\]?-->\s*(.+?)\s*$", context, re.M):
        edges.append({"source": a, "target": b, "label": rel.replace("_", " ")})
    return edges[:25]


async def _search(q: str, kind: SearchType, **kw):
    res = await asyncio.wait_for(cognee.search(query_text=q, query_type=kind, datasets=[DATASET], **kw), 60)
    return "\n".join(str(r.search_result if hasattr(r, "search_result") else r) for r in res)


async def ask(question: str) -> dict:
    try:
        answer = await _search(question, SearchType.GRAPH_COMPLETION, system_prompt=SYSTEM_PROMPT)
    except Exception:  # timeout or graph failure: plain vector RAG still gives a grounded answer
        answer = await _search(question, SearchType.RAG_COMPLETION, system_prompt=SYSTEM_PROMPT)
    answer = answer.strip()

    conflicts = []
    for old, new, note in re.findall(r"^OUTDATED:\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(.+)$", answer, re.M):
        conflicts.append({"outdated": old, "current": new, "note": note.strip()})
    answer = re.sub(r"^OUTDATED:.*$", "", answer, flags=re.M).strip()

    if REFUSAL.lower().rstrip(".") in answer.lower():
        return {"answer": REFUSAL, "sources": [], "path": [], "conflicts": []}

    try:
        path = _edges(await _search(question, SearchType.GRAPH_COMPLETION, only_context=True))
    except Exception:
        path = []

    ids = list(dict.fromkeys(ID.findall(answer + " " + " ".join(c["note"] for c in conflicts))))
    text = question + " " + answer
    sources = [
        {k: s[k] for k in ("id", "type", "title", "date")} | {"snippet": _snippet(s["body"], text)}
        for s in (SOURCES.get(i) for i in ids) if s
    ]
    return {"answer": answer, "sources": sources, "path": path, "conflicts": conflicts}


if __name__ == "__main__":
    import sys
    print(json.dumps(asyncio.run(ask(" ".join(sys.argv[1:]))), indent=2))
