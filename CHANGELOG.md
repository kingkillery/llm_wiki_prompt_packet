# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **`--wire-repo` / `-WireRepo` health check now propagates exit code by default.** Previously, a failing health check after `--wire-repo` installation printed a warning but always exited zero. The installer now exits with the health check's non-zero exit code so chained commands (`install.sh --wire-repo && next_thing`) correctly honor failure. Set `LLM_WIKI_HEALTH_CHECK_NONFATAL=1` to restore the old warn-only behavior. This is a **potential breaking change** for automation scripts that relied on the installer always succeeding. ([`install.sh`](install.sh), [`install.ps1`](install.ps1))

### Added

- **`wire_global_claude.py` heading-fallback fix.** When updating an older LLM Wiki section that lacks the `<!-- /llm-wiki -->` end-marker, section replacement now terminates on ANY markdown heading (`# ` or `## `), not just `## `. This prevents data loss of subsequent top-level headings in hand-edited `~/.claude/CLAUDE.md` files. ([`installers/wire_global_claude.py`](installers/wire_global_claude.py))
- **Regression tests for `wire_global_claude.py`.** Six permutation fixtures covering fresh insert, end-marker update, heading-fallback data-loss guard, append-to-existing, command copy idempotency, and dry-run zero-side-effects. ([`installers/tests/test_wire_global_claude.py`](installers/tests/test_wire_global_claude.py))
- **Updated agent-facing skill docs to teach `--wire-repo`.** The `g-kade` and `pokemon-benchmark` home skills now present `--wire-repo` as the primary one-command bootstrap path, replacing the legacy `llm_wiki_packet.ps1 init` flow. ([`skills/home/g-kade/SKILL.md`](skills/home/g-kade/SKILL.md), [`skills/home/pokemon-benchmark/SKILL.md`](skills/home/pokemon-benchmark/SKILL.md))
- **Optional Hugging Face integrations for local installs.** Added installer preflight detection for `hf`, optional `HF_TOKEN`-gated Hugging Face Hub MCP wiring into Claude Code and Factory, and an opt-in local TEI (`text-embeddings-inference`) docker service for embeddings. ([`installers/preflight.py`](installers/preflight.py), [`support/scripts/llm_wiki_memory_runtime.py`](support/scripts/llm_wiki_memory_runtime.py), [`docker-compose.yml`](docker-compose.yml), [`README.md`](README.md))
- **Regression tests for Hugging Face MCP wiring.** Runtime tests now verify both the skip path when `HF_TOKEN` is absent and the non-secret-persisting Claude/Factory wiring path when it is present. ([`tests/test_llm_wiki_memory_runtime.py`](tests/test_llm_wiki_memory_runtime.py))
