---
description: ingest one source into the persistent obsidian wiki
---
# Wiki ingest workflow

1. Read `AGENTS.md` if present.
2. Read `wiki/index.md`.
3. Read recent `wiki/log.md`.
4. Read the source the user wants ingested.
5. Extract:
   - entities
   - concepts
   - claims
   - dates or timeline items
   - contradictions
   - open questions
6. Create or update the source summary page.
7. Update all materially affected wiki pages.
8. Update `wiki/index.md`.
9. Append an `ingest` entry to `wiki/log.md`.
10. Return:
   - files read
   - files changed
   - uncertainties
   - next best actions
