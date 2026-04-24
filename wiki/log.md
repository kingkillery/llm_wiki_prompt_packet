# Wiki Log

## 2026-04-24T02:56:00Z - fix: llm-wiki-skills MCP lookup and CLI alias

- Fixed `SkillStore.lookup` so legacy registry rows without a `status` field are normalized instead of crashing with `KeyError`.
- Added first-class `llm_wiki_skills` CLI aliases for Python, PowerShell, and cmd in source and deployed script surfaces.
- Updated `.mcp.json` to use a repo-relative script path instead of the unresolved `${CLAUDE_PLUGIN_ROOT}` placeholder.
- Added regression coverage for legacy registry lookup and the CLI alias.

## 2026-04-23T01:05:00Z - fix: PowerShell installer invokes check wrapper with bound switch, not argv array

- Fixed the remaining PowerShell hosted-installer health-check bug.
- Root cause: `install.ps1` invoked `check_llm_wiki_memory.ps1` via `& $checkHelper @checkArgs`, so `-SkipGitvizz` was treated as a positional string and landed in `$WorkspaceRoot`.
- Updated the installer to call the wrapper directly with `& $checkHelper -SkipGitvizz` when appropriate.
- Verification: `python -m pytest tests/test_installer_flags.py -q` -> `6 passed, 1 skipped`.

## 2026-04-23T00:50:00Z - fix: PowerShell hosted installer now uses native -SkipGitvizz switch

- Fixed a PowerShell-specific argument forwarding bug in `install.ps1`.
- The hosted installer was invoking `check_llm_wiki_memory.ps1` with the GNU-style string `--skip-gitvizz`, which the PowerShell wrapper mis-bound and then forwarded as a broken runtime argument set.
- Updated the closing health-check path to pass the native wrapper switch `-SkipGitvizz` instead.
- Verification: `python -m pytest tests/test_installer_flags.py -q` -> `6 passed, 1 skipped`.

## 2026-04-23T00:35:00Z - fix: wire-repo health check now skips GitVizz by default

- Updated both `install.ps1` and `install.sh` so the final hosted-installer health check passes `--skip-gitvizz` by default for `g-kade` / `--wire-repo` installs.
- This aligns the closing health check with the repo bootstrap path, which intentionally skips GitVizz until the user explicitly enables it.
- Added regression coverage in `tests/test_installer_flags.py` for both PowerShell and shell installer variants.
- Verification: `python -m pytest tests/test_installer_flags.py -q` -> `6 passed, 1 skipped`.

## 2026-04-22T17:05:00Z - fix: shorter PowerShell temp extraction root for hosted install

- Shortened `install.ps1` temp extraction directory prefix from the long packet name to `lwpk-<id>`.
- This avoids Windows PowerShell `Expand-Archive` failures on long nested archive paths during hosted install into repos like `Autonomous-Business`.
- Added regression coverage in `tests/test_installer_flags.py` to guard the short temp-root behavior.
- Verification: `python -m pytest tests/test_installer_flags.py -q` -> `4 passed, 1 skipped`.

## 2026-04-22T16:15:00Z - docs+runtime: automatic skill-index maintenance and documentation QA

- Added automatic skill-index maintenance to the runtime: setup and health-check now refresh `.llm-wiki/skill-index.json`.
- Added lazy rebuilds in `skill_index.py` so wrapped interactive sessions rebuild the index when skills, retired skills, feedback, or config changed.
- Updated the dashboard to auto-refresh the skill index before reading skill data.
- Added regression coverage for missing-index auto-build, feedback-driven rebuilds, and runtime setup/index refresh.
- Audited and corrected core docs: `README.md`, `QUICKSTART.md`, `LLM_WIKI_MEMORY.md`, `docs/rfc-memory-taxonomy.md`, and `deploy/cloudflare/README.md`.
- Added `docs/decisions/ADR-001-automatic-skill-index-maintenance.md` and `docs/documentation-audit-2026-04-22.md`.
- Focused verification passed: `python -m pytest tests/test_skill_trigger.py tests/test_dashboard_server.py tests/test_llm_wiki_memory_runtime.py tests/test_llm_wiki_agent_failure_capture.py -q` -> `53 passed`.


## 2026-04-22T14:30:00Z - implement: negative-example filtering

- Added `SkillIndex.penalties` dict and `_penalty_multiplier()` method.
- Retired skills (in `wiki/skills/retired/`) incur +0.5 penalty.
- Negative feedback entries (in `.llm-wiki/skill-pipeline/feedback.jsonl`) incur +0.25 per -1 verdict, capped at +0.5 from feedback.
- Total penalty capped at 0.75, so minimum multiplier is 0.25 (skill never fully disappears).
- Updated `build_index()` to merge both penalty sources at index build time.
- Added 5 tests: retired skill penalty, feedback penalty, custom active-dir workspace lookup, score reduction, and cap at 0.75.
- All 16 skill-trigger tests pass.

## 2026-04-22T14:00:00Z - polish: remaining flow items

