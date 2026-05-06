# Spec: LLM Wiki Compounding Memory Roadmap

## Status

Implemented deterministic first milestone. Semantic/LLM-backed enrichment remains optional future work under the boundaries below.

## Related

- PRD: `docs/prd-llm-wiki-compounding-memory-roadmap.md`
- Backlog: `possible-improvements.md`
- Existing Obsidian provider PRD/SPEC: `docs/prd-obsidian-canonical-wiki-provider.md`, `docs/spec-obsidian-canonical-wiki-provider.md`
- Existing save/provider scripts: `support/scripts/llm_wiki_save.py`, `support/scripts/llm_wiki_provider.py`
- Existing packet context/retrieval script: `support/scripts/llm_wiki_packet.py`
- Existing runtime setup/check script: `support/scripts/llm_wiki_memory_runtime.py`
- Existing skill/memory lifecycle script: `support/scripts/llm_wiki_skill_mcp.py`

## Assumptions

1. The packet remains agent-neutral and must continue supporting Codex, Claude Code, Antigravity, Droid/Pi-style agents, and compatible file/MCP workflows.
2. Obsidian remains the preferred human wiki layer, but core wiki operations must work with direct filesystem access to an explicitly configured vault.
3. `pk-qmd`, BRV, and GitVizz remain separate retrieval/memory/graph planes; this roadmap adds a wiki knowledge layer rather than replacing them.
4. The first implementation should favor deterministic filesystem and markdown behavior before optional LLM-heavy graph inference or UI work.
5. Generated artifacts may contain sensitive project knowledge, so automatic capture and graph output must be conservative by default.

## Objective

Turn the existing improvement backlog into a staged technical design for a compounding wiki memory system.

The implementation should add:

- living overview and saved-query pages
- conflict-aware saves and temporal entity metadata
- wiki lint/status commands
- compiler-style raw-source ingestion and incremental compile state
- progressive disclosure search and retrieval routing
- optional wiki graph, guided tours, and diff impact reports
- optional lifecycle capture into memory candidates
- provider configuration precedence and prompt-budget controls

## Tech Stack

- Language: Python for packet scripts and tests.
- Data format: Markdown with YAML frontmatter, JSON for structured state and graph artifacts.
- Test framework: `pytest`.
- Existing transports: direct file provider, `mcpvault`, `mcp-obsidian` compatibility.
- Existing retrieval integrations: local markdown scan, `pk-qmd`, BRV, GitVizz.
- Optional future UI: local loopback web viewer or static graph HTML.

## Commands

Existing verification:

```powershell
py -m pytest tests\test_llm_wiki_provider.py tests\test_llm_wiki_save.py tests\test_llm_wiki_packet.py tests\test_llm_wiki_memory_runtime.py tests\test_install_obsidian_agent_memory.py
```

Target commands to add or extend:

```powershell
python scripts\llm_wiki_save.py --workspace . --title "Title" --type synthesis --body-file .tmp\note.md
python scripts\llm_wiki_packet.py context --workspace . --task "question" --mode default --json
python scripts\llm_wiki_packet.py evidence --workspace . --query "question" --json
python scripts\llm_wiki_compile.py status --workspace . --json
python scripts\llm_wiki_compile.py compile --workspace . --changed-only --json
python scripts\llm_wiki_lint.py --workspace . --json
python scripts\llm_wiki_graph.py build --workspace . --json
python scripts\llm_wiki_graph.py tour --workspace . --topic "onboarding" --json
python scripts\llm_wiki_impact.py diff --workspace . --base HEAD~1 --json
```

The exact command set can be consolidated if implementation proves a single `llm_wiki_packet.py wiki-*` surface is cleaner.

## Project Structure

Existing areas to extend:

```text
support/scripts/       Source scripts copied into installed workspaces.
installers/            Config builder, bootstrap files, and install behavior.
tests/                 Unit and integration tests for packet behavior.
prompts/               Agent command/workflow guidance.
docs/                  PRDs, specs, architecture notes.
wiki/                  Repo-local packet knowledge base.
```

New installed workspace artifacts:

```text
wiki/overview.md                       Living workspace synthesis.
wiki/queries/                          Saved high-value query answers.
wiki/tours/                            Optional guided tours.
wiki/meta/dashboard.base               Optional Obsidian Bases dashboard.
wiki/meta/diff-impact.md               Optional latest diff impact report.
.llm-wiki/state/wiki-compile.json      Source hash and compile state.
.llm-wiki/reports/                     Generated lint/status/impact reports.
graph/graph.json                       Optional wiki graph artifact.
graph/graph.html                       Optional static wiki graph view.
raw/imports/                           Optional source drop zone.
raw/converted/                         Optional normalized markdown output.
```

