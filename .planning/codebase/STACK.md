# Stack

## Languages And Formats

- Python:
  installers, release asset generation, skill MCP server
- PowerShell:
  Windows-first bootstrap, setup, health, BRV and GitVizz helpers
- Bash:
  Unix/macOS bootstrap, setup, health, Docker and GCP scripts
- JavaScript and MJS:
  qmd embed runner, Docker MCP HTTP proxy, Cloudflare Worker
- JSON, TOML, YAML, Markdown:
  config, registry, plugin metadata, prompts, docs, vault content

## Runtime Dependencies

- Required for the main bootstrap path:
  - Python
  - Node/npm for packet-local `pk-qmd` install
- Expected external tools:
  - `pk-qmd`
  - `brv`
  - GitVizz if that surface is enabled
- Optional tooling:
  - Docker and docker compose
  - `gcloud`
  - `wrangler`

## Persistent State Shapes

- Source repo state:
  tracked source files under `installers/`, `support/`, `docker/`, `deploy/`, `plugins/`, `prompts/`, `tests/`
- Installed workspace state:
  - `.llm-wiki/config.json`
  - `.llm-wiki/skills-registry.json`
  - `.llm-wiki/skill-pipeline/briefs`
  - `.llm-wiki/skill-pipeline/deltas`
  - `.llm-wiki/skill-pipeline/validations`
  - `.llm-wiki/skill-pipeline/packets`
  - `.brv/`
  - `wiki/skills/active`, `wiki/skills/feedback`, `wiki/skills/retired`
- User-global state:
  MCP config files in `~/.claude`, `~/.codex`, and `~/.factory`

## External System Contract

- `pk-qmd`:
  primary retrieval plane and MCP server
- `brv`:
  durable memory plane
- GitVizz:
  graph and web surface
- Obsidian:
  target vault / durable markdown workspace
- Codex plugin bundle:
  packaging surface for `llm-wiki-organizer`

## Repo Character

This is an integration-heavy repo, not an application with one server entrypoint. The main value is in installation flow, config synthesis, and maintaining a stable contract across multiple tools and agent clients.