- Dashboard: added `/dashboard/api/log` endpoint (reads recent `wiki/log.md` entries), Obsidian deep-links in wiki page list, log card in frontend.
- README: documented unattended install env vars (`LLM_WIKI_VAULT`, `LLM_WIKI_TARGETS`, `LLM_WIKI_INSTALL_MODE`, `LLM_WIKI_GLOBAL_WIRE`, `BYTEROVER_API_KEY`, `HF_TOKEN`).
- Preflight: added `_get_version()` helper; now prints detected versions for all found tools (python, git, node, bun, docker, etc.).
- CI: created `.github/workflows/docker-publish.yml` for GitHub Container Registry builds on push to main and version tags.
- Benchmark: ran 10-episode stub-mode benchmark (Packet vs Baseline). Results: 100% completion rate (packet) vs 70% (baseline), 27.5% step reduction. Harness and analysis pipeline verified.
- All tracking files updated: `TODO.md`, `CHANGELOG.md`, `ROADMAP.md`.

## 2026-04-22T13:30:00Z - implement: M5 read-only memory dashboard

- Created `support/scripts/dashboard_server.py` — stdlib-only HTTP dashboard (no external dependencies).
- Serves at `http://127.0.0.1:8183/dashboard` by default.
- Endpoints:
  - `GET /dashboard` — SPA with wiki search, skill list, BRV status
  - `GET /dashboard/api/pages?q=` — keyword search across `wiki/**/*.md`
  - `GET /dashboard/api/skills` — active skills from `.llm-wiki/skill-index.json`
  - `GET /dashboard/api/skills/<id>` — skill detail
  - `GET /dashboard/api/brv/status` — proxies `brv status`
- Responsive CSS with flex/grid; zero frontend frameworks.
- Read-only: no write endpoints.
- Added `tests/test_dashboard_server.py` with 4 passing tests.
- Synced `scripts/dashboard_server.py` to deployed surface.

## 2026-04-22T13:00:00Z - implement: M4 Docker bootstrap + unattended installer

- Created `docker-compose.quickstart.yml` — minimal compose file for one-command `docker compose up`.
- Added `--unattended` flag to `install.sh`:
  - Skips `read -r -p` prompts when `LLM_WIKI_UNATTENDED=1`.
  - Falls back to `$PWD` for vault path.
- Added `-Unattended` switch to `install.ps1`:
  - Skips `Read-Host` prompts.
  - Falls back to `(Get-Location).Path`.
- Added `tests/test_installer_flags.py` with 4 tests (3 pass, 1 skipped on Windows).
- Deferred: Dockerfile.gateway (existing docker/Dockerfile suffices), CI publishing, README env var docs, preflight version checks.

## 2026-04-22T12:30:00Z - implement: M2 auto-reducer packets MVP

- Completed `scripts/auto_reducer_watcher.py` with full lifecycle: `start`, `end`, `list`, `approve`, `reject`, `show`.
- Integrated start/end markers into `llm_wiki_agent_failure_capture.py`:
  - `start` runs before agent launch (captures goal, agent, git status snapshot).
  - `end` runs after agent exit (captures returncode, diffs git status, writes draft to `auto-packets/`).
- Draft includes: task summary, files changed, outcome signal, skill candidacy heuristic.
- Added `tests/test_auto_reducer_watcher.py` with 7 passing tests.
- Synced `scripts/auto_reducer_watcher.py` to deployed surface.
- Open items deferred: mid-session crash draft (SIGINT), BRV/Ollama summarizer upgrade, optional `skill_pipeline_run` trigger on approve.

## 2026-04-22T12:00:00Z - implement: recency decay + graph traversal (QuickScope²)

- Implemented both retrieval improvements in a single pass through `skill_index.py`:
  1. **Recency decay**: `_recency_multiplier()` applies exponential decay `0.5 + 0.5 * exp(-age/halflife)` to skill scores. Fresh skills rank higher than stale ones. Configurable via `skills.index.halflife_days` (default 30).
  2. **Graph traversal**: Skills can declare `related_skills` edges in YAML frontmatter with `id` and `relation` (prerequisite, conflict, successor, etc.). `SkillIndex.neighbors()` walks edges and `format_suggestions()` emits a neighborhood block.
- Updated `.llm-wiki/config.json` with `halflife_days: 30.0`.
- Extended `discover_skills()` to parse `related_skills` and `build_index()` to populate the edge index.
- Added 3 new tests: `TestRecencyDecay`, `TestGraphTraversal.test_neighbors_returned_from_edges`, `TestGraphTraversal.test_suggest_skills_includes_neighbors`. All 11 tests pass.
- Synced `scripts/skill_index.py` and `scripts/llm_wiki_agent_failure_capture.py` with latest deployed copies.

## 2026-04-22T11:30:00Z - research: SOTA memory retrieval gaps

