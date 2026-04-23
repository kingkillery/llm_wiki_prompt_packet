# RFC: LLM Wiki Memory Taxonomy

> **Status:** Draft  
> **Date:** 2026-04-22  
> **Author:** llm-wiki-memory maintainers  
> **Scope:** Formalize the five-layer memory model, promotion state machine, and retrieval contracts for the `llm-wiki-memory` stack.  

---

## 1. Motivation

Most LLM/agent memory systems today treat memory as a single bucket: ingest conversation turns, embed them, retrieve nearest neighbors. This works for chatbots but breaks down for autonomous agents that must reuse procedures, recall durable facts, and respect preference boundaries across sessions.

The `llm-wiki-memory` stack uses five distinct memory layers. This RFC formalizes their semantics, promotion rules, and MCP bindings so that:

1. Future agents can reason about *which* layer to read or write without guessing.
2. Tool builders can implement compatible memory planes (vector stores, graph DBs, file systems) against a stable contract.
3. Researchers can compare the taxonomy against MemGPT, WorldDB, and other architectures using shared vocabulary.

---

## 2. Layer Definitions

### 2.1 Working Memory

**Definition:** Hot context that should usually stay in prompts or active session state.

**Store:** Active prompt context, `AGENTS.md`, `CLAUDE.md`, currently open files.

**Lifetime:** Single turn or single session. Discarded on session end.

**Write trigger:** Automatic (files opened by user/agent).

**Read path:** Direct injection into prompt. No retrieval step.

**MCP binding:** None (implicit in prompt construction).

### 2.2 Episodic Memory

**Definition:** Trajectory summaries, concrete run history, and raw exploration artifacts.

**Store:** `.llm-wiki/skill-pipeline/briefs/`, `packets/`, `failures/`, `auto-packets/`.

**Lifetime:** Days to weeks. Compressed or promoted after review.

**Write trigger:** After any task with real exploration cost (≥10 tool calls, novel failure, multi-step workflow).

**Read path:** `pk-qmd` search or direct path lookup.

**MCP binding:** `pk-qmd` stdio server.

### 2.3 Semantic Memory

**Definition:** Durable repo facts, concepts, syntheses, and validated decisions.

**Store:** `wiki/concepts/`, `wiki/syntheses/`, `wiki/entities/`, `wiki/comparisons/`, `wiki/timelines/`.

**Lifetime:** Months to years. Updated on contradiction or new evidence.

**Write trigger:** After validation; when a fact should survive the current session.

**Read path:** `pk-qmd` semantic/lexical search.

**MCP binding:** `pk-qmd` stdio server + `obsidian` MCP for vault mutations.

### 2.4 Procedural Memory

**Definition:** Reusable recipes, shortcuts, and stable workflows.

**Store:** `wiki/skills/active/` + `.llm-wiki/skills-registry.json`.

**Lifetime:** Indefinite. Versioned, evolved, retired when score drops below threshold.

**Write trigger:** After skill pipeline validation (`route_decision: complete`).

**Read path:** `skill_lookup` MCP tool or `pk-qmd` search.

**MCP binding:** `llm-wiki-skills` stdio server.

### 2.5 Preference Memory

**Definition:** Stable user or workflow preferences that survive project boundaries.

**Store:** `brv` context tree.

**Lifetime:** Indefinite. Curated explicitly.

**Write trigger:** When a preference is reusable, stable, and costly to rediscover.

**Read path:** `brv query`.

**MCP binding:** `brv` stdio server.

---

## 3. Promotion State Machine

```
raw task output
    │
    ▼
reducer packet (episodic)
    │
    ├── validated fact ──► wiki page (semantic)
    │
    ├── validated shortcut ──► active skill (procedural)
    │
    └── user/workflow preference ──► brv curate (preference)
```

### 3.1 Rules

1. **Never write directly to semantic or procedural memory without a validation step.** Episodic artifacts are the staging area.
2. **Prefer source evidence over memory when they conflict.** Current `pk-qmd` evidence wins.
3. **Do not write durable memory for transient runtime state.**
4. **Keep the wiki legible to humans.** Markdown is the canonical store format.

### 3.2 State Transitions

| From | To | Trigger | Gate |
|---|---|---|---|
| Working | Episodic | Session produces exploration cost | Automatic (auto-reducer watcher) |
| Episodic | Semantic | Fact validated against source | Human or surrogate review |
| Episodic | Procedural | Shortcut reusable ≥2 times | Skill pipeline validation (score ≥7) |
| Episodic | Preference | Workflow quirk confirmed | `brv curate` with explicit consent |
| Semantic | Retired | Contradicted by new evidence | Update or archive with provenance |
| Procedural | Retired | Score < -3 or superseded | `skill_retire` + index update |

---

## 4. Retrieval Contracts

### 4.1 Plane Routing

