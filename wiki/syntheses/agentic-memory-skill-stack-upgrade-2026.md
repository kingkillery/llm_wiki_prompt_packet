# Agentic Memory Skill Stack Upgrade (2026)

## Goal

Translate recent agentic-AI and memory-architecture literature into concrete upgrades for the `llm-wiki-memory` skill stack.

## Literature reviewed

Primary papers and sources reviewed from the session prompt:

1. **Memory in the LLM Era: Modular Architectures and Strategies in a Post-Context World** (2026)
2. **Agent-Native Memory Through LLM-Curated Hierarchical Context** (2026)
3. **Knowledge Objects for Persistent LLM Memory** (2026)
4. **Titans + MIRAS: Helping AI Have Long-Term Memory** (Google Research, 2025)
5. **The 2025 AI Agent Index** (2025)
6. **MemGPT / MemoryOS / Zep / MemoryBank / A-MEM / MemTree** cluster (surveyed in 2026)
7. **Survey on LLM Agents (CoLing 2025)**
8. **LLM Autonomous Agents: Comprehensive Survey & Guide** (2026)
9. **LLM Agent Survey: Methodology & Applications** (2026)
10. **Small Language Models are the Future of Agentic AI** (NVIDIA Research)

## Local skill references mined for one more pass

From `C:/Users/prest/.agents/skills1/pk-skills1`:

- `memory-management` — strong promotion/demotion split between hot cache and deep memory
- `architect_high_autonomy_agentic_systems` — explicit episodic/narrative memory framing inside the full agent loop
- `agent-self-improvement-harness` — benchmark, failure clustering, proposal, regression, and human-gated improvement loop

## Selected upgrades

### 1. Memory is now treated as layered, not monolithic

Packet-native mapping:

- **Working memory** → active prompt context, `AGENTS.md`, `CLAUDE.md`, open files
- **Episodic memory** → `.llm-wiki/skill-pipeline/briefs/` and `.llm-wiki/skill-pipeline/packets/`
- **Semantic memory** → `wiki/` pages
- **Procedural memory** → `wiki/skills/active/`
- **Preference memory** → `brv`

### 2. Active skills are treated as typed memory objects

The upgraded skill pipeline now supports:

- `memory_scope`
- `memory_strategy`
- `update_strategy`
- `durable_facts`
- `provenance_refs`
- `retrieval_hints`

This is the packet-native equivalent of moving from flat notes toward structured, persistent knowledge objects.

### 3. Long tasks now default toward hierarchical memory

For long or trajectory-heavy runs, the contract now prefers:

- reducer packet first
- summary-only packet surface
- durable facts plus provenance
- non-flat memory strategy for promotion into active skills

### 4. Evolution remains frontier-based and human-gated

The repo already had a strong reflection/validation/evolution loop. The upgrade keeps that structure and makes it more memory-aware rather than replacing it.

### 5. Practical model-tiering implication

The repo contract still assumes high-quality verifier/reviewer models for curation and frontier decisions, while lighter-weight summarization and lookup tasks can remain cheaper. The current uplift documents this policy without hardcoding a single provider strategy.

## Files upgraded in this pass

- `support/scripts/llm_wiki_skill_mcp.py`
- `tests/test_llm_wiki_skill_mcp.py`
- `LLM_WIKI_MEMORY.md`
- `SKILL_CREATION_AT_EXPERT_LEVEL.md`
- `SYSTEM_CONTRACT.md`
- `prompts/00-system-prompt.md`
- `prompts/04-tool-directives.md`
- `skills/home/llm-wiki-skills/SKILL.md`

## Why these were the highest-leverage targets

These surfaces define how the entire stack learns, stores reusable knowledge, validates changes, and exposes that behavior to downstream agents. Updating them raises the quality of all future skills instead of optimizing only one narrow workflow.

## Result

The packet is now materially closer to the literature consensus:

- modular memory layers instead of one memory bucket
- hierarchical promotion from episodes to reusable procedural memory
- typed skill memory objects instead of plain markdown-only skill records
- provenance-aware updates and deprecation paths
- frontier-based self-improvement preserved as the control loop