- Analyzed current retrieval mechanics vs. Zep, Mem0, WorldDB, Titans/MIRAS, and Agent-Native Memory literature.
- Identified two concrete gaps: (1) no temporal decay in scoring, (2) flat skill list instead of graph traversal.
- Wrote `wiki/syntheses/quickscope-memory-retrieval-improvements-2026.md` with exact file-by-file changes and 6-step execution order.
- Gap 1 (recency decay): ~30 min, touches `skill_index.py`, config, tests.
- Gap 2 (graph traversal): ~2 hrs, touches skill schema, edge index, `_graph_neighbors()`, formatter, tests.

## 2026-04-22T11:00:00Z - implement: M1 skill trigger classifier MVP

- Created `support/scripts/skill_index.py` — shared module for skill discovery, indexing, and scoring.
  - Supports three backends: `keyword` (weighted lexical overlap, dependency-free), `tei` (local HTTP embeddings), `stub` (deterministic unit vectors for tests).
  - Extracts YAML frontmatter and body sections (trigger, fast_path, failure_modes) from skill markdown.
  - `SkillIndex.score()` combines keyword and embedding scores with configurable weighting.
- Created `support/scripts/build_skill_index.py` — CLI to build `.llm-wiki/skill-index.json` from `wiki/skills/active/`.
- Created `support/scripts/skill_trigger.py` — CLI to query the index and return formatted suggestions.
- Integrated skill trigger into `llm_wiki_agent_failure_capture.py`: prints suggestions to stderr before launching interactive agents.
- Added `LLM_WIKI_SKILL_SUGGEST=0` escape hatch.
- Added `skills.index` section to `.llm-wiki/config.json`.
- Created `tests/test_skill_trigger.py` with 8 passing tests covering frontmatter extraction, keyword scoring, threshold filtering, stub embedder determinism, and CLI integration.
- Synced all new/updated Python files to `scripts/` deployed surface.
- Updated `TODO.md` to reflect completed M1 tasks.

## 2026-04-22T10:30:00Z - solidify: roadmap and todo canonical tracking

- Promoted the gap-closure plan from wiki synthesis to canonical project tracking.
- Created `ROADMAP.md` with milestones M1–M5, dates, success criteria, dependency graph, and explicit anti-goals.
- Created `TODO.md` with granular checkbox tasks mapped to each milestone, plus a backlog/icebox.
- Updated `CHANGELOG.md` Unreleased section to reference the new tracking files.
- Added cross-references between `ROADMAP.md`, `TODO.md`, `wiki/syntheses/packet-gap-closure-roadmap-2026.md`, and `wiki/comparisons/llm-wiki-vs-sota-memory-systems.md`.

## 2026-04-22T10:15:00Z - plan: packet gap closure roadmap

- Broke the four strategic gaps into five executable experiments with MVP scope, acceptance criteria, dependencies, and risk.
- Added the phased roadmap at `wiki/syntheses/packet-gap-closure-roadmap-2026.md`.
- Recommended execution order: (1) skill trigger classifier, (2) auto-reducer packets, (3) RFC + benchmark, (4) Docker/installer hardening, (5) dashboard, (6) hosted path (if justified).
- Surfaced open questions on hook architecture, suggestion injection channel, gateway capacity, and hosted-path budget.
- Updated `wiki/index.md`.

## 2026-04-22T10:00:00Z - compare: packet vs. state-of-the-art memory systems

- Reviewed the packet's memory architecture against Mem0, Zep, LangChain Memory, LlamaIndex Chat Engine, MemGPT/Letta, CrewAI, Claude native memory, and OpenAI memory.
- Identified two core differentiators: (1) first-class procedural memory with skill lifecycle, and (2) explicit write-path curation via ACE-style loops.
- Identified two major gaps: (1) lack of automatic episodic capture compared to auto-ingest competitors, and (2) no user-facing chat-native memory editing surface.
- Added a structured comparison matrix and deep-dive analysis at `wiki/comparisons/llm-wiki-vs-sota-memory-systems.md`.
- Updated `wiki/index.md` with the new comparison section.
- Recommended five strategic experiments: publish taxonomy spec, head-to-head benchmark, auto-reducer packets, skill trigger classifier, and hybrid cloud mode.

## 2026-04-21T00:30:00Z - synthesize: recent cs.AI actionable agent memory patterns

- Captured WorldDB-style write-time reconciliation, controller-driven memory use, capability-aware routing, and stable-summary reuse as packet-relevant design patterns.
- Added a second synthesis note at `wiki/syntheses/recent-csai-actionable-agent-memory-patterns-2026.md`.
- Folded the strongest concrete idea into the skill plane as lightweight `canonical_keys` for reconciliation.

## 2026-04-21T00:00:00Z - synthesize: agentic memory skill stack upgrade

- Reviewed the late-2024 to 2026 agent-memory literature supplied in-session.
- Cross-checked local patterns in `pk-skills1`, especially `memory-management`, `architect_high_autonomy_agentic_systems`, and `agent-self-improvement-harness`.
- Upgraded the packet-native skill pipeline to carry typed memory-object fields and hierarchical-memory defaults.
- Recorded the design rationale in `wiki/syntheses/agentic-memory-skill-stack-upgrade-2026.md`.

