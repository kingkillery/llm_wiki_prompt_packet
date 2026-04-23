# TODO

> **Source of truth:** This file tracks granular, assignable tasks. Milestone context lives in `ROADMAP.md`.
> **Last updated:** 2026-04-22

---

## M1: Skill Trigger Classifier
**Goal:** Proactively suggest skills at session start. **Target: 2026-05-01**

### Infrastructure
- [x] Decide embedding backend for skill index (TEI local, BRV, or `pk-qmd` vec mode). **Decision:** Pluggable backends — `tei`, `keyword` (default, dependency-free), `stub` (testing).
- [x] Write `scripts/build_skill_index.py`:
  - [x] Read all `wiki/skills/active/*.md`.
  - [x] Extract `title`, `goal`, `trigger`, `fast_path` frontmatter or heuristics.
  - [x] Compute embeddings and write `.llm-wiki/skill-index.json`.
  - [ ] Watch filesystem and auto-rebuild on skill changes (optional for MVP).
- [x] Add `skill_index` entry to `.llm-wiki/config.json` with path, backend, and threshold.

### Classification
- [x] Write `scripts/skill_trigger.py`:
  - [x] Accept `--task "user first message"`.
  - [x] Embed task text using same backend as index.
  - [x] Compute cosine similarity against skill index.
  - [x] Return top-N matches with scores and skill IDs as JSON.
- [x] Define threshold policy:
  - [x] Default threshold: `0.3` for keyword, `0.82` for embedding (tunable in config).
  - [x] If top match > threshold, emit suggestion.
  - [ ] If multiple skills in same family, suggest the highest-scored and mention alternates.

### Integration
- [x] Wire `skill_trigger.py` into session startup path:
  - [x] `llm_wiki_agent_failure_capture.py` calls `suggest_skills()` before launching agent.
  - [x] Suggestion format: compact one-liner with skill ID, score, and fast-path hint.
- [x] Add env var `LLM_WIKI_SKILL_SUGGEST=0` to disable.
- [x] Log suggestion events to `.llm-wiki/skill-pipeline/suggestions.jsonl`.

### Validation & Feedback
- [x] Reinforcement hook:
  - [x] If agent uses suggested skill and succeeds, record positive signal.
  - [x] If agent ignores suggestion and later hits a known failure mode, record negative signal.
- [x] Write `tests/test_skill_trigger.py`:
  - [x] Unit tests for similarity computation.
  - [x] Mock skill index and assert correct top-N.
  - [x] Threshold boundary tests (just above / just below).
  - [x] Recency decay test (newer skill outranks stale skill).
  - [x] Graph traversal test (neighbors returned from edges).

---

## M2: Auto-Reducer Packets
**Goal:** Draft episodic summaries automatically. **Target: 2026-05-15**

### Session Boundary Detection
- [x] Choose architecture. **Decision:** Wrapper-based start/end markers via `llm_wiki_agent_failure_capture.py`.
- [x] Implement boundary detector in `scripts/auto_reducer_watcher.py`:
  - [x] Detect start (wrapper invocation, first tool call).
  - [x] Detect end (wrapper exit, idle timeout, explicit `/done` or `/remember`).
  - [ ] Handle mid-session crashes (write partial draft on SIGINT).

### Summarization
- [x] Fallback-offline: rule-based heuristic (count files changed, tools used, error strings).
- [ ] Cheap summarizer integration:
  - [ ] Default: BRV query path with `google/gemini-3.1-flash-lite-preview`.
  - [ ] Fallback: local Ollama with a small model (`phi4` or `gemma2:2b`).
- [x] Prompt template for reducer generation:
  - [x] Input: session transcript (tool calls, file edits, user messages, errors).
  - [x] Output: task summary, files touched, outcome signal, skill candidacy (`none`/`ui`/`api`/`workflow`/`debug`).

### Staging & Review
- [x] Draft writer:
  - [x] Write to `.llm-wiki/skill-pipeline/auto-packets/YYYY-MM-DD_HHMMSS_<id>.md`.
  - [x] Include metadata: session ID, agent name, start time, end time, tool call count.
- [x] Review workflow:
  - [x] CLI: `list` lists pending drafts.
  - [x] CLI: `approve <id>`, `reject <id>`, `show <id>`.
  - [x] On approve: move to `.llm-wiki/skill-pipeline/packets/`.
  - [ ] On approve: optionally trigger `skill_pipeline_run`.
  - [x] On reject: move to `.llm-wiki/skill-pipeline/auto-packets/rejected/`.

### Tests
- [x] `tests/test_auto_reducer_watcher.py`:
  - [x] Start creates marker.
  - [x] End creates draft with success/failure.
  - [x] Approve moves to packets.
  - [x] Reject moves to rejected.
  - [x] Show displays draft.
  - [x] List shows pending.

---

## M3: Taxonomy RFC + Benchmark
**Goal:** Publish spec and prove superiority on repeated tasks. **Target: 2026-05-30**