| Need | First plane | Fallback | Never use |
|---|---|---|---|
| Exact evidence, docs, prompts | `pk-qmd` | Direct file I/O | `brv` for codebase questions |
| Repo topology, API surface | `GitVizz` | `pk-qmd` path search | `brv` for structure |
| Durable preferences | `brv` | `wiki/concepts/` temporary | `pk-qmd` for preference recall |
| Reusable workflow | `skill_lookup` | `pk-qmd` keyword search | Raw `brv` for procedures |

### 4.2 Retrieval Quality Requirements

- **Recency decay:** Skill scores decay exponentially with age (`halflife_days` configurable, default 30).
- **Graph traversal:** Skills expose `related_skills` edges (prerequisite, conflict, successor). Traversal returns up to 2 neighbors per relation type.
- **Automatic index maintenance:** Setup and health-check flows refresh `.llm-wiki/skill-index.json`; wrapped interactive sessions and the dashboard lazily rebuild it when active skills, retired skills, feedback, or config changed.
- **Conflict resolution:** When `brv` and `wiki/` disagree, current source evidence (`pk-qmd`) wins.

---

## 5. MCP Bindings

### 5.1 Required Servers

| Server | Command | Purpose | Required? |
|---|---|---|---|
| `pk-qmd` | `pk-qmd mcp` | Source evidence retrieval | Always |
| `llm-wiki-skills` | `python llm_wiki_skill_mcp.py mcp` | Skill lifecycle | Always |
| `obsidian` | `npx -y @bitbonsai/mcpvault <vault-path>` | Vault scribing | Pivotal but optional |
| `brv` | `brv mcp` | Durable memory | Optional |

### 5.2 Skill Lifecycle Tools

| Tool | Action |
|---|---|
| `skill_lookup` | Find matching skills by goal or trigger |
| `skill_reflect` | Emit reducer packet from trajectory |
| `skill_validate` | Check privacy, duplicates, evidence quality |
| `skill_pipeline_run` | Full ACE loop: reflect → validate → curate |
| `skill_propose` | Create skill proposal from packet |
| `skill_evolve` | Update existing skill with new evidence |
| `skill_feedback` | Record human or automated feedback |
| `skill_retire` | Move skill to retired/ with reason |

---

## 6. Comparison to Related Work

| System | Memory Model | Write Strategy | Retrieval | Procedural Memory |
|---|---|---|---|---|
| **LLM Wiki (this RFC)** | 5-layer with promotion | Explicit curation (ACE loop) | Multi-plane: qmd + graph + brv | Typed skill objects with lifecycle |
| MemGPT / Letta | OS paging (virtual context) | Auto memory pressure | Hierarchical context paging | Agent config, not reusable skills |
| WorldDB | Vector + graph with ontology | Write-time reconciliation | Graph traversal + vector | Implicit in ontology |
| Zep | Episodic + semantic auto-ingest | Auto-ingest + manual edit | Vector + session graph | None native |
| Mem0 | Entity + fact extraction | Auto-ingest every turn | Vector + keyword | None native |
| LangChain Memory | Buffer, window, vector, summary | Manual or callback | Vector or buffer | Tool descriptions only |

**Key differentiators of this taxonomy:**
1. **Explicit procedural memory** as first-class typed objects (not just tool descriptions or agent configs).
2. **Curation gate** before promotion (not append-only ingestion).
3. **Human-legible markdown stores** for governance and audit.
4. **Recency decay + graph traversal** in retrieval (not just static similarity).
5. **Auto-maintained procedural index** so end users do not need to understand or manually rebuild retrieval artifacts.

---

## 7. Backwards Compatibility

- All changes are additive. Existing skills without `related_skills` edges degrade gracefully to flat similarity search.
- `halflife_days` defaults to `30.0`; omitted values in config fall back safely.
- `brv` remains optional; preference-class knowledge can be staged in `wiki/concepts/` temporarily.

---

## 8. Open Questions

1. Should episodic memory support automatic compression into "epoch" summaries after N days?
2. Should the retrieval gate be learned (small classifier) or remain rule-based?
3. Should preference memory support cross-project sync, or remain project-scoped?
4. What is the formal semantics of `conflict` edges between skills? (Mutual exclusion, or warning?)

---

## 9. References

- `LLM_WIKI_MEMORY.md` — routing rules and wiki/brv routing table
- `SYSTEM_CONTRACT.md` — canonical layer-to-store mapping
- `SKILL_CREATION_AT_EXPERT_LEVEL.md` — skill promotion pipeline details
- `docs/decisions/ADR-001-automatic-skill-index-maintenance.md` — derived-artifact maintenance decision
- `wiki/syntheses/agentic-memory-skill-stack-upgrade-2026.md` — literature review
- `wiki/syntheses/recent-csai-actionable-agent-memory-patterns-2026.md` — design patterns
- `wiki/syntheses/quickscope-memory-retrieval-improvements-2026.md` — retrieval gap closure
