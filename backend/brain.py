"""Grounded Q&A over the Cognee Cloud dataset the pipeline fills. ask(question) -> {answer, sources, path, conflicts}"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from pipeline import cognee_client as cognee
from pipeline import config

DATA = config.DATA_DIR  # same folder the pipeline ingests; eval/ is a sibling, never ingested
DATASET = config.COGNEE_DATASET
ID = re.compile(r"(?<![A-Za-z0-9])((?:DOC|RFC|PAY|INC)-\d{3}|(?:MTG|SLACK)-\d{4}-\d{2}-\d{2})(?!\d)")
TYPES = {"docs": "document", "tickets": "ticket", "meetings": "meeting", "slack": "slack"}
REFUSAL = "Not found in company knowledge."
NOISE_RELATIONS = {"made_from", "is_part_of"}  # Cognee's chunk/summary bookkeeping edges

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
    """Source metadata from the file headers: id -> {id, type, title, date, body}.
    Rebuilt on every call so files the pipeline picked up since startup are citable."""
    idx = {}
    for f in sorted(DATA.glob("*/*.txt")):
        try:
            text = f.read_text()
            if text.split("\n", 1)[1].lstrip().startswith("{"):  # tickets: JSON under a SOURCE_TYPE line
                j = json.loads(text.split("\n", 1)[1])
                meta = {"id": j["id"], "title": j["title"], "date": j.get("created") or j["started"][:10]}
                fields = ("description", "impact", "resolution", "root_cause", "blocked_by")
                body = [str(j[k]) for k in fields if k in j] + [c["text"] for c in j.get("comments", [])]
            else:
                head, _, rest = text.partition("\n\n")
                h = dict(re.findall(r"^(\w+): (.+)$", head, re.M))
                meta = {"id": h["ID"], "title": h.get("TITLE") or h.get("CHANNEL", ""), "date": h["DATE"]}
                body = [rest]
        except (IndexError, KeyError, ValueError):
            continue  # file without the expected header: still searchable in Cognee, just not shown as a card
        idx[meta["id"]] = {**meta, "type": TYPES.get(f.parent.name, "document"), "body": "\n".join(body)}
    return idx


def _words(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", s.lower()))


def _snippet(body: str, text: str) -> str:
    """The two sentences of a source that overlap most with the question + answer."""
    want = _words(text)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if len(s.strip()) > 20]
    top = sorted(sents, key=lambda s: len(want & _words(s)), reverse=True)[:2]
    return " ".join(s for s in sents if s in top)[:320]


def _node(name: str) -> str:
    """Chunk nodes are named after their raw text; show them as their document ID instead."""
    m = ID.search(name)
    return m.group(1) if m else re.sub(r"\s*\[[^\]]*\]$", "", name).strip()


def _edges(context: str) -> list[dict]:
    """Parse Cognee context lines 'A --[relation]--> B  (description)' into edges."""
    edges, seen = [], set()
    for a, rel, b in re.findall(r"^(.+?) --\[(.+?)\]--> (.+?)(?:\s{2}\(.*\))?$", context, re.M):
        a, b = _node(a), _node(b)
        if rel in NOISE_RELATIONS or a == b or max(len(a), len(b)) > 60 or (a, rel, b) in seen:
            continue
        seen.add((a, rel, b))
        edges.append({"source": a, "target": b, "label": rel.replace("_", " ")})
    return edges[:25]


def _text(results: list[dict]) -> str:
    out = []
    for r in results:
        res = r.get("search_result", r) if isinstance(r, dict) else r
        out.extend(res if isinstance(res, list) else [res])
    return "\n".join(str(x) for x in out)


def _answer(question: str) -> str:
    kw = {"datasets": [DATASET], "system_prompt": SYSTEM_PROMPT, "include_references": True}
    try:
        return _text(cognee.search(question, "GRAPH_COMPLETION", **kw))
    except Exception:  # timeout or graph failure: plain vector RAG still gives a grounded answer
        return _text(cognee.search(question, "RAG_COMPLETION", **kw))


def _context(question: str) -> str:
    try:
        return _text(cognee.search(question, "GRAPH_COMPLETION", datasets=[DATASET], only_context=True))
    except Exception:
        return ""


def ask(question: str) -> dict:
    with ThreadPoolExecutor(2) as pool:
        answer_f, context_f = pool.submit(_answer, question), pool.submit(_context, question)
        answer = answer_f.result().strip()

    # include_references appends "Evidence:\n- chunk N of document <name> (...)"; keep the names, drop the block.
    answer, _, evidence = answer.partition("\nEvidence:")
    evidence_ids = ID.findall(evidence)
    answer = answer.replace("‑", "-").replace("**", "")  # non-breaking hyphens break ID matching; UI is plain text
    # Cognee's model sometimes cites with 【ID】 too: drop ones already cited in parentheses, convert the rest.
    paren_cited = set(ID.findall(" ".join(re.findall(r"\([^)]*\)", answer))))
    answer = re.sub(
        r"\s*【\s*([^】]+?)\s*】",
        lambda m: "" if set(ID.findall(m.group(1))) <= paren_cited and ID.search(m.group(1)) else f" ({m.group(1)})",
        answer,
    )

    conflicts = []
    for line in re.findall(r"^OUTDATED:(.*)$", answer, re.M):
        parts = [p.strip() for p in line.split("|")]
        old, new = (ID.search(p) for p in (parts + ["", ""])[:2])
        if old and new:
            conflicts.append({"outdated": old.group(1), "current": new.group(1), "note": " | ".join(parts[2:]) or line.strip()})
    answer = re.sub(r"^OUTDATED:.*$", "", answer, flags=re.M).strip()

    if REFUSAL.lower().rstrip(".") in answer.lower():
        return {"answer": REFUSAL, "sources": [], "path": [], "conflicts": []}

    path = _edges(context_f.result())

    # Cited IDs first; fall back to Cognee's retrieved documents if the answer cited nothing.
    cited = ID.findall(answer + " " + " ".join(c["outdated"] + " " + c["current"] + " " + c["note"] for c in conflicts))
    ids = list(dict.fromkeys(cited or evidence_ids))
    index, text = _index(), question + " " + answer
    sources = [
        {k: s[k] for k in ("id", "type", "title", "date")} | {"snippet": _snippet(s["body"], text)}
        for s in (index.get(i) for i in ids) if s
    ]
    return {"answer": answer, "sources": sources, "path": path, "conflicts": conflicts}


if __name__ == "__main__":
    print(json.dumps(ask(" ".join(sys.argv[1:])), indent=2))
