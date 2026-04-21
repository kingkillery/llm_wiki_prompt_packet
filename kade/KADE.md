# KADE.md

## Workspace

- root: `C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet`
- layering result: `repo-local intentional memory loop active`

## Repo Runtime Contract

- official Obsidian memory base: `C:\dev\Desktop-Projects\Helpful-Docs-Prompts\VAULTS-OBSIDIAN\Kade-HQ\llm_wiki_prompt_packet System Map.md`
- official vault identity: `kade-hq` / `fd8411f00d3a9d21`
- `g-kade`: status `detected`, configured `deps/pk-skills1/gstack/g-kade`
- `gstack`: status `detected`, configured `deps/pk-skills1/gstack`
- core launcher wrappers: `skills/home/kade-hq`, `skills/home/g-kade`, and `skills/home/gstack`
- reusable benchmark launcher: `skills/home/pokemon-benchmark`
- pi home launcher root: `C:\Users\prest\.pi\agent\skills`
- local Docker gateway: `127.0.0.1:8181`
- gateway routes: `/mcp`, `/graph/*`, `/memory/status`, `/memory/query`, `/memory/curate`
- local Docker auth: none on loopback-only binds; hosted or tunnelled access must add auth

## Handoff Log

2026-04-21T00:20:00Z - Literature-driven memory architecture simplification pass
Changed: upgraded the packet skill-learning plane with typed memory-object fields, layered-memory guidance, and WorldDB-style write-time reconciliation keys; then simplified the packet-owned `kade-hq`, `gstack`, and `g-kade` wrappers so they preserve the Kade homage while still reflecting controller-style memory routing and capability-aware harness choices.
Files: `support/scripts/llm_wiki_skill_mcp.py`, `tests/test_llm_wiki_skill_mcp.py`, `LLM_WIKI_MEMORY.md`, `SKILL_CREATION_AT_EXPERT_LEVEL.md`, `SYSTEM_CONTRACT.md`, `prompts/00-system-prompt.md`, `prompts/04-tool-directives.md`, `skills/home/llm-wiki-skills/SKILL.md`, `skills/home/kade-hq/SKILL.md`, `skills/home/gstack/SKILL.md`, `skills/home/g-kade/SKILL.md`, `.factory/memories.md`, the new vault progress files, and the repo wiki synthesis note.
Why: recent 2026 memory and harness papers pushed the stack toward hierarchical memory objects, explicit controller-style memory operations, capability-aware routing, and write-time reconciliation; the user also asked to keep the Kade framing simpler and more abstract.
Verified: [x] `python -m pytest tests/test_llm_wiki_skill_mcp.py -q`.
Next: if needed, extend the same simplified memory-routing language into README quickstarts and add one or two concrete active skills that demonstrate the new procedural-memory schema.


2026-04-13T13:11:00-06:00 - Packet-owned Pokemon benchmark skill landed for neutral repos
Changed: added `skills/home/pokemon-benchmark` as a packet-owned launcher skill that tells agents how to bootstrap a neutral repo with `llm_wiki_prompt_packet`, then run the installed smoke or framework Pokemon benchmark paths and report from `result.json`. Bootstrap installers now copy `support/scripts/pokemon_benchmark_adapter.py` and `support/scripts/run_pokemon_benchmark.ps1` into installed workspaces and scaffold the `pokemon-benchmark` skill into repo-local `.agents`, `.codex`, and `.claude` skill roots.
Files: `skills/home/pokemon-benchmark/SKILL.md`, `skills/home/pokemon-benchmark/agents/openai.yaml`, `installers/install_obsidian_agent_memory.py`, `installers/install_g_kade_workspace.py`, `tests/test_install_obsidian_agent_memory.py`, `tests/test_install_g_kade_workspace.py`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the benchmark runner already worked from this source repo, but neutral repos still had no reusable installed skill that knew how to bootstrap the packet and launch the benchmark through the supported wrapper surface.
Verified: [x] `python C:\Users\prest\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\home\pokemon-benchmark`; [x] `python -m unittest discover -s tests -p "test_install_obsidian_agent_memory.py"`; [x] `python -m unittest discover -s tests -p "test_install_g_kade_workspace.py"`; [x] bootstrap into a temporary neutral repo with `python .\installers\install_g_kade_workspace.py --workspace <temp-repo> --home-root <temp-home> --skip-setup --force`; [x] installed neutral repo smoke run via `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pokemon_benchmark.ps1 -Mode smoke`; [x] installed neutral repo framework run via `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pokemon_benchmark.ps1 -Mode framework -Agent codex -TimeoutSec 1200`; [x] both installed neutral-repo runs produced verifier score 100 with `success: true`.
Next: add shell or cmd benchmark launchers only if another environment needs a first-class non-PowerShell surface; the current installed skill and runner are already validated for the Windows neutral-repo flow.

