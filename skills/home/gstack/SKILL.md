---
name: gstack
description: Use when the user wants gstack-style execution workflows such as QA, browser dogfooding, code review, debugging, ship or PR preparation, design review, benchmark checks, or deployment verification. This packet-owned wrapper is installable into ~/.agents/skills, ~/.codex/skills, and ~/.claude/skills.
---

# gstack

This is the packet-owned home-skill wrapper for `gstack`.

## Startup

1. Read repo-local instructions first.
2. If you are inside an llm-wiki-memory workspace, read `AGENTS.md`, `LLM_WIKI_MEMORY.md`, and `.llm-wiki/config.json` before acting.
3. Detect whether a richer external `gstack` bundle is installed.

A richer bundle is any `gstack` folder that contains runtime or subskill content beyond this wrapper, for example `bin/`, `browse/`, `qa/`, `review/`, or multiple sibling skill folders.

Check these locations in order:

- `~/.codex/skills/gstack`
- `~/.claude/skills/gstack`
- `~/.agents/skills/gstack`
- repo-local `.codex/skills/gstack`
- repo-local `.claude/skills/gstack`
- repo-local `.agents/skills/gstack`

If you find a richer bundle, read the relevant upstream `SKILL.md` there and use it.

If you do not find one, continue with this wrapper and execute the workflow directly with native tools and subagents.

## Workflow Routing

- QA, site testing, browser dogfooding: reproduce the flow, capture evidence, then fix or report.
- Code review: findings first, severity ordered, with file references and missing-test risks.
- Investigation: reproduce, isolate root cause, patch minimally, verify the fix.
- Ship or PR prep: run the relevant checks, summarize risk, and only push or open a PR when asked.
- Design or DX review: inspect the real surface, not just source code.

## Lightweight control policy

Keep the harness simple:

1. decide whether this step needs retrieval, memory, tools, or only reasoning
2. read only the smallest useful context slice
3. act
4. save only durable facts, not the whole transcript

Prefer explicit read/write/update choices over dragging full history into every turn.

## Capability-aware routing

- Use the smallest sufficient workflow or model for narrow subtasks.
- Use stronger review/verification passes for high-risk actions, merges, or releases.
- In multi-step work, keep intermediate summaries short and reuse them instead of re-reading the same large context.

## Packet Integration

- Prefer packet helpers before guessing:
  - `scripts/setup_llm_wiki_memory.ps1`
  - `scripts/setup_llm_wiki_memory.sh`
  - `scripts/check_llm_wiki_memory.ps1`
  - `scripts/check_llm_wiki_memory.sh`
- Prefer packet retrieval and memory surfaces when they are available:
  - `pk-qmd`
  - `llm-wiki-skills`
  - `brv`
  - `GitVizz`

## Constraints

- Abstract and simplify. Do not turn the wrapper into a giant harness treatise.
- Do not assume external `gstack` binaries exist. Verify before invoking them.
- If a missing external runtime blocks a richer workflow, name the missing path or tool explicitly and fall back when possible.
- Keep the response concrete: workflow used, evidence gathered, files changed, next action.
