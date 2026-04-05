---
name: llm-wiki-organizer
description: Use this skill when the repo is an Obsidian-style knowledge vault and the task is to ingest a source, answer from the persistent wiki, file a durable answer back into the wiki, or lint and maintain the wiki. Do not use it for unrelated code changes.
---

# LLM Wiki Organizer

This skill helps maintain a persistent markdown wiki built from immutable raw sources.

## Rules
- Never edit raw sources unless explicitly asked.
- Update existing wiki pages before creating duplicates.
- Keep links, contradictions, and open questions current.
- Update `wiki/index.md` when page inventory or routing changes.
- Append `wiki/log.md` for ingests, filed query outputs, and lint passes.
- Ask before deletions, restructures, or schema changes.

## Startup
1. Read `AGENTS.md` if present.
2. Read `wiki/index.md`.
3. Read recent `wiki/log.md`.
4. Search for existing pages before creating new ones.

## Workflows

### Ingest
Read the source, create or update its summary, update affected pages, then update `index.md` and append `log.md`.

### Query
Answer from the wiki first. Read raw sources only when needed. If the result will likely be useful again, file it back into the wiki and update `index.md` and `log.md`.

### Lint
Check for contradictions, stale claims, orphan pages, duplicates, broken links, missing entity or concept pages, and uncited claims. Fix safe issues directly and flag judgment-heavy ones.

## Response shape
- Task type
- Files read
- Files changed
- What changed
- Unresolved questions / conflicts
