# Packet Gap Closure Roadmap (2026)

> **Goal:** Turn the four strategic gaps identified in `wiki/comparisons/llm-wiki-vs-sota-memory-systems.md` into a prioritized, phased execution plan. Each experiment includes MVP scope, acceptance criteria, dependencies, and risk.
> **Date:** 2026-04-22

---

## Gap summary

| # | Gap | SOTA competitors | Packet cost | Packet opportunity |
|---|---|---|---|---|
| 1 | **Automatic episodic capture** | Mem0, Zep, Claude auto-ingest turns | Agent must explicitly emit reducer packets | Higher signal, but higher friction |
| 2 | **Skill trigger classifier** | None do this well; closest is Copilot-style IntelliSense | Agent must search skill index manually | Could become the packet's "killer feature" |
| 3 | **User-facing memory surface** | Claude memory UI, Mem0 dashboard, Zep portal | Purely agent-facing markdown | Limits non-technical adoption |
| 4 | **Setup complexity** | `pip install mem0ai` | Multi-tool MCP + vault + harness wiring | Local-first power vs. onboarding friction |
| 5 | **Taxonomy visibility + validation** | Academic papers, vendor blogs | No published spec or benchmark | Missed thought leadership + proof points |

---

## Experiment 1: Auto-Reducer Packets (Episodic Capture)

**Problem:** The packet requires the agent harness to explicitly call `skill_reflect` or write reducer packets. In practice, agents forget to do this, especially on long tasks where the final turn is just a user "thanks."

**Hypothesis:** A background summarizer can watch session transcripts (tool calls, file edits, user messages) and emit *draft* reducer packets into `.llm-wiki/skill-pipeline/auto-packets/`. The draft sits in a staging area until validated. This preserves curation discipline while removing the "remember to write" burden.

**MVP scope:**
1. A small Python watcher (`scripts/auto_reducer_watcher.py`) that reads the last N lines of a session log or taps the agent's tool-use stream.
2. Uses a cheap summarizer model (BRV query path or local Ollama) to generate:
   - What was attempted
   - Key files touched
   - Failure or success signal
   - One-line skill candidacy verdict (`none`, `ui`, `api`, `workflow`, `debug`)
3. Writes a draft packet to `.llm-wiki/skill-pipeline/auto-packets/YYYY-MM-DD_HHMMSS_<session-id>.md`.
4. A validation gate: the *next* session start (or an explicit command) prompts the user/agent to review, edit, or discard the draft.

**Acceptance criteria:**
- [ ] 80% of sessions longer than 10 tool calls produce a draft packet within 30 seconds of session end.
- [ ] Draft packets contain at least: task summary, files changed, outcome signal, skill candidacy.
- [ ] User can approve, edit, or reject a draft in ≤3 interactions.
- [ ] Rejected drafts are moved to `.llm-wiki/skill-pipeline/auto-packets/rejected/` for audit.

**Dependencies:**
- Session boundary detection (when does a "task" end?). For Pi/Codex/Claude, this may require a hook or wrapper script.
- BRV or local LLM for cheap summarization.

**Estimated effort:** Medium (3-5 days).

**Risk:** Without good session boundaries, the watcher will generate noise. Mitigation: start with explicit session markers (e.g., the `run_llm_wiki_agent` wrappers already capture start/end).

---

## Experiment 2: Skill Trigger Classifier (Ambient Procedural Memory)

**Problem:** The agent must actively `skill_lookup` or `pk-qmd` search to discover a skill. If the agent does not know a skill exists, it rediscovers the workflow from scratch.

**Hypothesis:** A lightweight classifier can compare the user's current task against the skill index (`wiki/skills/index.md` + embeddings of skill titles/goals) and proactively suggest the top-1 or top-3 matching skills at session start or before the first tool call.

**MVP scope:**
1. Pre-compute embeddings for all active skills (title + goal + trigger + fast-path).
2. On session start, embed the user's first message.
3. Compute cosine similarity against the skill embedding index.
4. If top match > threshold (start at 0.82), inject a short suggestion into the prompt context or emit a system note:
   > "Skill match: `skill-google-flights-airport-row-click` (score 0.91). Fast path: click the exact airport row, do not press Enter."
