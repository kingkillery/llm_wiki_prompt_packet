# Roadmap

> **Last updated:** 2026-04-22
> **Source of truth:** This file is the canonical project roadmap. Derive sprint tasks from `TODO.md`.

---

## North star

Close the four verified gaps versus state-of-the-art memory systems (Mem0, Zep, LangChain, LlamaIndex, Letta, Claude native, OpenAI memory) while preserving the packet's local-first, human-legible, and governance-friendly architecture.

---

## Milestones

### M1: Ambient Procedural Memory — Skill Trigger Classifier
**Target:** 2026-05-01
**Goal:** Stop forcing agents to search for skills. Proactively suggest the right skill before the first tool call.

**Deliverables:**
- Pre-computed skill embedding index updated automatically when `wiki/skills/active/` changes.
- Session-start similarity check against user intent.
- Compact suggestion injection (system prompt or tool result) with score threshold and opt-out.
- Reinforcement signal when suggestion is used vs. ignored.

**Success criteria:**
- ≥70% top-1 relevance on repeated task shapes.
- ≤15% false-positive rate.
- ≤500ms latency on local hardware.

---

### M2: Automatic Episodic Capture — Auto-Reducer Packets
**Target:** 2026-05-15
**Goal:** Remove the "remember to write a reducer packet" friction without abandoning the validation gate.

**Deliverables:**
- `scripts/auto_reducer_watcher.py` that detects session boundaries (via wrapper hooks or log tailing).
- Cheap summarizer path (BRV query or local Ollama) producing draft packets.
- Staging directory `.llm-wiki/skill-pipeline/auto-packets/` with review/approve/reject workflow.
- Integration with `skill_pipeline_run` so approved drafts auto-promote.

**Success criteria:**
- ≥80% of sessions with ≥10 tool calls produce a draft packet within 30s of session end.
- Draft contains: task summary, files changed, outcome signal, skill candidacy.
- Reviewable in ≤3 interactions.

---

### M3: Proof & Visibility — Taxonomy RFC + Head-to-Head Benchmark
**Target:** 2026-05-30
**Goal:** Publish the packet's architectural contributions and validate them empirically.

**Deliverables:**
- RFC document (`docs/rfc-memory-taxonomy.md`) formalizing the five-layer model, promotion state machine, and MCP bindings.
- Benchmark harness run: packet vs. Mem0 vs. baseline using `cua_world/pokemon_agent_env`.
- Metrics: task completion rate, repeated-task step reduction, memory store signal/noise ratio.

**Success criteria:**
- ≥20 episodes per condition.
- Packet condition shows ≥30% step reduction on repeated tasks vs. baseline.
- Mem0 condition shows no step reduction on repetition (confirms procedural memory is the differentiator).
- RFC published to GitHub Discussions.

---

### M4: Frictionless Onboarding — Docker + Unattended Installer
**Target:** 2026-06-15
**Goal:** Reduce time-to-working-stack from 30+ minutes to <5 minutes.

**Deliverables:**
- `docker run` one-liner that spins up qmd, GitVizz, TEI, and local gateway.
- `--unattended` installer flag for CI/devcontainer use (zero prompts, valid `.llm-wiki/config.json`).
- Preflight auto-detection of existing Node/bun/Docker versions to skip redundant installs.

**Success criteria:**
- New user has working stack in ≤5 minutes via Docker.
- Unattended installer exits 0 and produces valid config without human input.

---

### M5: Human Surface — Read-Only Memory Dashboard
**Target:** 2026-06-30
**Goal:** Give non-technical users a browser window into the wiki, skill registry, and BRV status.

**Deliverables:**
- FastAPI/Flask route group on local gateway (`/dashboard`).
- Views: memory browser, skill inspector, BRV status.
- Search across wiki pages.
- Mobile-readable CSS.
- Deep-link to Obsidian when running.

**Success criteria:**
- Dashboard loads in <2s.
- Search returns results in <1s.
- No write capabilities in MVP (safety).

---

### M6: Hosted Path (Deferred — Demand-Gated)
**Target:** TBD
**Goal:** Offer a cloud convenience layer for users who prioritize speed over local-first governance.

**Trigger criteria:**
- ≥10 organic requests for cloud sync or team sharing.
- M1–M4 are stable and documented.

**Out of scope until triggered.**

---

## Dependency graph

```
M1 (Skill Classifier)
  └── M2 (Auto-Reducer) ──> drafts are classified and suggested faster
  └── M3 (RFC + Benchmark) ──> classifier is part of the proven architecture

M2 (Auto-Reducer)
  └── M3 (RFC + Benchmark) ──> auto-capture is a cited feature in the benchmark

M4 (Docker / Installer)
  └── M5 (Dashboard) ──> dashboard is served by the same gateway container
```

---

## What we will NOT do

- Replace markdown with an opaque vector store. Human legibility is non-negotiable.
- Auto-promote memory without a validation gate. Curation discipline is the differentiator.
- Build a chat-native memory UI before the agent-facing stack is proven. M5 is explicitly last.

---

## Tracking

- Sprint tasks: `TODO.md`
- Design rationale: `wiki/syntheses/packet-gap-closure-roadmap-2026.md`
- Competitive context: `wiki/comparisons/llm-wiki-vs-sota-memory-systems.md`
- Log: `wiki/log.md`
