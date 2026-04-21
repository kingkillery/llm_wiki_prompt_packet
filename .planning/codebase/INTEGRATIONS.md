# External Integrations

**Analysis Date:** 2026-04-12

## APIs & External Services

**Primary Retrieval Plane:**

- `pk-qmd` - Repo-specific retrieval, collection management, embedding, and MCP serving
  - SDK/Client: CLI and MCP process invoked from `package.json`, `support/scripts/setup_llm_wiki_memory.sh`, `support/scripts/setup_llm_wiki_memory.ps1`, and `docker/entrypoint.sh`
  - Auth: Optional `GH_TOKEN` / `GITHUB_TOKEN` for private fetches; runtime MCP auth is handled separately at the gateway layer
  - Endpoints used: Local MCP endpoint defaults to `http://localhost:8181/mcp`; container serve mode starts `pk-qmd mcp --http`

**Durable Memory Plane:**

- `byterover-cli` / `brv` - Query, curate, benchmark, and workspace memory initialization
  - SDK/Client: CLI wrappers in `support/scripts/brv_query.sh`, `support/scripts/brv_curate.ps1`, and `support/scripts/brv_benchmark.py`
  - Auth: `BYTEROVER_API_KEY` or `brv login`
  - Integration method: CLI plus the gateway routes `/memory/status`, `/memory/query`, and `/memory/curate`

**Graph / Web Surface:**

- GitVizz - Optional frontend/backend graph service
  - Integration method: Managed checkout plus Docker Compose, or external frontend/backend URLs
  - Auth: Local mode relies on loopback/network placement; hosted examples add Cloudflare Access in `deploy/cloudflare/mcp-edge-worker.js`
  - Rate limits: Not modeled in source; operational behavior depends on the deployed GitVizz runtime

## Data Storage

**Databases:**

- MongoDB 5.0 - Optional GitVizz backend store in `docker-compose.yml`
  - Connection: `mongodb://gitvizz-mongo:27017`
  - Client: External GitVizz backend container

**File Storage:**

- Local filesystem / Obsidian vault - Packet output and skill artifacts live under installed `wiki/`, `raw/`, `.llm-wiki/`, and `.brv/`
  - Source files: `installers/install_obsidian_agent_memory.py`, `support/scripts/llm_wiki_skill_mcp.py`
  - Mounted paths: `/workspace` in `docker-compose.yml`

**Telemetry / Observability Storage:**

- Phoenix - Optional GitVizz tracing surface in `docker-compose.yml`
  - Volumes: `gitvizz_phoenix`, `gitvizz_storage`

## Authentication & Identity

**Gateway Auth Provider:**

- Packet HTTP gateway - Optional bearer-auth guard
  - Implementation: `LLM_WIKI_AGENT_API_TOKEN` checked in `docker/mcp_http_proxy.mjs`
  - Token storage: environment variable only
  - Session management: stateless bearer check per request

**Edge Auth Integrations:**

- Cloudflare Access service token forwarding
  - Credentials: `ACCESS_CLIENT_ID`, `ACCESS_CLIENT_SECRET`, and optional `EDGE_API_TOKEN`
  - Implementation: `deploy/cloudflare/mcp-edge-worker.js`

## Monitoring & Observability

**Health Checks:**

- Local gateway health endpoint in `docker/mcp_http_proxy.mjs`
  - Path: `/healthz`
  - Purpose: exposes route availability and memory/QMD wiring state

**Release Validation:**

- GitHub Actions release verification in `.github/workflows/release-installers.yml`
  - Scope: verifies generated installer formatting and syntax

**Logs:**

- stdout/stderr only for most scripts
  - Integration: shell, PowerShell, and Python summary output plus `console.error` in `docker/mcp_http_proxy.mjs`

## CI/CD & Deployment

**Hosting:**

- Docker Compose - Local or VM-hosted stack in `docker-compose.yml` and `docker-compose.local-qmd.yml`
  - Deployment: manual `docker compose up --build` or via the GCP scripts
  - Environment vars: `LLM_WIKI_*`, provider keys, and GitHub tokens

**CI Pipeline:**

- GitHub Actions release asset job in `.github/workflows/release-installers.yml`
  - Workflows: build release-specific `install.ps1` and `install.sh`, then upload assets to the GitHub release

**Remote Deployment Surfaces:**

- GCP Compute Engine in `deploy/gcp/deploy_compute_engine.sh` and `.ps1`
- Cloudflare Worker edge in `deploy/cloudflare/mcp-edge-worker.js`

## Environment Configuration

**Development:**

- Required env vars depend on the mode: `LLM_WIKI_INSTALL_SCOPE`, `LLM_WIKI_QMD_*`, `LLM_WIKI_GITVIZZ_*`, and optional provider keys
- Secrets location: environment variables; no checked-in secret files
- Mock/stub services: local temp scripts and in-process HTTP servers are used in `tests/test_agent_api_gateway.mjs`

**Staging:**

- Not explicitly modeled as a separate environment in tracked source

**Production:**

- Hosted docs expect auth to be added at the edge or gateway level rather than exposing raw loopback defaults
- GCP and Cloudflare deployment scaffolds live under `deploy/gcp/` and `deploy/cloudflare/`

## Webhooks & Callbacks

**Incoming:**

- None handled by the packet application code itself
- The repo documents GitHub callback URLs for GitVizz setup in `README.md`, but the callback handling lives in the external GitVizz runtime, not this repo

**Outgoing:**

- GitHub zip download for the packet in `install.ps1` and `install.sh`
- Git clone / npm git-based fetches for `pk-qmd` and GitVizz in `support/scripts/setup_llm_wiki_memory.sh`, `support/scripts/setup_llm_wiki_memory.ps1`, and `docker/entrypoint.sh`

---

_Integration audit: 2026-04-12_
_Update when external tools, auth flows, or deploy surfaces change_