2026-04-13T13:24:00-06:00 - pi home install and prompt framing updated for Pokemon benchmark skill
Changed: clarified that Pi home-skill install uses `C:\Users\prest\.pi\agent\skills`, not `C:\Users\prest\.pi\agents\skills`, and aligned the packet home-skill surface there to include `kade-hq`, `g-kade`, `gstack`, and `pokemon-benchmark`. The skill text and framework prompt still make clear that the harness or skill under test is invoked with `pokemon-benchmark` available as the benchmark-side coordinator rather than the launcher skill being the evaluated system by itself.
Files: `skills/home/pokemon-benchmark/SKILL.md`, `support/scripts/pokemon_benchmark_adapter.py`, `installers/install_obsidian_agent_memory.py`, `tests/test_install_obsidian_agent_memory.py`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the user corrected the Pi-native home-skill path, and the packet needs its wrapper trio plus the benchmark launcher available there without leaving the mistaken `.pi\agents` install behind.
Verified: [x] `python -m unittest discover -s tests -p "test_install_obsidian_agent_memory.py"`; [x] direct install into `C:\Users\prest\.pi\agent\skills`; [x] verified `SKILL.md`, `agents/openai.yaml`, and `.llm-wiki-packet-owner.json` for `kade-hq`, `g-kade`, `gstack`, and `pokemon-benchmark`; [x] removal of mistaken `C:\Users\prest\.pi\agents\skills\pokemon-benchmark`.
Next: keep future Pi installer and memory updates pinned to `.pi\agent\skills` so the wrong pluralized path does not reappear.

2026-04-13T14:05:00-06:00 - Project activation quickstart landed for packet plus Pi flow
Changed: added `support/scripts/activate_llm_wiki_project.ps1` as a thin activation wrapper over `install_g_kade_workspace.py`, and documented a repo-to-project quickstart block in `README.md`. The activation path is now: point the packet checkout at a target repo, bootstrap packet files there, install packet-owned home wrappers including Pi's `C:\Users\prest\.pi\agent\skills`, and run the shared setup/check flow so project-local `pk-qmd`, `brv`, and configured `GitVizz` surfaces are activated without manually reconstructing installer arguments.
Files: `support/scripts/activate_llm_wiki_project.ps1`, `README.md`, `installers/install_obsidian_agent_memory.py`, `installers/install_g_kade_workspace.py`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the packet already had the right low-level installer surfaces, but it did not offer a direct command-block quickstart for activating a specific project, especially when Pi needed to participate as a first-class launcher surface.
Verified: [x] wrapper smoke against a temporary target repo with `powershell -NoProfile -ExecutionPolicy Bypass -File .\support\scripts\activate_llm_wiki_project.ps1 -ProjectRoot <temp-project> -HomeRoot <temp-home> -SkipSetup -Force`; [x] verified temp project packet files plus temp-home `.pi\agent\skills\pokemon-benchmark` and `.pi\agent\skills\gstack`; [x] README quickstart command review.
Next: keep this wrapper as the stable project-activation entry surface unless a future Pi-native extension becomes necessary for MCP/runtime wiring.

2026-04-13T02:26:00-06:00 - Pokemon benchmark self-test path landed
Changed: added `support/scripts/pokemon_benchmark_adapter.py` and `support/scripts/run_pokemon_benchmark.ps1` so this repo can act as the agent-under-test against Gym-Anything's Pokemon benchmark. The adapter starts a real Gym session, supports a deterministic headless smoke mode plus a wrapper-driven framework mode, reuses `support/scripts/run_llm_wiki_agent.ps1` and the existing failure-capture plane, writes prompt/task/session/verification/result artifacts under `.artifacts/pokemon-benchmark/runs/`, and includes a narrow `session-write-report` helper so the required `/root/Desktop/pokemon_session_report.json` can be created inside the live container without brittle shell quoting. `support/scripts/run_llm_wiki_agent.ps1` now also accepts `-ArgumentJson` for machine-driven noninteractive agent calls.
Files: `support/scripts/pokemon_benchmark_adapter.py`, `support/scripts/run_pokemon_benchmark.ps1`, `support/scripts/run_llm_wiki_agent.ps1`, `.gitignore`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the repo needed a reusable harness-owned evaluation surface for the Pokemon benchmark that preserved the existing wrapper and failure-capture behavior instead of introducing a separate one-off benchmark runner.
Verified: [x] `python -m py_compile support/scripts/pokemon_benchmark_adapter.py`; [x] `python support/scripts/pokemon_benchmark_adapter.py smoke`; [x] `python support/scripts/pokemon_benchmark_adapter.py framework --agent codex --timeout-sec 1200`; [x] smoke verifier 100/100; [x] framework verifier 100/100.
Next: add tested default launcher presets for Claude Code, Factory Droid, and `pi` if they need the same benchmark path, while keeping the current adapter contract benchmark-agnostic enough to reuse for other Gym-Anything tasks.

