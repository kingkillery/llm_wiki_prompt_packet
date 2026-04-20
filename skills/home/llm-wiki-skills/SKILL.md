---
name: llm-wiki-skills
description: Use when the task should consult, capture, validate, evolve, or retire reusable workflow shortcuts through the local `llm-wiki-skills` MCP server. This packet-owned wrapper explains the full tool lifecycle in depth and is installable into ~/.agents/skills, ~/.codex/skills, and ~/.claude/skills.
---

# llm-wiki-skills

This is the packet-owned home-skill wrapper for `llm-wiki-skills`.

Use it when the job is not just "answer this once", but "make this reusable, reviewable, and cheaper next time."

## Startup

1. Read repo-local instructions first.
2. If you are inside an llm-wiki-memory workspace, read `AGENTS.md`, `LLM_WIKI_MEMORY.md`, and `.llm-wiki/config.json` before acting.
3. Verify that the local skill lifecycle plane exists:
- `scripts/llm_wiki_skill_mcp.py`
- `.llm-wiki/skills-registry.json`
- `.llm-wiki/skill-pipeline/`
4. If present, prefer the local MCP workflow over inventing an ad hoc skills registry.

## What This Surface Is For

`llm-wiki-skills` is the reusable skill lifecycle plane for the packet.

It is for:

- looking up prior reusable shortcuts before rediscovering them
- capturing reducer packets after meaningful exploration
- validating whether a candidate is safe, distinct, and promotion-worthy
- proposing merges or new active skills
- collecting feedback on whether a saved shortcut actually helped
- evolving skills through repeated review and frontier selection
- retiring stale or harmful skills cleanly

It is not for:

- storing secrets, tokens, API keys, or personal private data
- dumping raw transcripts without a reducer packet
- replacing source-evidence retrieval when `pk-qmd` is the right first move
- creating duplicates when an existing skill should be merged or amended

## Recommended Run Order

1. Start with `skill_lookup` before rediscovering a workflow.
2. If the task required real exploration or produced a repeatable shortcut, capture it with `skill_reflect` or `skill_pipeline_run`.
3. Use `skill_validate` when you need an explicit privacy, overlap, and promotion check.
4. Use `skill_propose`, `skill_feedback`, `skill_evolve`, and `skill_frontier` to improve the library over time.
5. Use `skill_get` when you need the full record or lineage of an existing entry.
6. Use `skill_retire` when a skill is stale, unsafe, superseded, or actively misleading.

## Tool Guide

### `skill_lookup`

Use this first when you suspect the library may already contain a shortcut.

Use it to:

- search for an existing skill by trigger, task shape, or domain
- avoid duplicated work before starting broad exploration
- decide whether to reuse, amend, or supersede an existing entry

Good default behavior:

- run `skill_lookup` before a long or repetitive operational task
- prefer reusing an existing high-confidence shortcut if it matches the current preconditions
- if the hit is partial, use it as the seed for reflection instead of inventing a brand-new skill from scratch

### `skill_reflect`

Use this after meaningful work when you want to capture the reusable lesson without promoting it blindly.

Use it to record:

- the repeated trigger
- the shortest reliable fast path
- preconditions
- failure modes
- artifact references
- a reducer packet for long tasks

This is the right tool when:

- the task took real exploration cost
- you found a stable shortcut
- you want a packet and review trail before deciding whether it belongs in the active library

For long tasks, do not save only a summary. Save a reducer packet plus artifact refs so future agents can escalate into the underlying evidence when needed.

### `skill_validate`

Use this when the candidate exists but should not be promoted on trust alone.

Validation should answer:

- does this contain secrets or sensitive data
- does this duplicate an existing skill
- are the trigger and fast path concrete enough
- are the preconditions and failure modes explicit
- should this merge into an existing record instead of creating a new one

Use it whenever:

- the candidate may overlap with an existing skill
- the material came from a long or messy session
- privacy or evidence boundaries are not obvious
- you want a formal gate before proposal or promotion

### `skill_pipeline_run`

Use this when you want the full packet-native pipeline in one pass.

This is the best default when the task produced a real reusable shortcut and you want:

- reflection
- validation
- proposal or merge output
- durable artifact placement under `.llm-wiki/skill-pipeline/`

Prefer `skill_pipeline_run` over a manual sequence when:

- you want the standard packet workflow
- the task already justified a reusable skill candidate
- you want fewer chances to skip a validation step

### `skill_propose`

Use this when you want an explicit candidate proposal or merge proposal, not just a reflection record.

Typical use:

- propose a new active skill candidate
- propose a delta against an existing skill
- prepare a candidate for review after validation

Use it when the important question is:

- "should this become an active reusable shortcut"

instead of:

- "what did we learn from the session"

### `skill_feedback`

Use this after a saved skill has been applied in the real world.

Feedback should capture whether the skill:

- actually saved time
- failed under a new edge case
- needs tighter preconditions
- should be merged, narrowed, or retired

Use feedback to improve the library instead of silently bypassing a bad or stale skill.

### `skill_evolve`

Use this when accumulated proposals, feedback, and review history justify a better version of the skill.

This is for deliberate improvement, not casual editing.

Typical evolution inputs include:

- repeated positive or negative feedback
- surrogate review artifacts
- validator findings
- frontier comparisons

Use it when you want the library to improve based on evidence instead of ad hoc rewrites.

### `skill_frontier`

Use this when you need the best current evolved candidates, not just the most recent raw proposals.

This is useful for:

- deciding which version should be treated as the current best shortcut
- checking whether an evolved candidate outperforms the active record
- surfacing the best-known entry after multiple iterations

### `skill_get`

Use this when you need the full stored record for a specific skill or candidate.

Use it to inspect:

- current content
- lineage
- proposal history
- validation trail
- associated packets or artifacts

This is the "show me the exact record" tool.

### `skill_retire`

Use this when a skill should stop being recommended.

Retire a skill when it is:

- stale because the environment changed
- misleading because the trigger is too broad
- superseded by a better frontier candidate
- unsafe because it encouraged private or brittle behavior

Retirement is preferable to leaving a known-bad shortcut active.

## Quality Bar

A solid reusable skill should include:

- a clear repeated trigger
- a compact, reliable fast path
- explicit preconditions
- explicit failure modes
- artifact references when the task had depth
- enough specificity that another agent can execute it without guesswork

If the shortcut still depends on hidden context in your head, it is not ready.

## Packet Integration

- `LLM_WIKI_MEMORY.md` describes the stack-level routing policy.
- `SKILL_CREATION_AT_EXPERT_LEVEL.md` is the implementation guide for high-quality skill capture.
- `.llm-wiki/skills-registry.json` is the canonical local registry state.
- `.llm-wiki/skill-pipeline/` stores briefs, packets, validations, proposals, surrogate reviews, evolution runs, frontier data, and failure artifacts.

## Constraints

- Do not store secrets, credentials, or private personal data.
- Do not promote vague summaries as reusable skills.
- Do not create a duplicate when a merge or delta is the correct move.
- Prefer reducer packets plus artifact refs for long tasks.
- Prefer `pk-qmd` for source evidence and `llm-wiki-skills` for reusable shortcut lifecycle; do not confuse the two roles.
