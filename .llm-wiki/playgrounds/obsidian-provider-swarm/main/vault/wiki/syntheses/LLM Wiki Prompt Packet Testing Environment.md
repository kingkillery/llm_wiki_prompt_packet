---
type: synthesis
title: "LLM Wiki Prompt Packet Testing Environment"
created: 2026-05-06
updated: 2026-05-06
tags:
  - testing
  - obsidian
  - evaluation
  - harness
status: developing
related: []
sources:
  - [[obsidian-provider-swarm-playground]]
---

# LLM Wiki Prompt Packet Testing Environment

This testing environment was built to make the Obsidian/wiki layer prove itself under repeated pressure, not just pass toy checks.

## What Exists

- Playground root: `.llm-wiki/playgrounds/obsidian-provider-swarm/`
- Activated packet workspace: `.llm-wiki/playgrounds/obsidian-provider-swarm/main/`
- Real repo fixture: `.llm-wiki/playgrounds/obsidian-provider-swarm/main/fixtures/click`
- Fixture source: `https://github.com/pallets/click.git`
- Fixture commit: `73e155006526575548d143ef519995f540547e52`
- Harness config: `.llm-wiki/playgrounds/obsidian-provider-swarm/main/agent-improvement.config.json`
- Latest passing harness run: `.llm-wiki/playgrounds/obsidian-provider-swarm/main/.ai/runs/20260506_012427/`

## What It Tests

The environment exercises the packet across the full wiki loop:

1. retrieve source-backed evidence from a real cloned repository
2. save durable research and architecture conclusions into Obsidian/wiki notes
3. update `wiki/index.md`, `wiki/log.md`, and `wiki/hot.md`
4. search the saved notes through the provider
5. create flywheel artifacts with manifest/reduce/evaluate/promote commands
6. run the agent self-improvement harness
7. catch retrieval weaknesses and verify patches

## Important Result

The first real-repo harness found a meaningful weakness: `llm-wiki-packet evidence --plane local --deep` did not search cloned fixture repos, so it missed `fixtures/click` even though direct `rg` found the relevant source.

That weakness was patched:

- deep/raw local evidence now includes `raw/`, `.raw/`, `fixtures/`, and `playgrounds/`
- deep/raw local evidence reads up to 50k characters per file so large source files can surface relevant sections
- regression coverage was added in `tests/test_llm_wiki_packet.py`

After the patch, the harness passed both active tasks:

- saved-note retrieval passed
- fixture-local evidence retrieval passed

Latest verification:

- harness run `20260506_012427`: 2 tasks, 2 successes, 0 failures
- focused pytest suite: 58 passed

## Durable Lesson

The Obsidian/wiki layer should be tested with real codebases, real notes, and repeated evaluation loops. The useful pattern is:

```text
real repo fixture -> source-backed synthesis -> Obsidian save -> provider search -> flywheel evaluation -> harness regression
```

This is the right shape for future packet testing. The environment is intentionally closer to a training chamber than a static smoke test: it should keep exposing weak retrieval, save, and promotion behavior until those paths become reliable.