2026-04-13T00:00:00-06:00 - Subjective EvoSkill verifier path landed
Changed: extended `support/scripts/llm_wiki_skill_mcp.py` so `skill_evolve` now distinguishes objective, heuristic, and subjective verifier modes. Objective runs still honor explicit oracle-style verdicts, while subjective tasks can now carry a VMR-inspired pairwise verifier packet with deterministic A/B ordering, a plain `A`/`B` judge prompt that works across Claude Code, Codex, Factory Droid, and `pi`, rubric criteria, and a candidate-win or baseline-win outcome. The repeated-failure collector now preserves those subjective verifier fields when promoting clusters into `skill_evolve`.
Files: `support/scripts/llm_wiki_skill_mcp.py`, `support/scripts/llm_wiki_failure_collector.py`, `tests/test_llm_wiki_skill_mcp.py`, `tests/test_llm_wiki_failure_collector.py`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the repo already had a good objective and heuristic evolution path, but subjective day-to-day work still collapsed into metadata-only surrogate judgments. That was too weak for writing, UX, and other non-benchmark tasks where the right fallback is a structured pairwise comparison, not a looser scalar guess.
Verified: [x] `python -m unittest discover -s tests -p "test_llm_wiki_skill_mcp.py"`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_failure_collector.py"`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_*.py"`.
Next: wire any external daily-work evaluators to submit `baseline_output`, `candidate_output`, `subjective_task`, and `judge_choice` so subjective evolutions can resolve automatically instead of stopping at packet generation.

2026-04-12T19:29:59.4610614-06:00 - Cross-agent failure wrapper landed for Codex, Factory Droid, and pi
Changed: added a shared CLI failure wrapper in `support/scripts/llm_wiki_agent_failure_capture.py`, shipped launcher surfaces for PowerShell, bash, and cmd, extended installer/runtime/config defaults to include `pi`, added wrapper tests, and fixed the PowerShell launcher plus Windows console encoding edge cases found during live smoke tests. Claude keeps native `.claude/settings.local.json` failure hooks, while Codex, Factory Droid, and `pi` now use the shared wrapper surface.
Files: `support/scripts/llm_wiki_agent_failure_capture.py`, `support/scripts/run_llm_wiki_agent.ps1`, `support/scripts/run_llm_wiki_agent.sh`, `support/scripts/run_llm_wiki_agent.cmd`, `support/scripts/llm_wiki_memory_runtime.py`, `installers/install_obsidian_agent_memory.py`, `install.ps1`, `install.sh`, `docker-compose.yml`, `docker/entrypoint.sh`, `.docker/vault/.llm-wiki/config.json`, `README.md`, `tests/test_llm_wiki_agent_failure_capture.py`, `tests/test_llm_wiki_memory_runtime.py`, `tests/test_install_obsidian_agent_memory.py`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the repeated-failure collector and Claude native hook path were already in place, but Codex, Factory Droid, and `pi` still had no real capture surface. Factory's documented CLI hooks do not expose a failure-specific event equivalent to Claude's `PostToolUseFailure` or `StopFailure`, so Droid needed the same process-level wrapper path as Codex and `pi`.
Verified: [x] `python -m py_compile support\scripts\llm_wiki_agent_failure_capture.py support\scripts\llm_wiki_memory_runtime.py installers\install_obsidian_agent_memory.py tests\test_llm_wiki_agent_failure_capture.py tests\test_llm_wiki_memory_runtime.py tests\test_install_obsidian_agent_memory.py`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_agent_failure_capture.py"`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_memory_runtime.py"`; [x] `python -m unittest discover -s tests -p "test_install_obsidian_agent_memory.py"`; [x] `python -m unittest discover -s tests -p "test_*.py"`; [x] `powershell -NoProfile -ExecutionPolicy Bypass -File .\support\scripts\run_llm_wiki_agent.ps1 -Agent claude -Arguments '--help'`; [x] `powershell -NoProfile -ExecutionPolicy Bypass -File .\support\scripts\run_llm_wiki_agent.ps1 -Agent codex -Arguments '--help'`; [x] `cmd /d /s /c "support\scripts\run_llm_wiki_agent.cmd --agent pi -- -h"`; [x] `bash -n ./support/scripts/run_llm_wiki_agent.sh`; [x] bash wrapper smoke with a temporary fake `droid` executable on `PATH`.
Next: keep the wrapper default surface aligned across docs and installer outputs, and only add native non-Claude hook wiring later if those CLIs expose a stable failure-event surface that actually matches the packet contract.

