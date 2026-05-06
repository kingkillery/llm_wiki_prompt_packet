# Obsidian Flywheel Evaluation Report

Date: 2026-05-06

## Workspace

The playground at `main/` is now a full packet activation target, not just a minimal provider fixture.

Installed/activated surfaces include:

- `.llm-wiki/config.json`
- `.llm-wiki/skill-index.json`
- `.llm-wiki/skill-pipeline/`
- local `scripts/llm_wiki_packet.py`
- local `scripts/llm_wiki_memory_runtime.py`
- local `scripts/llm_wiki_provider.py`
- local `scripts/llm_wiki_save.py`
- managed Obsidian MCP transport dependency
- managed `pk-qmd` checkout and wrappers

## Health

The corrected health check reports:

- skill index current
- Obsidian provider configured
- behavior layer: `agent-cli-obsidian`
- transport: `mcpvault`
- MCP transport readiness: available
- wiki layer readiness: ok

## Run

Run id: `obsidian-flywheel-practice-001`

Artifacts:

- `.llm-wiki/skill-pipeline/runs/obsidian-flywheel-practice-001/manifest.json`
- `.llm-wiki/skill-pipeline/runs/obsidian-flywheel-practice-001/raw-session.md`
- `.llm-wiki/skill-pipeline/runs/obsidian-flywheel-practice-001/reducer_packet.md`
- `.llm-wiki/skill-pipeline/runs/obsidian-flywheel-practice-001/claims.json`
- `.llm-wiki/skill-pipeline/runs/obsidian-flywheel-practice-001/evaluation.json`
- `.llm-wiki/skill-pipeline/runs/obsidian-flywheel-practice-001/promotion_decision.json`

## Evaluation Result

The synthetic run passed the task and had sufficient retrieval, but the evaluator recommended `do-not-promote` because citation quality was low. That is the right conservative behavior for a simulated run.

The dry-run promotion router still produced the expected target plan:

- semantic learning to `wiki/syntheses/obsidian-flywheel-practice-001.md`
- procedural learning to `.llm-wiki/skill-pipeline/proposals/obsidian-flywheel-practice-001-skill-candidate.md`
- preference learning left explicit through BRV curation

## Obsidian Save Result

Saved note:

- `vault/wiki/syntheses/Obsidian Provider Flywheel Practice Loop.md`

Provider search for `Obsidian Provider Flywheel Practice Loop` returned:

1. `wiki/syntheses/Obsidian Provider Flywheel Practice Loop.md`
2. `wiki/log.md`
3. `wiki/hot.md`
4. `wiki/syntheses/Canonical Obsidian Wiki Provider User Trial.md`
5. `wiki/index.md`

## Practical Conclusion

The playground now gives future agents a useful practice loop:

1. simulate a user action that should trigger durable Obsidian memory
2. save the durable synthesis/decision/source/session note
3. verify retrieval through provider search and `wiki/hot.md`
4. create packet run artifacts
5. reduce the run into memory candidates
6. evaluate promotion readiness
7. route promotion conservatively

## Real Repo Fixture Upgrade

The playground now includes a cloned real repository fixture:

- Repo: `https://github.com/pallets/click.git`
- Path: `fixtures/click`
- Commit: `73e155006526575548d143ef519995f540547e52`

Additional run:

- Run id: `click-real-repo-obsidian-001`
- Task: inspect Click deprecation behavior across commands, options, arguments, and parser compatibility, then save the reusable conclusion to Obsidian.
- Saved note: `vault/wiki/syntheses/Click Deprecation Handling Source-Backed Synthesis.md`

Provider search for `Click Deprecation Handling Source-Backed Synthesis` returned the saved note first, followed by `wiki/hot.md`, `wiki/log.md`, and `wiki/index.md`.

This scenario gives agents real code, tests, docs, and changelog material to inspect instead of a toy fixture.

## Self-Improvement Harness

The `$agent-self-improvement-harness` scaffold was added to this playground:

- `agent-improvement.config.json`
- `.agent-improvement/scripts/repo_local_harness.py`
- `.agent-improvement/scripts/native_eval_adapter.py`
- `.agent-improvement/scripts/obsidian_fixture_eval.py`
- `benchmarks/cua_world/environments/obsidian_wiki_env/`
- `.ai/runs/20260506_011038/`

Harness tasks:

- `save`: verifies the Click fixture exists, the source-backed synthesis is saved, and provider search retrieves it.
- `retrieval`: verifies packet local evidence retrieval surfaces `fixtures/click` source evidence.

Harness result:

- The `save` holdout task passed.
- The `retrieval` train task failed because packet local evidence did not surface `fixtures/click`, even though direct `rg` found the source evidence.
- The harness generated a human-gated `benchmark-issue-flag` proposal in `.ai/runs/20260506_011038/proposals.md`.

Practical finding: the Obsidian save/retrieval path works on the real repo fixture, but packet local evidence coverage should be improved so cloned playground fixtures are searched as first-class source evidence.

## Retrieval Patch Result

Patch applied:

- Deep/raw local evidence now includes `raw/`, `.raw/`, `fixtures/`, and `playgrounds/`.
- Deep/raw local evidence reads up to 50k characters per file instead of the compact 8k window, so large source files such as `fixtures/click/src/click/core.py` can surface relevant later sections.

Regression added:

- `tests/test_llm_wiki_packet.py::PacketCliTests::test_deep_evidence_includes_fixture_repositories`

Post-patch harness run:

- Run: `.ai/runs/20260506_011658/`
- Task count: 2
- Success count: 2
- Failure count: 0
- Review packet: `.ai/runs/20260506_011658/review_packet.md`

The previous retrieval weakness is patched: packet local evidence now surfaces `fixtures/click/src/click/core.py`.