## Module Design

### Wiki Save Module

Responsibilities:

- classify target note type
- find existing matching notes
- create or update structured frontmatter
- update index, log, hot cache, and overview when appropriate
- detect likely conflicts before write
- support saved query notes

Public behavior:

- `save_note(args) -> dict`
- future deep API: `save_wiki_note(workspace, payload) -> SaveResult`

Key additions:

- `conflict_policy`: `flag`, `supersede`, `ask`, `ignore`
- `note_type = "query"`
- `supersedes`, `contradicts`, `observed_at`, `valid_from`, `valid_until`

### Wiki Compiler Module

Responsibilities:

- normalize raw imported sources
- track source hashes and compile timestamps
- compile sources into concepts/entities/sources/syntheses
- enforce per-concept prompt budget
- emit structured compile results

Public behavior:

- `status(workspace) -> WikiStatus`
- `compile(workspace, changed_only=True) -> CompileResult`

State:

```json
{
  "version": 1,
  "sources": {
    "raw/imports/example.md": {
      "sha256": "...",
      "last_compiled_at": "...",
      "outputs": ["wiki/sources/example.md"]
    }
  }
}
```

### Wiki Lint Module

Responsibilities:

- validate frontmatter
- detect orphan pages
- detect broken wikilinks
- detect duplicate note titles or canonical keys
- detect unresolved contradictions
- detect stale active decisions
- detect source notes without citations or confidence
- detect entity pages without recent observations

Public behavior:

- `lint(workspace) -> LintReport`

Output:

- JSON report for tooling
- Markdown report for users

### Retrieval Router Module

Responsibilities:

- context gate before retrieval
- classify CHEAP/STANDARD/FULL retrieval tier
- dedupe results across planes
- stop on high-overlap repeated results
- cap at three hops
- expose progressive disclosure search

Public behavior:

- `route_retrieval(task, context) -> RetrievalPlan`
- `search_index(query) -> SearchIndex`
- `timeline(ids_or_query) -> TimelineContext`
- `get(ids) -> FullRecords`

Progressive disclosure:

1. compact IDs/snippets
2. chronological context around selected hits
3. full content for selected IDs only

### Wiki Graph Module

Responsibilities:

- parse wikilinks
- parse folder/category metadata
- optionally extract entities, claims, and implicit links
- label edge provenance
- cache graph by note hashes
- generate graph JSON and optional HTML
- generate guided tours from graph topology

Public behavior:

- `build_graph(workspace) -> GraphResult`
- `generate_tour(workspace, topic) -> TourResult`

Edge provenance:

- `EXTRACTED`: explicit wikilink or metadata
- `INFERRED`: LLM or heuristic relationship
- `AMBIGUOUS`: possible relationship requiring review

### Memory Capture Module

Responsibilities:

- normalize lifecycle events into candidate observations
- filter sensitive content
- create memory candidates, not approved memory
- support session-end compression
- integrate with existing memory ledger

Events:

- session start
- user prompt submit
- post tool use
- stop
- session end

Privacy filters:

- ignore `<private>...</private>`
- configurable path denylist
- generated report/data denylist
- PII-sensitive mode

### Provider Settings Module

Responsibilities:

- resolve provider, model, timeout, language, and endpoint settings
- document and test precedence

Precedence:

1. shell environment
2. local `.env`
3. agent/client settings
4. packet config
5. built-in defaults

## Config Model

Add or extend config sections:

```json
{
  "wiki_layer": {
    "overview_path": "wiki/overview.md",
    "queries_path": "wiki/queries",
    "tours_path": "wiki/tours",
    "compile_state_path": ".llm-wiki/state/wiki-compile.json",
    "reports_path": ".llm-wiki/reports",
    "graph_path": "graph/graph.json",
    "graph_html_path": "graph/graph.html",
    "conflict_policy": "flag",
    "saved_queries_enabled": true,
    "overview_update_policy": "on-substantial-save"
  },
  "wiki_compile": {
    "enabled": false,
    "changed_only_default": true,
    "prompt_budget_chars": 200000,
    "output_language": "",
    "request_timeout_ms": 600000
  },
  "retrieval_router": {
    "enabled": true,
    "max_hops": 3,
    "overlap_stop_threshold": 0.5,
    "progressive_disclosure": true
  },
  "memory_capture": {
    "enabled": false,
    "candidate_only": true,
    "private_block_pattern": "<private>...</private>",
    "pii_sensitive": false,
    "deny_paths": [],
    "deny_generated_artifacts": true
  }
}
```

