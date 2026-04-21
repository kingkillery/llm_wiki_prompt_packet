---
description: lint and maintain the persistent wiki
allowed-tools:
  - "mcp__pk-qmd__*"
  - "mcp__obsidian__read_note"
  - "mcp__obsidian__write_note"
  - "mcp__obsidian__search_notes"
  - "mcp__obsidian__manage_tags"
  - "mcp__obsidian__move_note"
  - "mcp__llm-wiki-skills__skill_lookup"
  - "mcp__llm-wiki-skills__skill_validate"
  - "mcp__brv__*"
---
Read `CLAUDE.md`, `LLM_WIKI_MEMORY.md` if present, `.llm-wiki/config.json`, `wiki/index.md`, and recent `wiki/log.md`.

Lint the wiki for:

**Content:**
- contradictions between pages
- stale claims (check dates against wiki/log.md)
- orphan or weakly linked pages
- duplicate pages covering the same pattern
- broken links
- missing entity or concept pages
- obvious research gaps

**Routing:**
- stack-routing rules that are missing or unclear
- command files that are out of sync across the three copies (`.claude/commands/`, `.docker/vault/.claude/commands/`, `.docker/vault/.agent/workflows/`)

**Skills (per SKILL_CREATION_AT_EXPERT_LEVEL.md):**
- active skills missing required frontmatter fields (`id`, `status`, `kind`, `pii_review`, `validation_status`, `score`)
- active skills missing privacy review (`pii_review: passed`)
- active skills with weak or missing triggers
- active skills with no fast path
- active skills missing Failure Modes or Evidence sections
- retired skills still linked as active in the index
- feedback entries without a written reason (score delta alone is not sufficient)
- long tasks that created a skill with no brief reference (`brief_refs: []` is acceptable only for research-synthesis sources)
- skills with `validation_status: needs_revision` still in `active/` (should be revised or blocked)
- skills whose score has dropped below −3 (retire threshold) but haven't been moved to `retired/`
- `wiki/skills/index.md` rows missing required columns (kind, score, validation, applies-to)

Fix safe issues directly. Prefer `obsidian` MCP tools for vault mutations when available.
For renames and moves, always prefer `obsidian` `move_note` over direct file I/O to preserve link integrity.
If `obsidian` is unavailable, log the fallback in `wiki/log.md` and flag link-integrity risk.
Flag judgment-heavy recommendations separately.
Update `wiki/index.md` if needed and append a `lint` entry to `wiki/log.md`.

Return:
- stack/config used
- MCP tools used (or fallback note if `obsidian` was unavailable)
- files changed
- issues fixed
- issues deferred
- next best actions
