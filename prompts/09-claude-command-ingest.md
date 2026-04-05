---
description: ingest a single source into the persistent wiki
---
Read `CLAUDE.md`, then read `wiki/index.md` and recent `wiki/log.md`.

Ingest the specified source into the wiki:
- create or update a source summary
- update affected entity, concept, synthesis, comparison, or timeline pages
- update `wiki/index.md`
- append an `ingest` entry to `wiki/log.md`

Rules:
- do not edit raw sources unless explicitly asked
- prefer updating pages over creating duplicates
- surface contradictions and open questions explicitly

Return:
- files read
- files changed
- what changed
- unresolved questions
