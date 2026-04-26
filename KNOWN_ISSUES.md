# Known Issues

## Open Operational Risks

- [#4](https://github.com/kingkillery/llm_wiki_prompt_packet/issues/4) The local gateway is still a single Node process. It is intentionally thin, but high-volume or public traffic should terminate at a real reverse proxy or edge layer instead of this process.
- [#5](https://github.com/kingkillery/llm_wiki_prompt_packet/issues/5) GitVizz still depends on an external checkout. The packet now records the managed checkout path and repo source explicitly, but GitVizz is not yet vendored like `deps/pk-skills1`.
- [#6](https://github.com/kingkillery/llm_wiki_prompt_packet/issues/6) Root release installers remain separate shell and PowerShell entrypoints because they must bootstrap the repo before any shared repo file exists.
- [#7](https://github.com/kingkillery/llm_wiki_prompt_packet/issues/7) BRV (`brv`) ships in the stack but requires an explicit `brv providers connect <provider>` step after install before `brv query` and `brv curate` work. `brv status` is always available. The default configured provider is `openrouter` with `google/gemini-3.1-flash-lite-preview`. Run `brv providers connect byterover` for the free built-in path or `brv providers connect openrouter` for BYOK.
- [#8](https://github.com/kingkillery/llm_wiki_prompt_packet/issues/8) `support/scripts/` is the source tree for all Python and shell scripts; `scripts/` is the installer-deployed surface in activated project vaults. When reading source code or tests, look in `support/scripts/`. When invoking installed helpers from a configured vault, use `scripts/`.

## Deferred Pipeline Artifacts

- [#9](https://github.com/kingkillery/llm_wiki_prompt_packet/issues/9) `proposal-pokemon-benchmark-verifier-failure-38e961fa` (created 2026-04-13): auto-promoted from a 3-session failure cluster but blocked at validation (missing `applies_to`, `fast_path`, and `outcome`). The root cause — the Pokemon session report not being written to `/root/Desktop/pokemon_session_report.json` inside the container — is a benchmark environment issue, not a stable reusable shortcut. Deferred pending a clean re-run that produces a complete session report. Retire if no re-run occurs within 30 days.

## Tracking Rules

- Add confirmed source-level bugs here instead of hiding them only in memory notes.
- Mirror durable contract changes into `SYSTEM_CONTRACT.md`, `.factory/memories.md`, `kade/KADE.md`, and the official Obsidian system map note.
- Remove entries when a fix ships and verification is recorded in tests or CI.
