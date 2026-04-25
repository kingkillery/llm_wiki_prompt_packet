# LLM Wiki Memory Agent Guide

Maintain this vault as a persistent markdown wiki built from immutable raw sources.

## Startup

Before substantive work:

1. Read this file.
2. Read `LLM_WIKI_MEMORY.md` if present.
3. Read `SKILL_CREATION_AT_EXPERT_LEVEL.md` if present when the task touches reusable skill authoring or review.
4. Read `.llm-wiki/config.json` if present.
5. If `pk-qmd`, `brv`, or GitVizz are missing, run the installed setup helper before deeper work:
   - PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_llm_wiki_memory.ps1`
   - Shell: `bash ./scripts/setup_llm_wiki_memory.sh`
6. Read `wiki/index.md`.
7. Read recent `wiki/log.md`.
8. Search for existing related pages.

## MCP Servers

Four MCP servers are wired via `.mcp.json` for stdio access:

| Server | Purpose | Required? |
|--------|---------|----------|
| `pk-qmd` | Source evidence, docs, prompts, notes retrieval | **Always** |
| `llm-wiki-skills` | Skill lifecycle (lookup, reflect, validate, evolve, retire) | **Always** |
| `obsidian` | Vault read/write — the scribing surface for wiki notes | **Pivotal but optional** |
| `brv` | Durable memory, preferences, workflow quirks | Optional |

### Obsidian: pivotal but optional

The `obsidian` MCP server connects to the Kade-HQ vault and provides `read_note`, `write_note`, `search_notes`, `manage_tags`, and `move_note` tools. It is the **preferred path** for all wiki scribing — creating, updating, and organizing notes.

When `obsidian` is unavailable (desktop app not running, vault not mounted, MCP connection refused):

1. Fall back to direct file I/O against the vault path.
2. Log that the fallback was used (append to `wiki/log.md`).
3. Note any link-integrity risk — Obsidian-aware moves preserve backlinks; raw file moves do not.
4. If the task is a rename or move, prefer pausing and asking the user to open Obsidian rather than risking broken links.

### BRV: skip gracefully

If `brv` has no connected provider, do not rely on `brv query` or `brv curate` for task completion.

## Script locations

- `support/scripts/` — source tree for all Python and shell scripts; read this for code review, debugging, or test authoring.
- `scripts/` — installer-deployed surface in an activated project vault; invoke scripts from here during normal vault operations.
- When KADE.md or handoff logs mention `support/scripts/`, they are referencing the source. When AGENTS.md, CLAUDE.md, or config reference `scripts/`, they mean the deployed copy.

## Tool routing

- Use `pk-qmd` for repo-specific source evidence.
- Use `pk-qmd` first when the target file, folder, prompt, or note is not yet known.
- Use `pk-qmd` first when the right existing skill page or feedback note is not yet known.
- Use `obsidian` MCP tools for all vault reads and writes when available.
- Use `brv` only for durable preferences, decisions, and workflow quirks.
- Prefer current source evidence over `brv` memory when they conflict.
- If BRV has no connected provider, do not rely on `brv query` or `brv curate` for task completion.
- Use configured `GitVizz` URLs for local graph and web access.
- Use `GitVizz` when you need repo topology, API surface, route relationships, or to hone in after `pk-qmd` found the likely area.
- Do not surface raw tool choices to end users unless asked.

## Rules

- Never edit `raw/` unless explicitly asked.
- Prefer updating existing pages over creating duplicates.
- Prefer `obsidian` MCP tools over direct file I/O for vault mutations.
- When `obsidian` is unavailable, direct file I/O is acceptable but note the fallback in `wiki/log.md`.
- Maintain links, contradictions, and open questions.
- Treat reusable skills as first-class wiki artifacts, not ad hoc notes.
- Make small, reversible edits by default.
- Ask before deletions, large renames, or restructures.

## Karpathy-Inspired Coding Guidelines

Use these rules for coding, review, refactoring, and debugging work. They bias toward caution over speed; for trivial one-line tasks, apply judgment without adding ceremony.

### Think Before Coding

- State key assumptions before changing code when they affect design, behavior, data, or compatibility.
- Do not silently choose between materially different interpretations; surface the plausible readings briefly.
- Ask for clarification when uncertainty would materially change the implementation.
- Push back on approaches that are unnecessarily complex, inconsistent with the request, or at odds with local project rules.

### Simplicity First

- Implement the minimum solution that fully solves the requested problem.
- Do not add speculative features, abstractions, configuration, error handling, or extensibility that the task does not require.
- Prefer straightforward code over cleverness.
- Simplify any solution that can be made substantially smaller or clearer without losing correctness.

### Surgical Changes

- Touch only the code and documentation necessary for the task.
- Do not refactor unrelated code, reformat broad areas, or rewrite adjacent comments unless required.
- Match existing local style, naming, structure, and helper patterns.
- Remove only the dead code, unused imports, or unused variables created by your own changes.
- Mention unrelated issues separately instead of changing them.

### Goal-Driven Execution

- Define concrete success criteria before making non-trivial changes.
- When fixing bugs, prefer reproducing the issue first, then verifying the fix.
- When adding behavior, add tests or other verifiable checks when appropriate.
- For multi-step work, make a short plan with a verification step for each stage.
- Do not stop at "implemented"; stop when the change is verified working or the remaining verification gap is clearly reported.

<!-- llm-wiki-prompt-packet:agents-guidance:start -->
## KADE-HQ, Memory, and Retrieval Routing

Use this workspace as a KADE-HQ-backed memory workspace. Treat `AGENTS.md`, `LLM_WIKI_MEMORY.md`, `.llm-wiki/config.json`, `wiki/`, and `kade/` as the operating contract for future agent work.

### Startup Routing

- Read `AGENTS.md` first, then `LLM_WIKI_MEMORY.md`, then `.llm-wiki/config.json` before substantive work.
- If this is a KADE-enabled workspace, also read `kade/AGENTS.md` and `kade/KADE.md` when present.
- Load `~/.kade/HUMAN.md` when present for user/workflow preferences, but prefer project-local instructions when they conflict.
- Run `scripts/setup_llm_wiki_memory.ps1` or `scripts/setup_llm_wiki_memory.sh` if required memory/retrieval tools are missing.

### Retrieval Order

- Use `pk-qmd` first for source-backed repo, prompt, note, and wiki evidence when the right file or concept is not already known.
- Use Obsidian MCP tools for wiki note reads, writes, moves, and tag updates when available; fall back to direct file I/O only when Obsidian is unavailable, and record that fallback in `wiki/log.md`.
- Use `llm-wiki-skills` for reusable skill lookup, reflection, validation, evolution, and retirement.
- Use BRV only for durable preferences, repeated workflow quirks, and decisions; do not rely on it when no provider is connected.
- Use GitVizz for repo topology, API surface, route relationships, and graph-oriented navigation after retrieval has identified the likely area.
- Prefer current source evidence over memory when sources and memory conflict.
- Start with `llm-wiki-packet context --task "..."` for a compact task bundle; use `llm-wiki-packet evidence --query "..."`, `llm-wiki-packet evidence --plane source --query "..."`, or `llm-wiki-packet context --mode deep` only when broader hybrid/source search is useful.
- For graph-heavy work, prefer configured `gitvizz.repo_id`; if GitVizz reports auth-required, use the configured auth env vars or treat graph results as degraded hints.
- Treat Hugging Face embedding/reranking settings as optional disabled-by-default planner hints, not required bootstrap tools.

### KADE-HQ System Use

- Treat KADE-HQ as the human/profile and workspace-orchestration layer, not as a replacement for project instructions.
- Treat `g-kade` as the bridge/router across KADE-HQ, G-Stack workflows, and this packet.
- Use G-Stack workflows for review, QA, debugging, browser dogfooding, deployment verification, and ship-readiness checks when the corresponding skill/runtime is installed.
- Keep the root packet files as the source of truth for memory/retrieval wiring; keep KADE-specific handoff state under `kade/`.

### Memory Writes

- Write durable repo knowledge to `wiki/` pages, not chat-only memory.
- Write reusable procedures as skill artifacts under the configured skill lifecycle, not ad hoc notes.
- Keep raw immutable sources under `raw/`; never edit `raw/` unless explicitly asked.
- Update `wiki/index.md` when adding or moving durable pages.
- Update `wiki/log.md` for meaningful wiki changes, tool fallbacks, setup changes, and unresolved questions.
- For long-running harness work, use `llm-wiki-packet manifest`, `context --run-id`, `evidence --run-id`, `reduce`, `evaluate`, `promote`, and `improve` so artifacts, retrieval metadata, memory promotion, and self-improvement gates share the same run id.
<!-- llm-wiki-prompt-packet:agents-guidance:end -->

## Done when

A task is complete only when relevant pages are updated, `index.md` is updated if needed, and `log.md` is updated if needed.

---

Updated by Codex:
- Added native Karpathy-inspired coding guidelines for assumption handling, simplicity, surgical edits, and verification.
- Merged overlapping guidance with the existing small, reversible edit rule; no project-specific rule was overridden.
- Skill folder install succeeded for `C:\Users\prest\.agents\skills1\pk-skills1`, `C:\Users\prest\.agents\skills`, and `C:\Users\prest\.claude\skills`.
- Added managed KADE-HQ, memory, and retrieval routing guidance for packet-installed agent workspaces.