5. If the agent uses the skill and succeeds, reinforce. If it ignores the skill and later hits the known failure, capture that as negative feedback.

**Acceptance criteria:**
- [ ] Top-1 skill suggestion is relevant (human judgment) in ≥70% of repeated task shapes.
- [ ] False-positive rate (suggesting a skill for an unrelated task) ≤15%.
- [ ] Suggestion latency ≤500ms on local hardware.
- [ ] Works with or without BRV connected (falls back to local TEI or keyword matching).

**Dependencies:**
- TEI or another local embedder running (or `pk-qmd` vec mode).
- Skill index in a machine-readable format (already exists: `.llm-wiki/skills-registry.json`).

**Estimated effort:** Small-Medium (2-4 days).

**Risk:** Over-suggestion creates prompt noise. Mitigation: make the injection compact (one line + link), and allow the user to disable with `LLM_WIKI_SKILL_SUGGEST=0`.

---

## Experiment 3: User-Facing Memory Surface

**Problem:** The packet has no chat-native UI for viewing or editing memory. Non-technical users cannot browse skills, correct `brv` preferences, or retire outdated facts without asking the agent.

**Hypothesis:** A lightweight web dashboard—served by the existing local gateway (`127.0.0.1:8181`)—can expose the wiki, skill registry, and BRV status in read-only mode first, then add edit capabilities.

**MVP scope:**
1. A new FastAPI/Flask route group under `/dashboard` on the local gateway.
2. Three views:
   - **Memory browser:** list wiki pages, skills, and recent log entries with search.
   - **Skill inspector:** show active skills with their score, feedback count, and retirement status.
   - **BRV status:** show connected provider, recent queries, and pending curations (if API allows).
3. Read-only for MVP. Edit capabilities (approve auto-packets, retire skills, edit BRV entries) in v2.
4. Obsidian-aware: if Obsidian is running, deep-link to the vault file instead of duplicating the editor.

**Acceptance criteria:**
- [ ] Dashboard loads in <2 seconds on localhost.
- [ ] Search across wiki pages returns results in <1 second.
- [ ] Mobile-readable (simple responsive CSS).
- [ ] No write capabilities in MVP (prevents accidental damage).

**Dependencies:**
- Local gateway Docker container or Python script.
- Optional: `gitvizz` frontend could host this instead of a separate app (evaluate reuse).

**Estimated effort:** Medium (4-6 days).

**Risk:** Scope creep into a full Obsidian replacement. Mitigation: explicitly out-of-scope for MVP: editing, backlinks graph, plugins, themes.

---

## Experiment 4: Setup Complexity Reduction

**Problem:** Installing the packet requires running a shell script, answering prompts, installing Node/bun deps, configuring MCP, and possibly wiring global Claude settings. Competitors are one `pip install` away.

**Hypothesis:** Three parallel tracks can reduce friction without losing local-first integrity:

**Track A: One-command Docker bootstrap**
```bash
docker run --rm -it -v $(pwd):/workspace -p 8181:8181 kingkillery/llm-wiki-packet:latest --init
```
This spins up qmd, GitVizz, TEI, and the local gateway. The user only needs Docker.

**Track B: Hosted quick-start (opt-in cloud)**
A stripped-down "cloud vault" that auto-wires BRV and provides a web UI. Target: users who want Mem0-like simplicity with packet governance. Revenue model: BRV provider markup or team seats.

**Track C: Installer hardening**
- Detect existing tool versions and skip redundant installs.
- Provide a `--unattended` flag for CI/devcontainer use.
- Auto-detect Windows vs. macOS vs. Linux and choose the right package manager.

**Acceptance criteria:**
- [ ] Docker path: new user has a working stack in ≤5 minutes.
- [ ] Unattended installer: returns 0 and produces a valid `.llm-wiki/config.json` without human input.
- [ ] Hosted path (if pursued): user can create a vault and add a first skill in ≤3 minutes from a browser.