## Code Style

Prefer small dataclasses or typed dictionaries at module boundaries. Keep CLI parsing thin and move behavior into testable functions.

Example style:

```python
@dataclass
class LintFinding:
    code: str
    severity: str
    path: str
    message: str
    suggestion: str = ""


def lint_workspace(workspace_root: Path) -> list[LintFinding]:
    notes = load_wiki_notes(workspace_root)
    findings: list[LintFinding] = []
    findings.extend(find_broken_links(notes))
    findings.extend(find_missing_frontmatter(notes))
    return sorted(findings, key=lambda item: (item.severity, item.path, item.code))
```

Conventions:

- Use explicit `Path` values internally.
- Return structured payloads from core functions.
- Keep markdown generation deterministic where possible.
- Use direct file I/O only against the configured vault/workspace root.
- Avoid hidden network calls in lint/status paths.

## Testing Strategy

Use `pytest`.

Test levels:

- unit tests for parsing, linting, routing, conflict detection, and graph extraction
- integration tests using temporary workspaces for save/compile/status side effects
- installer tests for generated config and bootstrap files
- regression tests for Windows TOML quoting and explicit vault path behavior

Coverage expectations:

- Core deterministic behavior should have direct tests.
- LLM-backed optional behavior should have interface/contract tests with stubs.
- CLI tests should verify JSON output shape and exit behavior.

## Boundaries

Always:

- Preserve existing packet behavior unless the spec explicitly changes it.
- Keep new features optional unless they improve core save/query correctness.
- Use explicit vault paths for Obsidian/file writes.
- Write tests for deterministic modules.
- Keep generated output structured and machine-readable where practical.
- Update docs/prompts when agent behavior changes.

Ask first:

- Adding new required runtime dependencies.
- Adding a long-running local service.
- Changing MCP server names.
- Changing existing config defaults that affect all installs.
- Making graph or lifecycle capture enabled by default.
- Adding CI requirements or Git LFS rules.

Never:

- Commit secrets, API keys, raw customer data, screenshots, or PII-heavy artifacts.
- Capture `<private>...</private>` content into memory.
- Silently use the current repo as an Obsidian vault when no vault is configured.
- Reuse incompatible-license implementation code.
- Make Obsidian Desktop mandatory.
- Replace existing `pk-qmd`, BRV, or GitVizz integrations.

## Implementation Plan

### Phase 1: Core Wiki Hygiene

- Add `wiki/overview.md` bootstrap.
- Add `wiki/queries/` bootstrap.
- Extend save workflow for query notes and overview updates.
- Add basic conflict metadata support.
- Add tests for save/update/index/log/hot/overview/query behavior.

Verification:

```powershell
py -m pytest tests\test_llm_wiki_save.py tests\test_install_obsidian_agent_memory.py
```

### Phase 2: Lint and Status

- Add wiki lint module and CLI.
- Add wiki status output.
- Add JSON and markdown report generation.
- Add tests for lint findings.

Verification:

```powershell
py -m pytest tests\test_llm_wiki_lint.py
```

### Phase 3: Retrieval Router

- Add explicit routing plan output.
- Implement context gate, tier classification, dedupe, hop cap, and overlap stop.
- Add progressive disclosure search APIs.
- Extend packet context/evidence commands.

Verification:

```powershell
py -m pytest tests\test_llm_wiki_packet.py tests\test_llm_wiki_retrieval_router.py
```

### Phase 4: Compiler Pipeline

- Add source hash state.
- Add changed-only compile status.
- Add saved query inclusion.
- Add prompt budget warnings.
- Stub LLM-backed compilation behind a testable interface.

Verification:

```powershell
py -m pytest tests\test_llm_wiki_compile.py
```

### Phase 5: Graph, Tours, and Diff Impact

- Add graph extraction from notes and index.
- Add edge provenance labels.
- Add tour generation from graph ordering.
- Add diff impact report.
- Add artifact ignore guidance.

Verification:

```powershell
py -m pytest tests\test_llm_wiki_graph.py tests\test_llm_wiki_impact.py
```

### Phase 6: Lifecycle Capture and Viewer

- Add optional lifecycle event normalization.
- Add privacy filters.
- Store candidates only.
- Add optional local viewer or extend existing dashboard.

