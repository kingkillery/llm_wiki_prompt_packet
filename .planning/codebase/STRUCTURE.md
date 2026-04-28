# Codebase Structure

**Analysis Date:** 2026-04-12

## Directory Layout

```text
llm_wiki_prompt_packet/
|-- installers/               # Python and shell bootstrap entrypoints
|-- support/                  # Shared docs and runtime helper scripts
|-- prompts/                  # Prompt and workflow source assets copied into targets
|-- skills/home/              # Thin packet-owned launcher wrappers
|-- plugins/                  # Codex plugin bundle surface
|-- docker/                   # Container entrypoint and HTTP gateway
|-- deploy/                   # GCP and Cloudflare hosted surfaces
|-- tests/                    # Python and Node tests
|-- kade/                     # Repo-local KADE overlay
|-- .planning/codebase/       # Generated codebase map documents
|-- .llm-wiki/                # Packet-local tool manifest for this checkout
|-- package.json              # Root packet dependency manifest
|-- install.ps1               # Hosted Windows installer wrapper
|-- install.sh                # Hosted Unix installer wrapper
`-- README.md                 # Product and operational documentation
```

## Directory Purposes

**installers/:**

- Purpose: Own the authoritative bootstrap and workspace-scaffolding logic
- Contains: `install_obsidian_agent_memory.py`, `install_g_kade_workspace.py`, paired `*.ps1` and `*.sh` installers, and packet asset stubs under `installers/assets/`
- Key files: `installers/install_obsidian_agent_memory.py`, `installers/install_g_kade_workspace.py`
- Subdirectories: `installers/assets/vault/` for files copied into installed workspaces

**support/:**

- Purpose: Hold the reusable runtime helpers and supporting docs
- Contains: `support/scripts/*.ps1`, `support/scripts/*.sh`, `support/scripts/*.py`, plus `LLM_WIKI_MEMORY.md` and `SKILL_CREATION_AT_EXPERT_LEVEL.md`
- Key files: `support/scripts/setup_llm_wiki_memory.sh`, `support/scripts/setup_llm_wiki_memory.ps1`, `support/scripts/llm_wiki_skill_mcp.py`, `support/scripts/llm_wiki_memory_controller.py`, `support/scripts/llm_wiki_packet.py`, `support/scripts/dashboard_server.py`
- Subdirectories: `support/scripts/` is the main executable surface

**prompts/:**

- Purpose: Source-of-truth prompt payloads for the installed agent targets
- Contains: numbered markdown prompt/workflow files
- Key files: `prompts/01-AGENTS.md`, `prompts/02-CLAUDE.md`, `prompts/03-codex-skill-SKILL.md`
- Subdirectories: none; flat numbered prompt set

**skills/home/:**

- Purpose: Provide the packet-owned home-wrapper skills that can be copied into `~/.agents`, `~/.codex`, and `~/.claude`
- Contains: `g-kade`, `gstack`, and `kade-hq` wrapper directories
- Key files: `skills/home/g-kade/SKILL.md`, `skills/home/gstack/SKILL.md`, `skills/home/kade-hq/SKILL.md`
- Subdirectories: one folder per wrapper skill, each with `agents/openai.yaml`

**plugins/:**

- Purpose: Package the Codex-facing plugin surface
- Contains: `plugins/llm-wiki-organizer/.codex-plugin/plugin.json`, assets, and skill payloads
- Key files: `plugins/llm-wiki-organizer/.codex-plugin/plugin.json`
- Subdirectories: `.codex-plugin/`, `assets/`, `skills/`

**docker/ and deploy/:**

- Purpose: Host the local gateway and remote deployment scaffolds
- Contains: container image files in `docker/`, plus GCP and Cloudflare deploy assets in `deploy/gcp/` and `deploy/cloudflare/`
- Key files: `docker/mcp_http_proxy.mjs`, `docker/entrypoint.sh`, `deploy/cloudflare/mcp-edge-worker.js`, `deploy/gcp/deploy_compute_engine.sh`
- Subdirectories: `deploy/cloudflare/`, `deploy/gcp/`

**tests/:**

- Purpose: Exercise installer, workspace bootstrap, skill-store, and gateway behavior
- Contains: Python `test_*.py` modules and one Node `test_*.mjs` file
- Key files: `tests/test_install_obsidian_agent_memory.py`, `tests/test_install_g_kade_workspace.py`, `tests/test_llm_wiki_skill_mcp.py`, `tests/test_agent_api_gateway.mjs`
- Subdirectories: none

## Key File Locations

**Entry Points:**

- `install.ps1` - Hosted Windows installer wrapper
- `install.sh` - Hosted Unix installer wrapper
- `installers/install_obsidian_agent_memory.py` - Standard packet installer
- `installers/install_g_kade_workspace.py` - Repo-local `g-kade` workspace installer
- `docker/entrypoint.sh` - Container bootstrap entrypoint

**Configuration:**

- `package.json` - Root packet dependency manifest
- `.llm-wiki/package.json` - Packet-local managed-tool manifest
- `docker-compose.yml` - Main local/hosted compose stack
- `.gitmodules` - Declares `deps/pk-skills1` as the richer runtime submodule

**Core Logic:**

- `installers/` - File-copy, workspace scaffolding, config generation
- `support/scripts/` - Tool resolution, MCP patching, BRV/QMD/GitVizz runtime helpers
- `docker/mcp_http_proxy.mjs` - Unified HTTP surface for `/mcp`, `/graph/*`, and `/memory/*`

**Testing:**

- `tests/` - Python `unittest` modules and the Node gateway integration test

**Documentation:**

- `README.md` - Main usage and deployment guide
- `AGENTS.md`, `kade/AGENTS.md`, `kade/KADE.md`, `.factory/memories.md` - Working contract and memory overlays

## Naming Conventions

**Files:**

- `install_*` for installer entrypoints, for example `install_obsidian_agent_memory.py`
- `setup_*` for bootstrap helpers, for example `support/scripts/setup_llm_wiki_memory.sh`
- `check_*` for verification helpers, for example `installers/assets/vault/scripts/check_llm_wiki_memory.sh`
- `test_*` for test modules, for example `tests/test_llm_wiki_skill_mcp.py`

**Directories:**

- Lowercase descriptive directories with underscores or compound names, for example `skills/home`, `support/scripts`, `deploy/cloudflare`
- Hidden directories are operational state or generated outputs, such as `.llm-wiki/`, `.brv/`, and `.planning/`

**Special Patterns:**

- Numbered prompt files in `prompts/00-*.md` through `prompts/13-*.md`
- One wrapper skill per directory under `skills/home/<skill-name>/`
- One test file per major behavior surface under `tests/`

## Where to Add New Code

**New installer or scaffold behavior:**

- Primary code: `installers/*.py`
- Platform wrappers: matching `installers/*.ps1` and `installers/*.sh` only when the Python path cannot own the behavior alone
- Tests: `tests/test_<area>.py`

**New runtime helper or tool wrapper:**

- Implementation: `support/scripts/`
- Docs if needed: `README.md` or `support/*.md`
- Tests: `tests/test_<area>.py` or a new Node test if the code is JavaScript

**New prompt or skill asset:**

- Prompt source: `prompts/`
- Home wrapper surface: `skills/home/`
- Plugin packaging: `plugins/llm-wiki-organizer/`

**New hosted deploy surface:**

- Deployment artifacts: `deploy/<provider>/`
- Shared container/runtime changes: `docker/` and `docker-compose*.yml`

## Special Directories

**deps/pk-skills1/:**

- Purpose: Richer repo-owned harness/runtime dependency
- Source: Git submodule declared in `.gitmodules`
- Committed: Submodule pointer only; the content is not first-party source in this repo

**.llm-wiki/:**

- Purpose: Packet-local managed-tool manifest and local workspace state for this checkout
- Source: Partly tracked (`.llm-wiki/package.json`), mostly generated in installed workspaces
- Committed: Partially

**.llm-wiki/memory-ledger/:**

- Purpose: Local-first semantic/preference memory controller state
- Source: Created by the memory controller and installer bootstrap
- Committed: Directory `.gitkeep` files only; memory objects, `events.jsonl`, and `index.json` are ignored
- Read by: `support/scripts/llm_wiki_packet.py` and `support/scripts/dashboard_server.py`
- Written by: `support/scripts/llm_wiki_memory_controller.py`

**.planning/codebase/:**

- Purpose: Generated codebase documentation for planning and onboarding
- Source: Refreshed by mapping workflows such as this one
- Committed: Yes

**Visual map:**

- `.planning/codebase/VISUAL_MEMORY_RETRIEVAL_MAP.md` shows the full review-gated memory loop, tool-call points, ledger state, retrieval precedence, and remaining personalization gaps.

---

_Structure analysis: 2026-04-12_
_Update when top-level layout or ownership boundaries change_