**Dependencies:**
- DockerHub or GHCR publishing pipeline.
- Potential backend service for hosted path (separate project).

**Estimated effort:**
- Track A: Small (2-3 days).
- Track B: Large (2-4 weeks); treat as spin-off, not core.
- Track C: Small (1-2 days).

**Risk:** Hosted path contradicts local-first ethos if not carefully scoped. Mitigation: hosted path is explicitly a convenience wrapper; data should remain exportable as markdown.

---

## Experiment 5: Taxonomy RFC + Head-to-Head Benchmark

**Problem:** The packet's architectural contributions (five-layer memory, typed skills, multi-plane retrieval) are invisible to the broader community. There is no published spec or empirical proof that the packet outperforms simpler systems.

**Hypothesis:** A short RFC + benchmark run will create both thought leadership and validation data.

**MVP scope:**
1. **RFC:** A 6-page markdown doc (`docs/rfc-memory-taxonomy.md`) defining:
   - The five layers with formal semantics.
   - Promotion flow as a state machine.
   - Comparison to MemGPT paging and WorldDB ontology.
   - MCP bindings for each layer.
2. **Benchmark:** Use the existing `cua_world/pokemon_agent_env` harness to run:
   - Condition A: packet-equipped agent (full stack).
   - Condition B: Mem0-equipped agent (vector memory only).
   - Condition C: baseline (no memory, raw context only).
   Metrics: task completion rate, steps to completion on repetition (should drop for A), memory store growth (signal/noise ratio).

**Acceptance criteria:**
- [ ] RFC published to GitHub Discussions or as a repo doc.
- [ ] Benchmark completes ≥20 episodes per condition.
- [ ] Packet condition shows ≥30% step reduction on repeated tasks vs. baseline.
- [ ] Mem0 condition shows faster setup but no step reduction on repetition (expected: no procedural memory).

**Dependencies:**
- Working Pokemon benchmark environment.
- Mem0 API key or local install for Condition B.

**Estimated effort:** Medium (3-5 days for benchmark + RFC).

**Risk:** Benchmark results may not favor the packet if the task is too simple. Mitigation: choose a multi-step task that rewards skill reuse (e.g., the Pokemon type-coverage workflow).

---

## Recommended execution order

| Phase | Experiment | Why first? | Effort |
|---|---|---|---|
| **1** | Experiment 2: Skill trigger classifier | Highest leverage, lowest risk, builds on existing index + TEI path | Small-Medium |
| **2** | Experiment 1: Auto-reducer packets | Closes the biggest friction gap (episodic capture); classifier provides the trigger | Medium |
| **3** | Experiment 5: Taxonomy RFC + benchmark | Validates phases 1-2 with data; generates visibility | Medium |
| **4** | Experiment 4: Track A + C (Docker + unattended installer) | Removes adoption barrier just as public interest peaks | Small-Medium |
| **5** | Experiment 3: User-facing dashboard | Unlock non-technical users after core stack is proven | Medium |
| **6** | Experiment 4: Track B (hosted path) | Only if organic demand justifies the infrastructure cost | Large |

---

## Open questions

1. Should auto-reducer packets run inside the agent process (hook-based) or as an external watcher (file/log tail-based)?
2. For the skill classifier, should suggestions be injected into the system prompt, shown as a tool result, or surfaced via a separate MCP resource?
3. Does the local gateway have enough headroom to host a dashboard, or should it be a separate lightweight process?
4. Is there budget for a hosted path, or should the project remain strictly local-first with Docker as the only "easy" option?

---

## References

- `wiki/comparisons/llm-wiki-vs-sota-memory-systems.md` — gap identification
- `wiki/syntheses/agentic-memory-skill-stack-upgrade-2026.md` — literature grounding
- `wiki/syntheses/recent-csai-actionable-agent-memory-patterns-2026.md` — design patterns
- `SYSTEM_CONTRACT.md` — canonical layer mapping
- `.llm-wiki/config.json` — pipeline and registry settings
