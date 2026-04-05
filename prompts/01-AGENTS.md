# LLM Wiki Agent Guide

Maintain this repo as a persistent markdown wiki built from immutable raw sources.

## Rules
- Never edit raw sources unless explicitly asked.
- Prefer updating existing wiki pages over creating duplicates.
- Maintain links and cross-references.
- Surface contradictions, uncertainty, and open questions explicitly.
- Make small, reversible edits by default.
- Ask before deletions, large renames, restructures, or schema changes.

## Startup
Before editing:
1. Read this file.
2. Read `wiki/index.md`.
3. Read recent entries in `wiki/log.md`.
4. Search for existing relevant pages.

## Task types

### Ingest
When a new source is added:
- read it
- create or update a source summary
- update affected entity/concept/synthesis pages
- update `wiki/index.md`
- append an entry to `wiki/log.md`

### Query
When answering questions:
- start from the wiki, not raw files
- read raw sources only when needed
- if the answer is durable, file it back into the wiki
- update `index.md` and `log.md` when filing

### Lint
Periodically check for:
- contradictions
- stale claims
- orphan or weakly linked pages
- missing concept/entity pages
- duplicate pages
- broken links
- obvious research gaps

Fix safe issues directly. Flag judgment-heavy issues.

## Defaults
- Prefer one-source-at-a-time ingestion unless asked to batch.
- Prefer concise pages over long notes.
- Preserve existing naming, structure, and link style.
- Keep `log.md` append-only.

## Done when
A task is complete only when the relevant wiki pages are updated, `index.md` is updated if needed, and `log.md` is updated if needed.