2026-04-12T18:53:44-06:00 - Automatic Claude failure-hook wiring landed
Changed: added `support/scripts/llm_wiki_failure_hook.py` to the installed asset surface and taught `support/scripts/llm_wiki_memory_runtime.py` to merge machine-local Claude hooks into `.claude/settings.local.json`. The generated hook uses PowerShell explicitly on Windows and a quoted POSIX command elsewhere, then records `PostToolUseFailure` and `StopFailure` events into the repeated-failure collector without clobbering unrelated local hooks.
Files: `support/scripts/llm_wiki_memory_runtime.py`, `support/scripts/llm_wiki_failure_hook.py`, `installers/install_obsidian_agent_memory.py`, `.docker/vault/.llm-wiki/config.json`, `.gitignore`, `tests/test_llm_wiki_memory_runtime.py`, `tests/test_install_obsidian_agent_memory.py`, `tests/test_llm_wiki_failure_hook.py`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the failure collector and EvoSkill promotion path already existed, but there was still no real normal-run emitter. That left the auto-improvement loop dependent on manual CLI calls instead of actual Claude failure events.
Verified: [x] `python -m py_compile support\scripts\llm_wiki_memory_runtime.py support\scripts\llm_wiki_failure_hook.py installers\install_obsidian_agent_memory.py tests\test_llm_wiki_memory_runtime.py tests\test_install_obsidian_agent_memory.py tests\test_llm_wiki_failure_hook.py tests\test_llm_wiki_failure_collector.py`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_memory_runtime.py"`; [x] `python -m unittest discover -s tests -p "test_install_obsidian_agent_memory.py"`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_failure_hook.py"`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_failure_collector.py"`; [x] `python -m unittest discover -s tests -p "test_*.py"`.
Next: add equivalent emitters for any non-Claude launcher surfaces only if those runtimes need the same automatic failure capture path.

2026-04-12T18:55:00-06:00 - Repeated-failure promotion into EvoSkill landed
Changed: added `support/scripts/llm_wiki_failure_collector.py`, a local-first failure collector/promoter that records runtime failures under `.llm-wiki/skill-pipeline/failures/{events,clusters,benchmarks}` and promotes repeated clusters into `skill_evolve`. Installer bootstrap, sample config, and runtime health verification now seed and expect the new failure directories and promotion thresholds.
Files: `support/scripts/llm_wiki_failure_collector.py`, `support/scripts/llm_wiki_memory_runtime.py`, `installers/install_obsidian_agent_memory.py`, `.docker/vault/.llm-wiki/config.json`, `tests/test_llm_wiki_failure_collector.py`, `tests/test_install_obsidian_agent_memory.py`, `tests/test_llm_wiki_memory_runtime.py`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the EvoSkill frontier existed, but recurrent runtime failures still had no local-first collection plane or thresholded promotion path; every future caller would have had to reinvent clustering and promotion logic.
Verified: [x] `python -m py_compile` on the touched scripts and tests; [x] `python -m unittest discover -s tests -p "test_llm_wiki_failure_collector.py"`; [x] `python -m unittest discover -s tests -p "test_install_obsidian_agent_memory.py"`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_memory_runtime.py"`; [x] `python -m unittest discover -s tests -p "test_llm_wiki_skill_mcp.py"`.
Next: add a thin wrapper or hook surface that emits failure events automatically from real agent runs so the collector does not rely on manual CLI calls.

2026-04-12T18:33:00-06:00 - EvoSkill auto-improvement loop landed in the repo skill plane
Changed: extended `support/scripts/llm_wiki_skill_mcp.py` with an EvoSkill-style evolution path that records proposals, surrogate verifier reviews, evolution runs, and a maintained frontier, then exposed that flow through both MCP tools and the cross-shell Python CLI. Bootstrapping now seeds the new `.llm-wiki/skill-pipeline/{proposals,surrogate-reviews,evolution-runs}` paths plus `frontier.json`.
Files: `support/scripts/llm_wiki_skill_mcp.py`, `installers/install_obsidian_agent_memory.py`, `tests/test_llm_wiki_skill_mcp.py`, `tests/test_install_obsidian_agent_memory.py`, `.factory/memories.md`, `kade/KADE.md`, and the canonical Obsidian system map note.
Why: the repo already had a strong reflect/validate/curate skill pipeline, but it did not yet model EvoSkill’s create-vs-edit proposals, verifier separation, or frontier tracking for skill auto-improvement.
Verified: [x] `python -m unittest discover -s tests -p "test_*.py"`; [x] `python -m py_compile` on the touched runtime, installer, and tests.
Next: wire a benchmark-driving caller onto `skill_evolve` so recurrent task failures can feed the frontier automatically instead of only through manual invocations.

