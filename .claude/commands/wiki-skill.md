---
description: create, refine, review, or retire reusable skills at expert level
allowed-tools:
  - "mcp__pk-qmd__*"
  - "mcp__obsidian__read_note"
  - "mcp__obsidian__write_note"
  - "mcp__obsidian__search_notes"
  - "mcp__obsidian__manage_tags"
  - "mcp__llm-wiki-skills__*"
  - "mcp__brv__*"
---
Read `CLAUDE.md`, then read `LLM_WIKI_MEMORY.md` if present, `SKILL_CREATION_AT_EXPERT_LEVEL.md` if present, `.llm-wiki/config.json`, `wiki/index.md`, `wiki/skills/index.md`, and recent `wiki/log.md`.

## Retrieval Protocol (apply before every search)

**Step 0 — Context gate:** Check `wiki/skills/index.md` and the current conversation for a matching skill before any tool call.

**Step 1 — Cheap tier:** If the skill MCP server is available, call `skill_lookup` first. If it resolves the question fully, stop — do not also fire `pk-qmd`.

**Step 2 — Standard tier:** Only escalate to `pk-qmd` if `skill_lookup` misses or the skill MCP server is unavailable. One `pk-qmd` lex call to find related skill pages or evidence.

**Step 3 — Full tier:** `pk-qmd` lex + vec for novel skills with no prior art. Cap at 2 hops. `brv` in parallel only if user workflow preferences affect the skill shape.

Create or update a reusable skill from the current task, trajectory, or evidence:
- if the local skill MCP server is available, call `skill_lookup` before exploring
- for long tasks or expensive exploration, call `skill_reflect` or `skill_pipeline_run` first so the important context is captured as a reducer packet plus artifact refs
- call `skill_validate` before direct save when the candidate is non-trivial, likely duplicated, or needs explicit review
- use `skill_propose`, `skill_feedback`, or `skill_retire` for lifecycle operations
- search for existing related skills first
- write or update the skill page under `wiki/skills/active/`
- append reasoned review notes under `wiki/skills/feedback/` when the task is feedback-driven
- retire the skill into `wiki/skills/retired/` when evidence shows it is unsafe or the score should fall below the retirement threshold
- update `wiki/skills/index.md`
- append a `skill` entry to `wiki/log.md`

Skill requirements:
- optimize for learn-once, reuse-forever shortcuts
- include trigger, preconditions, fast path, failure modes, and evidence
- run a privacy gate before saving
- validate duplicates before saving, and merge deltas when overlap is strong
- for long tasks, capture a strong middle-manager reducer packet with an explicit `route_decision`
- prefer a 1-3 call reusable recipe over verbose narrative
- mark HTTP upgrade candidates explicitly, but do not claim them without evidence

## Post-save Sync

After creating or editing any skill page under `wiki/skills/active/`, determine whether the skill belongs in the canonical `pk-skills1` source of truth (`C:\Users\prest\.agents\skills1\pk-skills1`).

**Decision rule:**
- Local operational shortcut for this vault only → no sync needed. Note in the skill's review trail.
- Reusable across sessions and projects → promote to pk-skills1, then launch `skill-sync-manager` as a background sub-agent to propagate to all mirrors.

**When syncing, launch `skill-sync-manager` with this brief (fill in concrete paths):**

```text
Source of truth: C:\Users\prest\.agents\skills1\pk-skills1
Changed skills:
- <skill-root>

Destinations to check:
- C:\Users\prest\.codex\skills
- C:\Users\prest\.pi\agent\skills\pk-skills1-imported
- C:\Users\prest\.agents\skills
- C:\Users\prest\.claude\skills

Backup location: C:\dev\Desktop-Projects\Helpful-Docs-Prompts\skills1-backup

Constraints:
- validate each changed skill before syncing
- safe add/update only — never delete without explicit approval
- preserve destination-local customizations
- create a dated zip backup entry before mirroring

Return: changed skills, validation results, actions taken, approval-required follow-ups
```

**Divergence rule:** Update the source-of-truth package first. Combine any mirror-only content into pk-skills1 before mirroring outward. Never edit mirrors first.

**If background sub-agents are unavailable:** run `managed-skill-sync` inline:
```powershell
python .codex\skills\managed-skill-sync\scripts\audit_and_sync.py --json-out .artifacts\skill-sync-audit.json --apply
```

**For the current session's `adaptive-retrieval-routing` skill:** Ask the user whether to promote it to pk-skills1 before syncing.

## Routing

- use `pk-qmd` MCP tools for repo-local evidence retrieval and prior skill lookup
- use `pk-qmd` first when the right prompt, note, file, or skill page is not known yet
- use `obsidian` MCP tools for vault reads and writes when available; fall back to direct file I/O if `obsidian` is down
- use `GitVizz` when repo topology or API context sharpens the reusable recipe
- use `brv` only for durable user or workflow preferences that materially affect the skill
- if `pk-qmd` and `brv` conflict, trust current source evidence

Return:
- stack/config used
- MCP tools used (or fallback note if `obsidian` was unavailable)
- files read
- files changed
- what changed
- unresolved questions
