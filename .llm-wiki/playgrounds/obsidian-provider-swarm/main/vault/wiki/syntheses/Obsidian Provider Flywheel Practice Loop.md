---
type: synthesis
title: "Obsidian Provider Flywheel Practice Loop"
created: 2026-05-06
updated: 2026-05-06
tags:
  - flywheel
  - obsidian
  - research-memory
status: developing
related: []
sources:
  - [[obsidian-flywheel-practice-001]]
---

# Obsidian Provider Flywheel Practice Loop

The playground now exercises the Obsidian wiki layer through the packet runtime instead of only a minimal provider fixture.

## What was practiced

- A simulated research/architecture conversation produced durable knowledge.
- The save policy classified it as synthesis-worthy.
- The Obsidian provider saved the note, index, log, and hot cache.
- The packet flywheel created a manifest, reduced raw session output, evaluated promotion readiness, and attempted promotion routing.

## Durable lesson

Research-paper discussions, architectural conclusions, reusable debugging findings, decisions, and high-signal syntheses should trigger a forceful Obsidian save offer. For deep research, saving should be the default outcome unless the user opts out.

## Architecture conclusion

The clean layer split still holds:

- `llm_wiki_prompt_packet` owns installation, MCP wiring, retrieval, evaluation, and cross-agent memory workflow.
- `agent-cli-obsidian` contributes the behavior policy and wiki note taxonomy.
- `mcpvault` or direct-file provider handles vault reads and writes.

## Follow-up test expectation

Future agents should be able to retrieve this learning from `wiki/hot.md`, search the saved synthesis, and use the flywheel artifacts to decide whether the behavior should be promoted into semantic or procedural memory.
