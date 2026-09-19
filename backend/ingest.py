"""Load the PayNest sources into Cognee and build the knowledge graph.
Run once before starting the API (cognify is slow). Re-running only processes new or changed files."""
import asyncio

from brain import DATA, DATASET, cognee

EXTRACTION_PROMPT = """Extract a knowledge graph from this PayNest company record.
Entity types: Person, Team, Service, Ticket, Decision, Meeting, Document, SlackThread, Rule, Bank, PullRequest, Incident.
- Use the record's ID exactly as written (e.g. PAY-231, RFC-014, MTG-2026-08-12, SLACK-2026-08-20, INC-017, DOC-004) as the name of the record's own node, and keep its DATE.
- Use people's full names (e.g. Priya Sharma) and service names as written (e.g. refund-service).
- Capture who decided, proposed, approved, owns, implemented, reported, is assigned or is blocked by what,
  which records reference or supersede other records, and which settings a decision sets (e.g. max retries 3 or 5)."""


async def main():
    for folder in sorted(p for p in DATA.iterdir() if p.is_dir()):  # docs, meetings, slack, tickets
        files = [str(f) for f in sorted(folder.glob("*.txt"))]
        await cognee.add(files, dataset_name=DATASET, node_set=[folder.name])
        print(f"added {len(files)} files from {folder.name}/")
    await cognee.cognify(datasets=[DATASET], custom_prompt=EXTRACTION_PROMPT)
    print("cognify done")


if __name__ == "__main__":
    asyncio.run(main())
