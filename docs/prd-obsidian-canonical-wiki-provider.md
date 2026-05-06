# PRD: Obsidian Canonical Wiki Provider

## Status

Draft for implementation planning.

## Problem

The packet currently treats Obsidian as a preferred scribing surface and exposes `mcpvault` as a low-level MCP transport. That is useful, but it does not yet make Obsidian the canonical semantic wiki layer.

The desired product behavior is stronger: when an agent learns something durable, especially from research, investigation, source analysis, or a solved workflow, the knowledge should land in a maintained Obsidian wiki where future agents can find it, update it, cite it, and avoid rediscovery.

## Goal

Make Obsidian a first-class canonical wiki provider for the packet.

In this mode:

- the Obsidian vault is the durable wiki store
- `agent-cli-obsidian` conventions define wiki behavior
- `mcpvault` or `mcp-obsidian` provides read/write transport
- agents consistently save, query, ingest, and maintain wiki pages
- deep research is saved by default unless the user opts out
- substantial answers are offered for save instead of disappearing into chat history

## Non-Goals

- Do not replace `pk-qmd`; it remains the source evidence and retrieval plane.
- Do not replace `brv`; it remains the preference and workflow memory plane.
- Do not require Obsidian Desktop for filesystem-backed vault operation.
- Do not vendor the full `agent-cli-obsidian` repository in the first milestone.
- Do not make direct file writes impossible; they remain the fallback when Obsidian transport is unavailable.

## Users

- A user who wants an Obsidian vault to become their long-term LLM wiki.
- Agents running in Codex, Claude Code, Droid, Antigravity, or Pi-compatible environments.
- Maintainers who need a predictable config and health-check contract for Obsidian-backed wiki operations.

## Success Criteria

- A fresh install can declare `wiki_layer.provider = "obsidian"` in `.llm-wiki/config.json`.
- Health checks report whether the Obsidian wiki layer is ready.
- Agents can discover the canonical wiki paths: `.raw/`, `wiki/`, `wiki/index.md`, `wiki/log.md`, and `wiki/hot.md`.
- Packet guidance and generated prompts instruct agents to save substantial answers and default-save deep research.
- A packet-owned save workflow can create or update a structured wiki note, then update `index`, `log`, and `hot`.
- Existing pages are updated before duplicates are created.
- Transport is abstracted so the same wiki operation can use MCP, REST, or direct file fallback.
- Tests cover generated config, health checks, transport fallback selection, and save workflow side effects.

## Product Requirements

### P0: Canonical Wiki Layer Config

Add a `wiki_layer` section to `.llm-wiki/config.json`:

```json
{
  "wiki_layer": {
    "provider": "obsidian",
    "behavior_layer": "agent-cli-obsidian",
    "transport": "mcpvault",
    "alternate_transport": "mcp-obsidian",
    "vault_path": ".",
    "raw_path": ".raw",
    "wiki_path": "wiki",
    "index_path": "wiki/index.md",
    "log_path": "wiki/log.md",
    "hot_cache_path": "wiki/hot.md",
    "note_types": ["synthesis", "concept", "source", "decision", "session"],
    "research_note_types": ["source", "entity", "concept", "question", "synthesis"],
    "deep_research_save_default": true,
    "offer_save_for_substantial_answers": true
  }
}
```

Acceptance:

- Installer writes this section for new installs.
- Runtime reads defaults when the section is absent.
- Existing `obsidian` config continues to work.

### P0: Wiki Readiness Health Check

Health checks must verify:

- configured vault path exists
- `wiki/`, `.raw/`, `wiki/index.md`, `wiki/log.md`, and `wiki/hot.md` exist or can be created
- configured transport is resolvable or direct file fallback is available
- behavior layer metadata is present
- note taxonomy is present

Acceptance:

- `scripts/check_llm_wiki_memory.*` reports pass/warn/fail for wiki-layer readiness.
- Missing optional Obsidian Desktop app does not fail filesystem-backed operation.
- Missing write capability fails the wiki-layer check.

### P0: Save Workflow

Add a packet-owned save workflow that can be called by commands, agents, or future MCP tools.

Required behavior:

1. classify note type
2. choose existing page or create new page
3. write YAML frontmatter
4. write body with source links and citations
5. update `wiki/index.md`
6. prepend to `wiki/log.md`
7. refresh `wiki/hot.md`

Acceptance:

- Save workflow supports at least `synthesis`, `concept`, `source`, `decision`, and `session`.
- Research saves can write source/entity/concept/question pages plus a synthesis page.
- Existing note detection prevents obvious duplicates.
- Save result returns created/updated paths.

### P0: Agent Guidance and Commands

Agents must behave as follows:

