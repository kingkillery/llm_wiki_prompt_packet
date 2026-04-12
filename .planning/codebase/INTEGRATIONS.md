# Integrations

## pk-qmd

Files:

- `package.json`
- `support/scripts/setup_llm_wiki_memory.ps1`
- `support/scripts/setup_llm_wiki_memory.sh`
- `docker/entrypoint.sh`

Connection:

- root package depends on `@kingkillery/pk-qmd`
- setup helpers prefer packet-local install under `.llm-wiki/node_modules`
- helpers wire `pk-qmd` into agent MCP config
- Docker serve mode runs `pk-qmd mcp --http`

Why it matters:

This is the primary retrieval plane and the main MCP surface expected by agent clients.

## Byterover / brv

Files:

- `support/scripts/setup_llm_wiki_memory.ps1`
- `support/scripts/setup_llm_wiki_memory.sh`
- `support/scripts/brv_query.*`
- `support/scripts/brv_curate.*`
- `support/scripts/brv_benchmark.*`

Connection:

- setup verifies or installs `brv`
- workspace BRV state lives in `.brv/`
- helper scripts assume BRV is the durable memory layer

Why it matters:

This is the curated memory plane, separate from source-grounded retrieval.

## GitVizz

Files:

- `support/scripts/launch_gitvizz.*`
- `support/scripts/gitvizz_api.*`
- `support/scripts/setup_llm_wiki_memory.ps1`
- `support/scripts/setup_llm_wiki_memory.sh`

Connection:

- config carries frontend and backend URLs
- setup can verify or start GitVizz when a repo path is configured
- health checks can enforce reachability when GitVizz is managed

Why it matters:

GitVizz is the graph and web surface, but it is optional unless the workspace is configured to manage it.

## Obsidian

Files:

- installers
- prompt assets
- installed `wiki/`, `raw/`, `templates/`, and `scripts/` tree

Connection:

- the vault is the durable markdown workspace
- the packet installs source, structure, and helper entrypoints into that vault

Why it matters:

The vault is where the packet becomes real and where durable memory and skill outputs are stored.

## User Agent Clients

Files:

- `support/scripts/setup_llm_wiki_memory.ps1`
- `support/scripts/setup_llm_wiki_memory.sh`

Connection:

- setup patches:
  - `~/.claude/settings.json`
  - `~/.codex/config.toml`
  - `~/.factory/mcp.json`

Why it matters:

This is how Claude, Codex, and Factory discover the `pk-qmd` and `llm-wiki-skills` servers.

## Codex Plugin Bundle

Files:

- `plugins/llm-wiki-organizer/.codex-plugin/plugin.json`
- `plugins/llm-wiki-organizer/skills/*`
- `plugins/llm-wiki-organizer/assets/*`

Connection:

- packages the organizer skill as a Codex plugin surface
- not part of the default installer happy path

Why it matters:

This is a packaging and distribution surface, not the core bootstrap engine.

## Hosted Surfaces

Files:

- `docker/*`
- `docker-compose*.yml`
- `deploy/gcp/*`
- `deploy/cloudflare/*`

Connection:

- Docker packages the bootstrap and serves remote MCP
- GCP deploy provisions a VM and runs the compose stack
- Cloudflare provides a secure public edge in front of the VM

Why it matters:

These files matter only if the system is being exposed remotely. They are not required for the normal local vault bootstrap.