Verification:

```powershell
py -m pytest tests\test_llm_wiki_memory_capture.py tests\test_dashboard_server.py
```

## Task Breakdown

- [x] Task: Add overview/query bootstrap paths.
  - Acceptance: New installs create `wiki/overview.md` and `wiki/queries/.gitkeep`.
  - Verify: installer tests pass.
  - Files: installer config, bootstrap constants, installer tests.

- [x] Task: Extend save workflow for query notes.
  - Acceptance: `--type query` writes to configured query folder and updates index/log/hot.
  - Verify: save tests pass with temporary vault.
  - Files: save script and save tests.

- [x] Task: Add conflict-aware save metadata.
  - Acceptance: save can write `contradicts` and `supersedes` metadata and record conflict sections.
  - Verify: save tests assert frontmatter and body output.
  - Files: save script and save tests.

- [x] Task: Add overview refresh behavior.
  - Acceptance: substantial saves can update or append a deterministic overview summary section.
  - Verify: save tests assert overview side effect.
  - Files: save script, bootstrap files, tests.

- [x] Task: Add wiki lint module.
  - Acceptance: linter reports broken links, missing frontmatter, orphans, duplicates, stale decisions, and unresolved contradictions.
  - Verify: lint tests pass.
  - Files: new lint script and tests.

- [x] Task: Add wiki status command.
  - Acceptance: status reports page counts, source counts, pending compile count, and lint summary.
  - Verify: status tests pass.
  - Files: compile/status script and tests.

- [x] Task: Add retrieval router.
  - Acceptance: router returns CHEAP/STANDARD/FULL plans and obeys gate/hop/dedupe rules.
  - Verify: router tests pass.
  - Files: packet or retrieval router script and tests.

- [x] Task: Add progressive disclosure search.
  - Acceptance: compact search, timeline, and batch get outputs are separately callable.
  - Verify: packet tests pass.
  - Files: packet/retrieval script and tests.

- [x] Task: Add compile state.
  - Acceptance: changed-only compile skips unchanged sources based on hashes.
  - Verify: compile tests pass.
  - Files: compiler script and tests.

- [x] Task: Add prompt budget enforcement.
  - Acceptance: over-budget concepts emit deterministic warnings and fair-share truncation.
  - Verify: compile tests pass.
  - Files: compiler script and tests.

- [x] Task: Add wiki graph artifacts.
  - Acceptance: graph build extracts wikilinks and writes stable graph JSON.
  - Verify: graph tests pass.
  - Files: graph script and tests.

- [x] Task: Add guided tours.
  - Acceptance: tour generation emits ordered markdown from graph or index evidence.
  - Verify: graph/tour tests pass.
  - Files: graph/tour script and tests.

- [x] Task: Add diff impact report.
  - Acceptance: diff report identifies likely stale wiki pages, decisions, entities, and skills.
  - Verify: impact tests pass.
  - Files: impact script and tests.

- [x] Task: Add lifecycle capture candidates.
  - Acceptance: events produce candidate memories and never approved memories directly.
  - Verify: memory capture tests pass.
  - Files: memory capture script and tests.

- [x] Task: Add privacy filters.
  - Acceptance: private blocks, denylisted paths, and generated artifacts are excluded from candidates.
  - Verify: memory capture tests pass.
  - Files: memory capture script/config tests.

## Success Criteria

- Fresh installs include overview/query scaffolding and config.
- Save workflow supports query pages, conflict metadata, and overview updates.
- Lint/status commands return structured diagnostics.
- Retrieval routing can explain why retrieval was skipped, cheap, standard, or full.
- Progressive disclosure search avoids fetching full notes until IDs are selected.
- Compile state tracks hashes and avoids reprocessing unchanged sources.
- Graph output is deterministic for explicit links.
- Privacy filters prevent known sensitive blocks and paths from entering memory candidates.
- All new deterministic behavior has tests.
- Existing Obsidian provider and install tests continue passing.

## Open Questions

- Should the first milestone expose new standalone scripts or consolidate under `llm_wiki_packet.py` subcommands?
- Should `wiki/overview.md` be purely deterministic or optionally LLM-refreshed?
- Should saved query pages be a first-class note type in the Obsidian taxonomy or an internal folder only?
- Should graph HTML be generated by Python only, or should a small optional frontend package be allowed?
- Should lifecycle capture integrate with Codex hooks first, Claude hooks first, or remain runtime-agnostic until the core wiki features are stable?
