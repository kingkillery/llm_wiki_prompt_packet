# Obsidian Provider Swarm Playground Report

Date: 2026-05-06

## Scope

All generated test artifacts were kept under:

```text
.llm-wiki/playgrounds/obsidian-provider-swarm/
```

The scenarios pretended to be users doing actions that should trigger the canonical Obsidian wiki provider:

- saving a substantial research-paper answer
- saving and later updating a durable decision
- writing/searching through the provider
- attempting a path traversal write
- running wiki-layer readiness in a minimal playground
- activating the playground with the full packet runtime and skill pipeline
- exercising a flywheel evaluation loop for Obsidian save behavior
- cloning a real repository fixture and evaluating source-backed Obsidian memory
- running the agent self-improvement harness against the playground behavior

## Scenario Results

| Scenario | Location | Result |
|---|---|---|
| Research paper answer save | `swarm/research-paper-flow/result.md` | PASS |
| Decision save/update duplicate prevention | `swarm/decision-and-update-flow/result.md` | PASS |
| Provider write/search/path safety | `swarm/provider-safety-flow/result.md` | PASS |
| Main playground synthesis save | `main/vault/wiki/syntheses/Canonical Obsidian Wiki Provider User Trial.md` | PASS |
| Wiki-layer readiness in minimal playground | `main` health-check output | WIKI PASS, broader stack expected FAIL |
| Full runtime activation | `main/.llm-wiki/skill-index.json` and copied runtime scripts | PASS |
| Flywheel manifest/reduce/evaluate/promote | `main/.llm-wiki/skill-pipeline/runs/obsidian-flywheel-practice-001/` | PASS |
| Flywheel synthesis save/search | `main/vault/wiki/syntheses/Obsidian Provider Flywheel Practice Loop.md` | PASS |
| Real Click repo fixture | `main/fixtures/click` at `73e155006526575548d143ef519995f540547e52` | PASS |
| Source-backed Click synthesis save/search | `main/vault/wiki/syntheses/Click Deprecation Handling Source-Backed Synthesis.md` | PASS |
| Agent self-improvement harness | `main/.ai/runs/20260506_011038/` | PASS with expected retrieval failure proposal |
| Patched fixture evidence retrieval | `main/.ai/runs/20260506_011658/` | PASS |

## Findings

1. `llm_wiki_save.py` successfully creates user-facing wiki notes and updates `wiki/index.md`, `wiki/log.md`, and `wiki/hot.md`.
2. Re-saving a same-title decision updates the existing note instead of creating a duplicate.
3. `llm_wiki_provider.py` direct-file writes stay inside the configured vault and reject `..\outside.md`.
4. `verify_wiki_layer()` reports wiki readiness OK with direct-file fallback when MCP transport is unavailable.
5. A Windows-specific config issue was found: PowerShell-created JSON with a UTF-8 BOM broke config loading. Fixed by reading JSON config with `utf-8-sig` in both provider and runtime loaders.
6. Running full stack health in a deliberately minimal playground still fails on unrelated missing skill-pipeline scripts and agent failure wrappers. The wiki-layer subsection itself reported OK, which is the expected result for this isolated playground.
7. The playground was then upgraded from a minimal provider fixture into a fully activated packet workspace with local runtime scripts, `.llm-wiki/skill-pipeline`, `skill-index.json`, managed `pk-qmd`, and managed `mcpvault`.
8. The corrected health check now reports the skill index current, Obsidian wiki layer ready, and MCP transport available.
9. The flywheel run created a manifest, reducer packet, claims, evaluation, and promotion decision for `obsidian-flywheel-practice-001`.
10. The synthetic flywheel evaluation correctly stayed conservative: task success and retrieval were sufficient, but citation quality was low, so the recommendation was `do-not-promote`. The dry-run promotion still routed the learning to semantic wiki, procedural skill proposal, and explicit preference curation targets.
11. The flywheel synthesis save refreshed `wiki/index.md`, `wiki/log.md`, and `wiki/hot.md`, and provider search retrieved the saved synthesis first.
12. A real `pallets/click` clone now gives the playground a source-backed repo with implementation files, tests, docs, and changelog material.
13. The Click deprecation scenario saved a durable Obsidian synthesis and provider search retrieved it first.
14. The agent self-improvement harness was scaffolded into the playground and configured with explicit Obsidian wiki tasks.
15. The harness found a real improvement signal: the source-backed save/search path passes, but `llm-wiki-packet evidence --plane local --deep` did not surface `fixtures/click`, despite direct `rg` finding the code. The harness generated a human-gated `benchmark-issue-flag`.
16. The harness also exposed a Windows path-length issue with verbose artifact names. The playground config now uses shorter task IDs and `.ai` as the harness output root.
17. The retrieval weakness was patched by including `fixtures/`, `.raw/`, and `playgrounds/` in deep/raw local evidence and widening deep/raw file reads to 50k characters.
18. The post-patch harness run `20260506_011658` passed both active tasks: saved-note retrieval and fixture-local evidence retrieval.

