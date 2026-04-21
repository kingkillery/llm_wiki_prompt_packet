# Codebase Concerns

**Analysis Date:** 2026-04-12  
**Refresh Date:** 2026-04-12

## Resolved In This Pass

- Setup and health helper drift:
  - `scripts/llm_wiki_memory_runtime.py` now owns shared setup and verification logic.
  - Bash, PowerShell, and CMD surfaces are thin wrappers.

- Contract and bug-backlog sprawl:
  - `SYSTEM_CONTRACT.md` is now the canonical packet contract document.
  - `KNOWN_ISSUES.md` is now the explicit operational backlog.
  - `.llm-wiki/config.json` now carries the pinned `pk-qmd` ref plus the contract/backlog paths.

- Gateway safety:
  - `docker/mcp_http_proxy.mjs` now rejects non-loopback host exposure without auth unless `LLM_WIKI_AGENT_API_UNSAFE_NO_AUTH=1` is set explicitly.
  - Docker now passes the host bind host into the container so loopback-only host exposure remains allowed.

- Broad GitHub token rewriting:
  - `docker/entrypoint.sh` now writes a scoped `.netrc` instead of adding global tokenized `git config url.*.insteadOf` rules.

- Reproducibility:
  - `pk-qmd` is pinned to commit `ef26cb62bb8132bc3a851b23f450af8e382e4c4e` in repo manifests and installed workspace config.

- Runtime/bootstrap verification:
  - CI now runs Python tests, Node tests, and cross-platform wrapper smoke checks on Ubuntu, Windows, and macOS.
  - `install_g_kade_workspace.py` now attempts to initialize `deps/pk-skills1` when the declared submodule is missing.

## Remaining Open Concerns

- Root release installers still exist as separate shell and PowerShell assets:
  - This is intentional because they must bootstrap the repo before any shared repo file exists.
  - The risk is now bounded by CI wrapper smoke coverage.

- GitVizz is still an external checkout rather than a vendored runtime:
  - The packet now records the checkout path and repo source explicitly, but GitVizz still depends on an external repo acquisition step.

- The local gateway remains a single Node process:
  - It is acceptable for loopback-local use, but public or higher-throughput deployments should terminate at a real edge or reverse proxy.

## Verification Targets

- `python -m unittest discover -s tests -p "test_*.py"`
- `node --test tests/test_agent_api_gateway.mjs`
- GitHub Actions matrix in `.github/workflows/ci.yml`
