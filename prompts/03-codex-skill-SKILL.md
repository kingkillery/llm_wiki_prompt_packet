---
name: llm-wiki-organizer
description: Use this skill when the repo is an llm-wiki-memory vault and the task is to ingest a source, answer from the persistent wiki, create or review reusable skills, use pk-qmd for repo-local evidence retrieval, consult brv for durable memory, or lint and maintain the wiki.
---

# LLM Wiki Memory Organizer

This skill helps maintain a persistent markdown wiki backed by an explicit retrieval and memory stack.

## Startup

1. Read `AGENTS.md`.
2. Read `LLM_WIKI_MEMORY.md` if present.
3. Read `SKILL_CREATION_AT_EXPERT_LEVEL.md` if present when the task touches skill creation, feedback, or retirement.
4. Read `.llm-wiki/config.json` if present.
5. If `pk-qmd`, `brv`, or GitVizz are not ready, run `scripts/setup_llm_wiki_memory.ps1` or `scripts/setup_llm_wiki_memory.sh` before substantive work.
6. Read `wiki/index.md`.
7. Read recent `wiki/log.md`.
8. Search for existing pages before creating new ones.

## Routing

- `pk-qmd` is the default evidence lookup tool for repo-specific work.
- Use `pk-qmd` first for difficult searches when the target repo area is not known yet.
- Use `pk-qmd` first for prior skill lookup when the right skill page is not yet known.
- `brv` is for durable preferences, prior decisions, and costly rediscoveries.
- If BRV has no connected provider, do not block on BRV query/curate.
- `GitVizz` is the local graph and web surface.
- Use `GitVizz` to inspect repo topology, API routes, dependency context, and to narrow in once `pk-qmd` has located the relevant area.
- Source evidence beats memory for current factual claims.

## Skill lifecycle

- Treat reusable skills as first-class wiki assets.
- Store active skills under `wiki/skills/active/`.
- Store reasoned reviews under `wiki/skills/feedback/`.
- Store retired skills under `wiki/skills/retired/`.
- Store internal reflection briefs, reducer packets, delta snapshots, and validation reports under `.llm-wiki/skill-pipeline/`.
- Update `wiki/skills/index.md` whenever a skill is added, amended, merged, or retired.
- For long tasks, create a typed reducer packet before proposing the skill. Preserve the important context, not just the final answer.
- Run the privacy gate before saving a skill. Do not store private user data.
- Prefer skills that compress future execution into a short reusable recipe, not long summaries.
- Prefer reflect -> validate -> curate over direct save when the task involved meaningful exploration.
- Merge into an existing skill when overlap is high instead of creating a near-duplicate.
- When negative feedback implies the score should fall below `-3`, retire the skill instead of silently patching history.

## Response shape

- Task type
- Stack/config used
- Files read
- Files changed
- What changed
- Unresolved questions or conflicts
- Next best actions
