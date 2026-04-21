# Technology Stack

**Analysis Date:** 2026-04-12

## Languages

**Primary:**

- Python 3 - Installer and scaffold logic in `installers/install_obsidian_agent_memory.py`, `installers/install_g_kade_workspace.py`, release asset generation in `scripts/build_release_bootstraps.py`, and the local skill server in `support/scripts/llm_wiki_skill_mcp.py`
- PowerShell - Windows bootstrap and setup flows in `install.ps1`, `installers/*.ps1`, `support/scripts/setup_llm_wiki_memory.ps1`, and the BRV/GitVizz wrappers under `support/scripts/*.ps1`
- Bash - Unix and container bootstrap flows in `install.sh`, `installers/*.sh`, `support/scripts/setup_llm_wiki_memory.sh`, and `docker/entrypoint.sh`

**Secondary:**

- JavaScript / ESM - Local gateway and edge helpers in `docker/mcp_http_proxy.mjs`, `deploy/cloudflare/mcp-edge-worker.js`, and `tests/test_agent_api_gateway.mjs`
- Markdown / JSON / YAML - Prompt assets in `prompts/*.md`, plugin metadata in `plugins/llm-wiki-organizer/.codex-plugin/plugin.json`, and deployment/workflow config in `docker-compose.yml` and `.github/workflows/release-installers.yml`

## Runtime

**Environment:**

- Python 3 on PATH - Required by the installers and most helper scripts; `docker/Dockerfile` installs `python3`
- Node.js - Required for packet-local npm installs, the local HTTP gateway, and the embed runner; the container image is `node:22-bookworm-slim` in `docker/Dockerfile`
- Git - Required for git-based `pk-qmd` and optional GitVizz acquisition in `support/scripts/setup_llm_wiki_memory.sh` and `docker/entrypoint.sh`

**Package Manager:**

- npm - Root dependency manifest in `package.json` and packet-local tool manifest in `.llm-wiki/package.json`
- Lockfile: Not tracked in this repo; installs are intentionally packet-local or managed-tool installs rather than committed workspace dependencies

## Frameworks

**Core:**

- Python stdlib CLI style - `argparse`, `pathlib`, and filesystem-first orchestration across `installers/*.py` and `support/scripts/llm_wiki_skill_mcp.py`
- Node stdlib HTTP/runtime - `http`, `child_process`, and `node:test` in `docker/mcp_http_proxy.mjs` and `tests/test_agent_api_gateway.mjs`
- Cloudflare Worker runtime - Remote MCP edge proxy in `deploy/cloudflare/mcp-edge-worker.js`

**Testing:**

- `unittest` - Python tests in `tests/test_install_obsidian_agent_memory.py`, `tests/test_install_g_kade_workspace.py`, and `tests/test_llm_wiki_skill_mcp.py`
- Node built-in `node:test` - Gateway integration test in `tests/test_agent_api_gateway.mjs`

**Build/Dev:**

- Docker Compose - Local and hosted stack assembly in `docker-compose.yml`, `docker-compose.local-qmd.yml`, and `deploy/gcp/compose.yaml`
- GitHub Actions - Release-asset generation in `.github/workflows/release-installers.yml`

## Key Dependencies

**Critical:**

- `@kingkillery/pk-qmd` from GitHub `main` - Root dependency in `package.json`; this is the primary retrieval and MCP plane
- `byterover-cli` - Packet-local dependency in `.llm-wiki/package.json`; this is the durable memory plane
- `deps/pk-skills1` submodule - Declared in `.gitmodules`; this is the richer repo-owned harness/runtime source expected by the packet contract

**Infrastructure:**

- Mongo 5.0 - Optional GitVizz backend storage in `docker-compose.yml`
- Phoenix (`arizephoenix/phoenix`) - Optional GitVizz telemetry surface in `docker-compose.yml`

## Configuration

**Environment:**

- Environment variables drive nearly all bootstrap behavior: `LLM_WIKI_INSTALL_SCOPE`, `LLM_WIKI_QMD_*`, `LLM_WIKI_GITVIZZ_*`, `LLM_WIKI_AGENT_API_TOKEN`, `BYTEROVER_API_KEY`, `GH_TOKEN`, and `GITHUB_TOKEN` are used across `install.ps1`, `install.sh`, `support/scripts/setup_llm_wiki_memory.sh`, and `docker-compose.yml`
- Generated workspace config is expected at `.llm-wiki/config.json`; the source repo only tracks `.llm-wiki/package.json` and writes the config during installation

**Build:**

- Deployment and runtime wiring live in `docker-compose.yml`, `docker-compose.local-qmd.yml`, `deploy/gcp/compose.yaml`, and `.github/workflows/release-installers.yml`

## Platform Requirements

**Development:**

- Windows, macOS, and Linux are all supported through paired `*.ps1` and `*.sh` entrypoints
- Optional Docker, Cloudflare/Wrangler, and GCP tooling are only needed for the hosted surfaces under `docker/` and `deploy/`

**Production:**

- Local-first runtime is a loopback gateway on `127.0.0.1:8181` exposed by `docker-compose.yml`
- Hosted runtime is designed around a long-lived GCP VM plus an optional Cloudflare Worker edge under `deploy/gcp/` and `deploy/cloudflare/`

---

_Stack analysis: 2026-04-12_
_Update after major dependency or deployment changes_