### RFC
- [x] Draft `docs/rfc-memory-taxonomy.md`:
  - [x] Formal definitions of five layers (working, episodic, semantic, procedural, preference).
  - [x] Promotion state machine with diagrams.
  - [x] MCP bindings per layer.
  - [x] Comparison table: MemGPT paging vs. WorldDB ontology vs. packet taxonomy.
  - [x] Backwards compatibility notes.
- [ ] Review cycle:
  - [ ] Internal review (self + g-kade skill review).
  - [ ] Publish to GitHub Discussions.
  - [ ] Collect feedback for 7 days.

### Benchmark Harness
- [x] Define conditions:
  - [x] Condition A: packet agent (full stack: skills, auto-reducer, classifier).
  - [x] Condition B: baseline (no memory, raw context only).
  - [x] Condition C: Mem0 agent — defer (needs Mem0 integration).
- [x] Task selection: `git-workflow` (stub mode for harness validation).
- [x] Metrics:
  - [x] Task completion rate (%).
  - [x] Steps to completion (mean, median, stddev).
  - [x] Steps to completion on repetition 2 and 3 (learning curve).
- [x] Run: 10 episodes per condition in stub mode.
- [x] Analysis: harness produces report with step reduction %.
- [ ] Full 20-episode run with real agent — defer (needs task environment wiring).

---

## M4: Docker + Unattended Installer
**Goal:** <5 min to working stack. **Target: 2026-06-15**

### Docker
- [x] Write `docker-compose.quickstart.yml`:
  - [x] Single service with core components.
  - [x] Volume mount for workspace markdown.
  - [x] Environment variable defaults.
  - [x] TEI profile optional.
- [ ] Write `Dockerfile.gateway` (defer: existing `docker/Dockerfile` covers core needs).
- [ ] Test one-liner with published image (defer: needs CI + registry).
- [ ] CI: GitHub Action to build and push image on release tag (defer).

### Unattended Installer
- [x] Add `--unattended` / `-Unattended` flag to `install.sh` and `install.ps1`:
  - [x] Skip all interactive prompts.
  - [x] Use environment variables or defaults for every choice.
  - [x] Exit non-zero on any failure (no warn-and-continue).
- [ ] Document required env vars in `README.md` (defer to docs pass).

### Preflight Hardening
- [ ] Detect existing installations and skip:
  - [ ] Node version check (skip nvm install if compatible).
  - [ ] bun check (skip install if present).
  - [ ] Docker check (suggest Docker path if available).
- [ ] Platform-specific package manager selection:
  - [ ] Windows: `winget` or `choco` if available, else fallback.
  - [ ] macOS: `brew` if available.
  - [ ] Linux: `apt`, `dnf`, or `pacman` detection.

---

## M5: Read-Only Memory Dashboard
**Goal:** Browser window into wiki, skills, BRV. **Target: 2026-06-30**

### Backend
- [x] Add lightweight HTTP server in `support/scripts/dashboard_server.py`:
  - [x] Run as separate lightweight process (`python scripts/dashboard_server.py`).
  - [x] Routes:
    - [x] `GET /dashboard` -> SPA index.
    - [x] `GET /dashboard/api/pages?q=` -> search wiki pages.
    - [x] `GET /dashboard/api/skills` -> list active skills from registry.
    - [x] `GET /dashboard/api/skills/<id>` -> skill detail.
    - [x] `GET /dashboard/api/brv/status` -> BRV provider status.
    - [ ] `GET /dashboard/api/log` -> recent `wiki/log.md` entries (defer).

### Frontend
- [x] Single-page HTML + vanilla JS (no build step):
  - [x] Search bar for wiki pages.
  - [x] Skill list with score and feedback count.
  - [x] BRV status indicator (connected / disconnected).
  - [x] Mobile-responsive CSS (flex/grid, no framework).
- [ ] Obsidian deep-link (defer).

### Safety
- [x] Explicitly NO write endpoints in MVP.
- [x] CORS restricted to localhost.
- [x] Tests: `tests/test_dashboard_server.py` (4 pass).

---

## Backlog / Icebox

These are not assigned to milestones. Promote when capacity opens.

- [ ] **Hosted path (M6):** Cloud convenience layer. Gated on organic demand.
- [x] **Negative-example filtering:** Downrank retired / negatively-reviewed skills in classifier scoring. Implemented via `penalties` in `SkillIndex`.
- [ ] **Auto-embed wiki pages:** On save, auto-chunk and embed wiki pages into qmd `vec` mode. Currently manual.
- [ ] **Multi-vault sync:** Support multiple vaults in one gateway instance.
- [ ] **Skill graph visualization:** Render skill dependencies and trigger relationships in GitVizz or dashboard.

---

## Done

_Move items here when complete and verified._

- [x] Identify gaps vs. SOTA memory systems (`wiki/comparisons/llm-wiki-vs-sota-memory-systems.md`).
- [x] Draft gap closure roadmap (`wiki/syntheses/packet-gap-closure-roadmap-2026.md`).
- [x] Create canonical `ROADMAP.md` and `TODO.md`.