- after substantial answers, offer to save to Obsidian/wiki
- for deep research, save unless the user opts out
- for ordinary Q&A, do not force a save
- when saving, preserve citations, caveats, open questions, and useful tags
- update existing notes before creating duplicates

Acceptance:

- Root guides, generated prompts, and command docs carry the behavior.
- A user can trigger the save flow with a command such as `/wiki-save` or `/save-to-wiki`.

### P1: Transport Abstraction

Introduce a wiki operation interface:

- `wiki_read(path)`
- `wiki_write(path, content)`
- `wiki_search(query)`
- `wiki_move(old_path, new_path)`
- `wiki_tag(path, tags)`
- `wiki_exists(path)`

Transport order:

1. configured Obsidian MCP server
2. configured Local REST API / `mcp-obsidian`
3. direct file I/O fallback

Acceptance:

- Callers use the interface instead of transport-specific code.
- Fallback usage is logged in `wiki/log.md`.
- Move/rename operations warn or pause when link integrity cannot be preserved.

### P1: Query Lifecycle

Wiki-backed query behavior:

1. read `wiki/hot.md`
2. read `wiki/index.md`
3. read relevant pages
4. synthesize answer with citations
5. offer save for substantial answer
6. default-save deep research

Acceptance:

- Query command docs encode this lifecycle.
- Save prompt is suppressed for trivial lookups.

### P1: Ingest and Autoresearch Compatibility

The packet should be compatible with `agent-cli-obsidian` conventions:

- `.raw/` is immutable source storage
- source summaries go under `wiki/sources/`
- concepts go under `wiki/concepts/`
- entities go under `wiki/entities/`
- questions go under `wiki/questions/`
- syntheses go under `wiki/syntheses/` or `wiki/questions/` depending on install convention

Acceptance:

- Config declares paths for these folders.
- Documentation explains compatibility with `agent-cli-obsidian`.
- The packet can later install or symlink behavior skills without changing the config model.

### P2: Optional Skill Import

Add an optional installer flag to install or symlink compatible behavior skills from `agent-cli-obsidian`.

Candidate skills:

- `wiki`
- `wiki-query`
- `wiki-ingest`
- `wiki-lint`
- `save`
- `autoresearch`
- `obsidian-markdown`
- `obsidian-bases`

Acceptance:

- Opt-in only.
- Does not overwrite packet-owned skills without explicit force.
- Works when `agent-cli-obsidian` checkout path is supplied.

## User Experience

### Fresh Install

After install, the user sees that Obsidian is the canonical wiki provider if enabled:

```text
Wiki layer: Obsidian
Behavior: agent-cli-obsidian conventions
Transport: mcpvault
Vault: C:\path\to\vault
Status: ready
```

### Research Paper Flow

1. User asks about a paper.
2. Agent answers with citations.
3. Agent says: "This is worth keeping. I can save it as a source-backed Obsidian wiki note."
4. If accepted, the agent creates or updates:
   - `wiki/sources/{paper-title}.md`
   - `wiki/concepts/{concept}.md` as needed
   - `wiki/questions/{question-title}.md`
   - `wiki/log.md`
   - `wiki/hot.md`

### Deep Research Flow

1. User asks for deep research.
2. Agent collects and synthesizes evidence.
3. Agent writes the wiki pages by default unless the user opts out.
4. Chat response summarizes what was filed and where.

## Risks

- Obsidian MCP capabilities may differ between transports.
- Direct file fallback can break backlinks during moves.
- Over-saving can clutter the wiki if substantial/trivial distinction is weak.
- Imported behavior skills may drift upstream.
- Note taxonomy may conflict with existing vault conventions.

## Open Questions

- Should `wiki/syntheses/` be added as a standard folder, or should synthesis pages live in `wiki/questions/` for compatibility with `agent-cli-obsidian`?
- Should Local REST API support be first-class in P0 or P1?
- Should `/save` be packet-owned, or should the packet expose `/wiki-save` to avoid command conflicts?
- Should Obsidian Desktop presence be a warning or an optional capability badge?
- Should the packet ever auto-install `agent-cli-obsidian`, or only reference/import a user-provided checkout?

## Milestones

### M1: Canonical Provider Contract

- Add `wiki_layer` config.
- Add runtime defaults.
- Add docs and generated prompt guidance.
- Add health-check readiness surface.

### M2: Save Workflow

- Add save workflow implementation.
- Add command wrapper.
- Add tests for create/update/index/log/hot behavior.

### M3: Transport Abstraction

- Introduce wiki operation interface.
- Implement direct file fallback first.
- Wire MCP transport where available.

### M4: Query and Research Lifecycle

- Update query command flow.
- Add deep-research default-save behavior.
- Add research note taxonomy path support.

### M5: Optional Behavior Skill Import

- Add opt-in installer flag.
- Support user-provided `agent-cli-obsidian` checkout.
- Add non-overwrite safety tests.