## Commands Verified

```powershell
py support\scripts\llm_wiki_save.py --workspace .llm-wiki\playgrounds\obsidian-provider-swarm\main --title "Canonical Obsidian Wiki Provider User Trial" --type synthesis --tag playground --tag obsidian --source "[[User Simulation]]" --related "[[Obsidian Canonical Wiki Provider]]" --body "..."
py support\scripts\llm_wiki_provider.py --workspace .llm-wiki\playgrounds\obsidian-provider-swarm\main search "canonical provider hot cache" --limit 5
py support\scripts\llm_wiki_memory_runtime.py check --workspace .llm-wiki\playgrounds\obsidian-provider-swarm\main --skip-qmd --skip-brv --skip-gitvizz
py scripts\llm_wiki_packet.py setup --workspace-root .
py scripts\llm_wiki_packet.py manifest --workspace-root . --run-id obsidian-flywheel-practice-001 --json
py scripts\llm_wiki_packet.py reduce --workspace-root . --run-id obsidian-flywheel-practice-001 --source-file .llm-wiki\skill-pipeline\runs\obsidian-flywheel-practice-001\raw-session.md --json
py scripts\llm_wiki_packet.py evaluate --workspace-root . --run-id obsidian-flywheel-practice-001 --task-success pass --retrieval-sufficiency sufficient --retrieval-plane obsidian --retrieval-plane local-files --default-context-sufficient no --json
py scripts\llm_wiki_packet.py promote --workspace-root . --run-id obsidian-flywheel-practice-001 --target auto --json
py scripts\llm_wiki_save.py --workspace . --title "Obsidian Provider Flywheel Practice Loop" --type synthesis --tag flywheel --tag obsidian --tag research-memory --source "[[obsidian-flywheel-practice-001]]" --body-file .llm-wiki\skill-pipeline\runs\obsidian-flywheel-practice-001\save-note-body.md
py scripts\llm_wiki_provider.py --workspace . search "Obsidian Provider Flywheel Practice Loop" --limit 10
git clone --depth 1 https://github.com/pallets/click.git fixtures\click
py scripts\llm_wiki_save.py --workspace . --title "Click Deprecation Handling Source-Backed Synthesis" --type synthesis --tag real-repo --tag click --tag deprecation --tag research-memory --source "[[click-real-repo-obsidian-001]]" --body-file .llm-wiki\skill-pipeline\runs\click-real-repo-obsidian-001\source-backed-synthesis.md
py scripts\llm_wiki_provider.py --workspace . search "Click Deprecation Handling Source-Backed Synthesis" --limit 10
python .agent-improvement\scripts\repo_local_harness.py all --config agent-improvement.config.json
python .agent-improvement\scripts\repo_local_harness.py evaluate --config agent-improvement.config.json
python .agent-improvement\scripts\repo_local_harness.py analyze --config agent-improvement.config.json
python .agent-improvement\scripts\repo_local_harness.py propose --config agent-improvement.config.json
python .agent-improvement\scripts\repo_local_harness.py report --config agent-improvement.config.json
py -m pytest tests\test_llm_wiki_provider.py tests\test_llm_wiki_save.py tests\test_llm_wiki_memory_runtime.py
```

## Verification

Focused tests after the playground-discovered BOM fix:

```text
32 passed
```

Focused tests after the full playground activation and flywheel run:

```text
57 passed
```

## Notes

One delegated provider-safety worker was blocked by platform safety filtering, so the provider safety scenario was completed locally in the same isolated playground.