2026-04-12T14:40:00-06:00 - Shared runtime and gateway safety pass
Changed: replaced duplicated setup and health helper implementations with the shared `scripts/llm_wiki_memory_runtime.py` control path, added CMD wrappers, pinned managed `pk-qmd` installs to commit `ef26cb62bb8132bc3a851b23f450af8e382e4c4e`, switched container GitHub auth from broad URL rewriting to `.netrc`, and made the gateway reject non-loopback host exposure without auth unless explicitly overridden.
Files: `support/scripts/llm_wiki_memory_runtime.py`, setup/check wrappers, `installers/install_obsidian_agent_memory.py`, `installers/install_g_kade_workspace.py`, `docker/mcp_http_proxy.mjs`, `docker/entrypoint.sh`, `docker-compose.yml`, CI, and the contract/known-issues docs.
Why: the shell families had drifted, the gateway safety rule lived mostly in docs, and bootstrap/runtime behavior was not reproducible enough across platforms.
Verified: [ ] focused tests; [ ] cross-platform CI matrix; [ ] docker-local gateway path.
Next: keep the root release installers aligned with the shared runtime contract even though they must stay standalone bootstrap assets.

2026-04-12T13:25:00-06:00 - Official Kade-HQ memory base and launcher split aligned
Changed: promoted the official durable memory base to the `Kade-HQ` Obsidian vault, aligned repo mirrors to the `kade-hq` vault identity, and clarified that `kade-hq`, `g-kade`, and `gstack` all install as launcher surfaces while `g-kade` remains only the bridge skill.
Files: `AGENTS.md`, `.factory/memories.md`, `kade/AGENTS.md`, `kade/KADE.md`, installer tests, and the official Obsidian system map note.
Why: the repo contract still pointed at the old vault and still implied the launcher surface was only `g-kade` plus `gstack`, which no longer matched the intended system.
Verified: [x] grounded retrieval with `pk-qmd`; [x] repaired the installer/test regression; [ ] reran focused tests after the mirror update.
Next: keep the shell setup helpers in parity with the corrected PowerShell bootstrap and update any legacy Obsidian mirror note to point at the official `Kade-HQ` vault.

2026-04-11T18:41:02-06:00 - Intentional memory alignment
Changed: refreshed the durable memory contract to reflect the repo-owned `deps/pk-skills1` runtime, the loopback-only Docker gateway, and the local-vs-hosted security split.
Files: `AGENTS.md`, `.factory/memories.md`, `kade/AGENTS.md`, `kade/KADE.md`, Obsidian `llm_wiki_prompt_packet System Map.md`, and the vault log.
Why: repo and Obsidian memory were stale relative to the implemented bootstrap, Docker, and gateway behavior.
Verified: [x] inspected repo memory files; [x] attempted qmd retrieval for grounding; [x] aligned repo memory mirrors to the same contract.
Next: keep the top-level installer wrappers and hosted edge docs aligned with the same first-class gateway contract.

2026-04-11T19:18:00-06:00 - HUMAN profile seeding corrected
Changed: pointed the g-kade workspace installer at the packaged Kade-HQ Layer 1 profile, preserved real existing `~/.kade/HUMAN.md` files, and upgraded only the exact legacy stub.
Files: `installers/install_g_kade_workspace.py`, `tests/test_install_g_kade_workspace.py`, `AGENTS.md`, `.factory/memories.md`, `kade/KADE.md`, Obsidian `llm_wiki_prompt_packet System Map.md`, and `C:\Users\prest\.kade\HUMAN.md`.
Why: the installer was still generating the generic HUMAN stub instead of the Kade-HQ profile and needed an explicit preserve-existing rule.
Verified: [x] `python tests\test_install_g_kade_workspace.py`; [x] refreshed the live `~/.kade/HUMAN.md` only because it matched the exact legacy stub.
Next: keep future install and migration paths on the same rule: seed or upgrade the legacy stub, but preserve any real existing Layer 1 profile.
