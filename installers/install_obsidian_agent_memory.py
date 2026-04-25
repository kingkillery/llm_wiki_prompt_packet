#!/usr/bin/env python3
"""
Install the LLM Wiki prompt packet into an Obsidian vault for Claude Code,
Antigravity, Codex, and Droid-compatible setups.

Usage:
  python3 install_obsidian_agent_memory.py --vault "/path/to/Vault"
  python3 install_obsidian_agent_memory.py --vault "/path/to/Vault" --targets claude,antigravity,codex,droid --force
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

PACKET_ROOT = Path(__file__).resolve().parents[1]
PROMPTS = PACKET_ROOT / "prompts"
ASSET_ROOT = PACKET_ROOT / "installers" / "assets" / "vault"
SUPPORT = PACKET_ROOT / "support"
HOME_SKILLS_ROOT = PACKET_ROOT / "skills" / "home"

TARGETS_ALL = ("claude", "antigravity", "codex", "droid", "pi")
STACK_CONFIG_PATH = ".llm-wiki/config.json"
STACK_DEPENDENCY_MANIFEST_PATH = ".llm-wiki/package.json"
STACK_GITIGNORE_PATH = ".llm-wiki/.gitignore"
PACKET_OWNER = "llm-wiki-prompt-packet"
HOME_SKILL_OWNER_MARKER = ".llm-wiki-packet-owner.json"
RICH_MARKERS = {"bin", "browse", "qa", "review", "kade"}
RICH_SIBLING_HINTS = {"debug", "debugging", "deploy", "deployment", "design", "dogfood", "dx", "investigate", "ship", "workflows"}
DEFAULT_INSTALL_SCOPE = "local"
DEFAULT_BRV_PACKAGE = "byterover-cli"
DEFAULT_OBSIDIAN_PACKAGE = "@bitbonsai/mcpvault"
DEFAULT_QMD_REPO_REF = "ef26cb62bb8132bc3a851b23f450af8e382e4c4e"
DEFAULT_GITVIZZ_REPO_URL = "https://github.com/kingkillery/GitVizz.git"
OFFICIAL_MEMORY_VAULT_NAME = "kade-hq"
OFFICIAL_MEMORY_VAULT_ID = "fd8411f00d3a9d21"
OFFICIAL_MEMORY_VAULT_PATH = r"C:\dev\Desktop-Projects\Helpful-Docs-Prompts\VAULTS-OBSIDIAN\Kade-HQ"
PK_SKILLS_SUBMODULE_PATH = "deps/pk-skills1"
PK_SKILLS_REPO_URL = "https://github.com/kingkillery/pk-skills1.git"
REPO_RUNTIME_DEFAULT_PATHS = {
    "g-kade": "deps/pk-skills1/gstack/g-kade",
    "gstack": "deps/pk-skills1/gstack",
}
REPO_RUNTIME_PREFERRED_CANDIDATES = {
    "g-kade": (
        "deps/pk-skills1/gstack/g-kade",
        "deps/pk-skills1/g-kade",
    ),
    "gstack": (
        "deps/pk-skills1/gstack",
    ),
}
REPO_RUNTIME_FALLBACK_ROOTS = (
    ".llm-wiki/deps",
    "vendor",
    "deps",
    "dependencies",
    "submodules",
)
AGENTS_GUIDANCE_START = "<!-- llm-wiki-prompt-packet:agents-guidance:start -->"
AGENTS_GUIDANCE_END = "<!-- llm-wiki-prompt-packet:agents-guidance:end -->"
AGENTS_GUIDANCE_SECTION = f"""{AGENTS_GUIDANCE_START}
## KADE-HQ, Memory, and Retrieval Routing

Use this workspace as a KADE-HQ-backed memory workspace. Treat `AGENTS.md`, `LLM_WIKI_MEMORY.md`, `.llm-wiki/config.json`, `wiki/`, and `kade/` as the operating contract for future agent work.

### Startup Routing

- Read `AGENTS.md` first, then `LLM_WIKI_MEMORY.md`, then `.llm-wiki/config.json` before substantive work.
- If this is a KADE-enabled workspace, also read `kade/AGENTS.md` and `kade/KADE.md` when present.
- Load `~/.kade/HUMAN.md` when present for user/workflow preferences, but prefer project-local instructions when they conflict.
- Run `scripts/setup_llm_wiki_memory.ps1` or `scripts/setup_llm_wiki_memory.sh` if required memory/retrieval tools are missing.

### Retrieval Order

- Use `pk-qmd` first for source-backed repo, prompt, note, and wiki evidence when the right file or concept is not already known.
- Use Obsidian MCP tools for wiki note reads, writes, moves, and tag updates when available; fall back to direct file I/O only when Obsidian is unavailable, and record that fallback in `wiki/log.md`.
- Use `llm-wiki-skills` for reusable skill lookup, reflection, validation, evolution, and retirement.
- Use BRV only for durable preferences, repeated workflow quirks, and decisions; do not rely on it when no provider is connected.
- Use GitVizz for repo topology, API surface, route relationships, and graph-oriented navigation after retrieval has identified the likely area.
- Prefer current source evidence over memory when sources and memory conflict.
- Start with `llm-wiki-packet context --task "..."` for a compact task bundle; use `llm-wiki-packet evidence --query "..."`, `llm-wiki-packet evidence --plane source --query "..."`, or `llm-wiki-packet context --mode deep` only when broader hybrid/source search is useful.

### KADE-HQ System Use

- Treat KADE-HQ as the human/profile and workspace-orchestration layer, not as a replacement for project instructions.
- Treat `g-kade` as the bridge/router across KADE-HQ, G-Stack workflows, and this packet.
- Use G-Stack workflows for review, QA, debugging, browser dogfooding, deployment verification, and ship-readiness checks when the corresponding skill/runtime is installed.
- Keep the root packet files as the source of truth for memory/retrieval wiring; keep KADE-specific handoff state under `kade/`.

### Memory Writes

- Write durable repo knowledge to `wiki/` pages, not chat-only memory.
- Write reusable procedures as skill artifacts under the configured skill lifecycle, not ad hoc notes.
- Keep raw immutable sources under `raw/`; never edit `raw/` unless explicitly asked.
- Update `wiki/index.md` when adding or moving durable pages.
- Update `wiki/log.md` for meaningful wiki changes, tool fallbacks, setup changes, and unresolved questions.
- For long-running harness work, use `llm-wiki-packet manifest`, `reduce`, `evaluate`, `promote`, and `improve` so artifacts, memory promotion, and self-improvement gates share the same run id.
{AGENTS_GUIDANCE_END}"""

ROOT_FILES = {
    "AGENTS.md": PROMPTS / "01-AGENTS.md",
    "CLAUDE.md": PROMPTS / "02-CLAUDE.md",
    "LLM_WIKI_MEMORY.md": SUPPORT / "LLM_WIKI_MEMORY.md",
    "SYSTEM_CONTRACT.md": SUPPORT / "SYSTEM_CONTRACT.md",
    "KNOWN_ISSUES.md": SUPPORT / "KNOWN_ISSUES.md",
    "SKILL_CREATION_AT_EXPERT_LEVEL.md": SUPPORT / "SKILL_CREATION_AT_EXPERT_LEVEL.md",
}

CLAUDE_FILES = {
    ".claude/commands/wiki-ingest.md": PROMPTS / "09-claude-command-ingest.md",
    ".claude/commands/wiki-query.md": PROMPTS / "10-claude-command-query.md",
    ".claude/commands/wiki-lint.md": PROMPTS / "11-claude-command-lint.md",
    ".claude/commands/wiki-skill.md": PROMPTS / "12-claude-command-skill.md",
}

ANTIGRAVITY_FILES = {
    ".agent/workflows/wiki-ingest.md": PROMPTS / "06-antigravity-ingest-workflow.md",
    ".agent/workflows/wiki-query.md": PROMPTS / "07-antigravity-query-workflow.md",
    ".agent/workflows/wiki-lint.md": PROMPTS / "08-antigravity-lint-workflow.md",
    ".agent/workflows/wiki-skill.md": PROMPTS / "13-antigravity-skill-workflow.md",
}

CODEX_FILES = {
    ".agents/skills/llm-wiki-organizer/SKILL.md": PROMPTS / "03-codex-skill-SKILL.md",
    ".agents/skills/llm-wiki-organizer/assets/system-prompt.md": PROMPTS / "00-system-prompt.md",
    ".agents/skills/llm-wiki-organizer/assets/tool-directives.md": PROMPTS / "04-tool-directives.md",
    ".agents/skills/llm-wiki-organizer/assets/output-contract.md": PROMPTS / "05-output-contract.md",
}

STACK_FILES = {
    "scripts/check_llm_wiki_memory.ps1": ASSET_ROOT / "scripts" / "check_llm_wiki_memory.ps1",
    "scripts/check_llm_wiki_memory.sh": ASSET_ROOT / "scripts" / "check_llm_wiki_memory.sh",
    "scripts/check_llm_wiki_memory.cmd": ASSET_ROOT / "scripts" / "check_llm_wiki_memory.cmd",
    "scripts/llm_wiki_packet.py": SUPPORT / "scripts" / "llm_wiki_packet.py",
    "scripts/llm_wiki_packet.ps1": SUPPORT / "scripts" / "llm_wiki_packet.ps1",
    "scripts/llm_wiki_packet.sh": SUPPORT / "scripts" / "llm_wiki_packet.sh",
    "scripts/llm_wiki_packet.cmd": SUPPORT / "scripts" / "llm_wiki_packet.cmd",
    "scripts/llm_wiki_memory_runtime.py": SUPPORT / "scripts" / "llm_wiki_memory_runtime.py",
    "scripts/llm_wiki_obsidian_mcp.py": SUPPORT / "scripts" / "llm_wiki_obsidian_mcp.py",
    "scripts/llm_wiki_skill_mcp.py": SUPPORT / "scripts" / "llm_wiki_skill_mcp.py",
    "scripts/llm_wiki_failure_collector.py": SUPPORT / "scripts" / "llm_wiki_failure_collector.py",
    "scripts/llm_wiki_failure_hook.py": SUPPORT / "scripts" / "llm_wiki_failure_hook.py",
    "scripts/llm_wiki_agent_failure_capture.py": SUPPORT / "scripts" / "llm_wiki_agent_failure_capture.py",
    "scripts/run_llm_wiki_agent.ps1": SUPPORT / "scripts" / "run_llm_wiki_agent.ps1",
    "scripts/run_llm_wiki_agent.sh": SUPPORT / "scripts" / "run_llm_wiki_agent.sh",
    "scripts/run_llm_wiki_agent.cmd": SUPPORT / "scripts" / "run_llm_wiki_agent.cmd",
    "scripts/pokemon_benchmark_adapter.py": SUPPORT / "scripts" / "pokemon_benchmark_adapter.py",
    "scripts/run_pokemon_benchmark.ps1": SUPPORT / "scripts" / "run_pokemon_benchmark.ps1",
    "scripts/setup_llm_wiki_memory.ps1": SUPPORT / "scripts" / "setup_llm_wiki_memory.ps1",
    "scripts/setup_llm_wiki_memory.sh": SUPPORT / "scripts" / "setup_llm_wiki_memory.sh",
    "scripts/setup_llm_wiki_memory.cmd": SUPPORT / "scripts" / "setup_llm_wiki_memory.cmd",
    "scripts/qmd_embed_runner.mjs": SUPPORT / "scripts" / "qmd_embed_runner.mjs",
    "scripts/invoke_bash_helper.ps1": SUPPORT / "scripts" / "invoke_bash_helper.ps1",
    "scripts/brv_query.ps1": SUPPORT / "scripts" / "brv_query.ps1",
    "scripts/brv_query.sh": SUPPORT / "scripts" / "brv_query.sh",
    "scripts/brv_curate.ps1": SUPPORT / "scripts" / "brv_curate.ps1",
    "scripts/brv_curate.sh": SUPPORT / "scripts" / "brv_curate.sh",
    "scripts/brv_benchmark.py": SUPPORT / "scripts" / "brv_benchmark.py",
    "scripts/brv_benchmark.ps1": SUPPORT / "scripts" / "brv_benchmark.ps1",
    "scripts/brv_benchmark.sh": SUPPORT / "scripts" / "brv_benchmark.sh",
    "scripts/gitvizz_api.ps1": SUPPORT / "scripts" / "gitvizz_api.ps1",
    "scripts/gitvizz_api.sh": SUPPORT / "scripts" / "gitvizz_api.sh",
    "scripts/launch_gitvizz.ps1": SUPPORT / "scripts" / "launch_gitvizz.ps1",
    "scripts/launch_gitvizz.sh": SUPPORT / "scripts" / "launch_gitvizz.sh",
}

BOOTSTRAP_FILES = {
    "wiki/index.md": "# Wiki Index\n\n",
    "wiki/log.md": "# Wiki Log\n\n",
    "wiki/skills/index.md": "# Skill Index\n\n",
    "raw/.gitkeep": "",
    "raw/assets/.gitkeep": "",
    "wiki/sources/.gitkeep": "",
    "wiki/entities/.gitkeep": "",
    "wiki/concepts/.gitkeep": "",
    "wiki/syntheses/.gitkeep": "",
    "wiki/comparisons/.gitkeep": "",
    "wiki/timelines/.gitkeep": "",
    "wiki/questions/.gitkeep": "",
    "wiki/skills/active/.gitkeep": "",
    "wiki/skills/feedback/.gitkeep": "",
    "wiki/skills/retired/.gitkeep": "",
    "templates/.gitkeep": "",
    "scripts/.gitkeep": "",
    ".llm-wiki/.gitkeep": "",
    ".llm-wiki/.gitignore": "node_modules/\npackage-lock.json\ntools/\nsetup-state.json\nskill-pipeline/runs/*\n!skill-pipeline/runs/.gitkeep\n",
    ".llm-wiki/skills-registry.json": "{\n  \"skills\": {},\n  \"feedback\": [],\n  \"briefs\": [],\n  \"deltas\": [],\n  \"validations\": [],\n  \"packets\": [],\n  \"proposals\": [],\n  \"surrogate_reviews\": [],\n  \"evolution_runs\": [],\n  \"frontier\": [],\n  \"events\": []\n}\n",
    ".llm-wiki/skill-pipeline/.gitkeep": "",
    ".llm-wiki/skill-pipeline/briefs/.gitkeep": "",
    ".llm-wiki/skill-pipeline/deltas/.gitkeep": "",
    ".llm-wiki/skill-pipeline/validations/.gitkeep": "",
    ".llm-wiki/skill-pipeline/packets/.gitkeep": "",
    ".llm-wiki/skill-pipeline/runs/.gitkeep": "",
    ".llm-wiki/skill-pipeline/proposals/.gitkeep": "",
    ".llm-wiki/skill-pipeline/surrogate-reviews/.gitkeep": "",
    ".llm-wiki/skill-pipeline/evolution-runs/.gitkeep": "",
    ".llm-wiki/skill-pipeline/frontier.json": "[]\n",
    ".llm-wiki/skill-pipeline/failures/.gitkeep": "",
    ".llm-wiki/skill-pipeline/failures/events/.gitkeep": "",
    ".llm-wiki/skill-pipeline/failures/clusters/.gitkeep": "",
    ".llm-wiki/skill-pipeline/failures/benchmarks/.gitkeep": "",
    ".brv/.gitkeep": "",
    ".brv/context-tree/.gitkeep": "",
    ".llm-wiki/qmd-embed-state.json": "{\n  \"status\": \"not-run\"\n}\n",
}

HOME_SKILL_TARGETS = {
    ".agents/skills/gstack": HOME_SKILLS_ROOT / "gstack",
    ".agents/skills/kade-hq": HOME_SKILLS_ROOT / "kade-hq",
    ".agents/skills/g-kade": HOME_SKILLS_ROOT / "g-kade",
    ".agents/skills/llm-wiki-skills": HOME_SKILLS_ROOT / "llm-wiki-skills",
    ".agents/skills/pokemon-benchmark": HOME_SKILLS_ROOT / "pokemon-benchmark",
    ".pi/agent/skills/gstack": HOME_SKILLS_ROOT / "gstack",
    ".pi/agent/skills/kade-hq": HOME_SKILLS_ROOT / "kade-hq",
    ".pi/agent/skills/g-kade": HOME_SKILLS_ROOT / "g-kade",
    ".pi/agent/skills/llm-wiki-skills": HOME_SKILLS_ROOT / "llm-wiki-skills",
    ".pi/agent/skills/pokemon-benchmark": HOME_SKILLS_ROOT / "pokemon-benchmark",
    ".codex/skills/gstack": HOME_SKILLS_ROOT / "gstack",
    ".codex/skills/kade-hq": HOME_SKILLS_ROOT / "kade-hq",
    ".codex/skills/g-kade": HOME_SKILLS_ROOT / "g-kade",
    ".codex/skills/llm-wiki-skills": HOME_SKILLS_ROOT / "llm-wiki-skills",
    ".codex/skills/pokemon-benchmark": HOME_SKILLS_ROOT / "pokemon-benchmark",
    ".claude/skills/gstack": HOME_SKILLS_ROOT / "gstack",
    ".claude/skills/kade-hq": HOME_SKILLS_ROOT / "kade-hq",
    ".claude/skills/g-kade": HOME_SKILLS_ROOT / "g-kade",
    ".claude/skills/llm-wiki-skills": HOME_SKILLS_ROOT / "llm-wiki-skills",
    ".claude/skills/pokemon-benchmark": HOME_SKILLS_ROOT / "pokemon-benchmark",
}

DANGEROUS_HOME_TARGETS = (
    ".agents",
    ".agents/skills",
    ".pi",
    ".pi/agent",
    ".pi/agent/skills",
    ".codex",
    ".codex/skills",
    ".claude",
    ".claude/skills",
)


def env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def normalize_url(value: str) -> str:
    return value.rstrip("/")


def normalize_path_string(value: str) -> str:
    return value.strip().rstrip("/\\")


def qmd_source_checkout_path(raw_path: str) -> Path | None:
    normalized = normalize_path_string(raw_path)
    if not normalized:
        return None
    return Path(normalized).expanduser().resolve()


def env_flag(name: str) -> bool:
    value = os.getenv(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_install_scope(value: str | None) -> str:
    normalized = (value or DEFAULT_INSTALL_SCOPE).strip().lower()
    aliases = {
        "g": "global",
        "global": "global",
        "l": "local",
        "local": "local",
        "project": "local",
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise SystemExit(f"Unknown install scope: {value}. Use 'local' or 'global'.") from exc


def default_install_scope() -> str:
    return normalize_install_scope(env_or_default("LLM_WIKI_INSTALL_SCOPE", DEFAULT_INSTALL_SCOPE))


def managed_tool_root(vault: Path, home_root: Path, install_scope: str) -> Path:
    if normalize_install_scope(install_scope) == "global":
        return (home_root / ".llm-wiki" / "tools").resolve()
    return vault / ".llm-wiki" / "tools"


def qmd_managed_candidates(vault: Path, home_root: Path, install_scope: str) -> list[Path]:
    tool_root = managed_tool_root(vault, home_root, install_scope)
    checkout_root = tool_root / "pk-qmd"
    return [
        tool_root / "bin" / "pk-qmd.cmd",
        tool_root / "bin" / "pk-qmd.ps1",
        tool_root / "bin" / "pk-qmd",
        checkout_root / "dist" / "cli" / "qmd.js",
    ]


def brv_managed_candidates(vault: Path, home_root: Path, install_scope: str) -> list[Path]:
    install_root = managed_tool_root(vault, home_root, install_scope) / "brv"
    return [
        install_root / "node_modules" / ".bin" / "brv.cmd",
        install_root / "node_modules" / ".bin" / "brv.ps1",
        install_root / "node_modules" / ".bin" / "brv",
    ]


def obsidian_managed_candidates(vault: Path, home_root: Path, install_scope: str) -> list[Path]:
    install_root = managed_tool_root(vault, home_root, install_scope) / "obsidian-mcp"
    return [
        install_root / "node_modules" / ".bin" / "mcpvault.cmd",
        install_root / "node_modules" / ".bin" / "mcpvault.ps1",
        install_root / "node_modules" / ".bin" / "mcpvault",
    ]


def default_memory_vault_path(vault: Path) -> str:
    override = os.getenv("LLM_WIKI_MEMORY_VAULT_PATH")
    if override and override.strip():
        return normalize_path_string(override)
    official = Path(OFFICIAL_MEMORY_VAULT_PATH)
    if official.exists():
        return str(official)
    return str(vault.resolve())


def default_memory_vault_name(vault_path: Path) -> str:
    override = os.getenv("LLM_WIKI_MEMORY_VAULT_NAME")
    if override and override.strip():
        return override.strip()
    try:
        if vault_path.resolve() == Path(OFFICIAL_MEMORY_VAULT_PATH).resolve():
            return OFFICIAL_MEMORY_VAULT_NAME
    except OSError:
        pass
    return vault_path.name.lower().replace(" ", "-")


def default_memory_vault_id(vault_path: Path) -> str:
    override = os.getenv("LLM_WIKI_MEMORY_VAULT_ID")
    if override and override.strip():
        return override.strip()
    try:
        if vault_path.resolve() == Path(OFFICIAL_MEMORY_VAULT_PATH).resolve():
            return OFFICIAL_MEMORY_VAULT_ID
    except OSError:
        pass
    return ""


def resolve_home_skill_install(args: argparse.Namespace) -> bool:
    if getattr(args, "install_home_skills", False):
        return True
    if getattr(args, "skip_home_skills", False):
        return False
    if env_flag("LLM_WIKI_INSTALL_HOME_SKILLS"):
        return True
    if env_flag("LLM_WIKI_SKIP_HOME_SKILLS"):
        return False
    return False


def global_tool_install_allowed(args: argparse.Namespace | None = None) -> bool:
    if args is not None and getattr(args, "allow_global_tool_install", False):
        return True
    return env_flag("LLM_WIKI_ALLOW_GLOBAL_TOOL_INSTALL")


def qmd_package_spec(repo_url: str, repo_ref: str) -> str:
    normalized_url = repo_url.rstrip("/")
    if normalized_url.startswith("git+"):
        base = normalized_url
    elif normalized_url.endswith(".git"):
        base = f"git+{normalized_url}"
    else:
        base = f"git+{normalized_url}.git"
    normalized_ref = repo_ref.strip()
    if normalized_ref:
        return f"{base}#{normalized_ref}"
    return base


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, help="Path to the Obsidian vault")
    parser.add_argument(
        "--targets",
        default="claude,antigravity,codex,droid,pi",
        help="Comma-separated targets: claude,antigravity,codex,droid,pi",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files managed by this installer",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Report bootstrap actions and tool detection without writing files",
    )
    parser.add_argument(
        "--allow-home-root",
        action="store_true",
        help="Allow installing directly into shared home-control paths such as ~ or ~/.agents/skills",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing files",
    )
    home_skill_group = parser.add_mutually_exclusive_group()
    home_skill_group.add_argument(
        "--install-home-skills",
        action="store_true",
        help="Install packet-owned wrapper skills into ~/.agents, ~/.codex, ~/.claude, and ~/.pi/agent",
    )
    home_skill_group.add_argument(
        "--skip-home-skills",
        action="store_true",
        help="Skip installing packet-owned home skills into the user skill roots",
    )
    parser.add_argument(
        "--home-root",
        default=env_or_default("LLM_WIKI_HOME_ROOT", str(Path.home())),
        help="Override the home directory used for installing packet-owned skills",
    )
    parser.add_argument(
        "--install-scope",
        default=default_install_scope(),
        help="Install tool dependencies into the local workspace or the user-level managed tool root: local|global",
    )
    parser.add_argument(
        "-g",
        "--global-install",
        dest="install_scope",
        action="store_const",
        const="global",
        help="Install managed tool dependencies into the user-level shared tool root instead of the workspace",
    )
    parser.add_argument(
        "--allow-global-tool-install",
        action="store_true",
        help="Allow setup helpers to fall back to global npm installs when packet-local installs are unavailable",
    )
    parser.add_argument(
        "--qmd-command",
        default=env_or_default("LLM_WIKI_QMD_COMMAND", "pk-qmd"),
        help="Command name for the custom QMD fork",
    )
    parser.add_argument(
        "--qmd-repo-url",
        default=env_or_default("LLM_WIKI_QMD_REPO_URL", "https://github.com/kingkillery/pk-qmd"),
        help="Packet fallback source for the custom pk-qmd fork",
    )
    parser.add_argument(
        "--qmd-repo-ref",
        default=env_or_default("LLM_WIKI_QMD_REPO_REF", DEFAULT_QMD_REPO_REF),
        help="Pinned commit or tag for the managed pk-qmd checkout",
    )
    parser.add_argument(
        "--qmd-source-checkout",
        default=os.getenv("LLM_WIKI_QMD_SOURCE_CHECKOUT", ""),
        help="Optional local pk-qmd checkout to prefer over the managed git fallback, for example a Gemini-capable pk-qmd-main repo",
    )
    parser.add_argument(
        "--qmd-mcp-url",
        default=env_or_default("LLM_WIKI_QMD_MCP_URL", "http://localhost:8181/mcp"),
        help="HTTP MCP endpoint for the shared pk-qmd server",
    )
    parser.add_argument(
        "--brv-command",
        default=env_or_default("LLM_WIKI_BRV_COMMAND", "brv"),
        help="Command name for the Byterover CLI",
    )
    parser.add_argument(
        "--gitvizz-frontend-url",
        default=env_or_default("LLM_WIKI_GITVIZZ_FRONTEND_URL", "http://localhost:3000"),
        help="Frontend URL for the GitVizz web app",
    )
    parser.add_argument(
        "--gitvizz-backend-url",
        default=env_or_default("LLM_WIKI_GITVIZZ_BACKEND_URL", "http://localhost:8003"),
        help="Backend URL for the GitVizz API service",
    )
    parser.add_argument(
        "--gitvizz-repo-path",
        default=env_or_default("LLM_WIKI_GITVIZZ_REPO_PATH", ""),
        help="Optional local checkout path for launching GitVizz via docker-compose",
    )
    parser.add_argument(
        "--gitvizz-repo-url",
        default=env_or_default("LLM_WIKI_GITVIZZ_REPO_URL", DEFAULT_GITVIZZ_REPO_URL),
        help="Optional GitVizz repo URL for managed local acquisition",
    )
    parser.add_argument(
        "--gitvizz-checkout-path",
        default=env_or_default("LLM_WIKI_GITVIZZ_CHECKOUT_PATH", ""),
        help="Optional managed local checkout path for GitVizz acquisition or update",
    )
    parser.add_argument(
        "--g-kade-dependency-path",
        default=env_or_default("LLM_WIKI_G_KADE_DEPENDENCY_PATH", REPO_RUNTIME_DEFAULT_PATHS["g-kade"]),
        help="Repo-owned richer g-kade dependency, submodule, or vendor path relative to the workspace",
    )
    parser.add_argument(
        "--gstack-dependency-path",
        default=env_or_default("LLM_WIKI_GSTACK_DEPENDENCY_PATH", REPO_RUNTIME_DEFAULT_PATHS["gstack"]),
        help="Repo-owned richer gstack dependency, submodule, or vendor path relative to the workspace",
    )
    parser.add_argument(
        "--memory-vault-path",
        default=env_or_default("LLM_WIKI_MEMORY_VAULT_PATH", ""),
        help="Official Obsidian memory-base vault path used for pk-qmd traversal and long-term system memory",
    )
    parser.add_argument(
        "--memory-vault-name",
        default=env_or_default("LLM_WIKI_MEMORY_VAULT_NAME", ""),
        help="Stable name for the official memory-base vault",
    )
    parser.add_argument(
        "--memory-vault-id",
        default=env_or_default("LLM_WIKI_MEMORY_VAULT_ID", ""),
        help="Stable vault identifier for the official memory-base vault",
    )
    return parser.parse_args()


def ensure_safe_install_root(target_root: Path, home_root: Path, *, allow_home_root: bool) -> None:
    if allow_home_root:
        return

    dangerous_paths = [home_root]
    dangerous_paths.extend(home_root / relative for relative in DANGEROUS_HOME_TARGETS)
    if any(target_root == path.resolve() for path in dangerous_paths):
        raise SystemExit(
            "Refusing to install into a shared home path: "
            f"{target_root}. Pass --allow-home-root only if you explicitly intend to manage that shared root."
        )


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def tool_status_line(name: str, path: str | Path | None, *, missing_note: str) -> str:
    if path:
        return f"preflight {name}: {path}"
    return f"preflight {name}: missing ({missing_note})"


def workspace_relative_path(workspace_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    return workspace_root / normalize_path_string(raw_path)


def relative_or_absolute_path(path: Path, workspace_root: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def repo_runtime_candidate_relpaths(name: str, configured_path: str) -> list[str]:
    normalized = normalize_path_string(configured_path) or REPO_RUNTIME_DEFAULT_PATHS[name]
    candidates = [normalized]
    for preferred in REPO_RUNTIME_PREFERRED_CANDIDATES.get(name, ()):
        if preferred not in candidates:
            candidates.append(preferred)
    for root in REPO_RUNTIME_FALLBACK_ROOTS:
        fallback = f"{root}/{name}"
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def richer_skill_markers(candidate: Path, wrapper_root: Path) -> list[str]:
    if not candidate.exists() or not candidate.is_dir():
        return []
    if not (candidate / "SKILL.md").exists():
        return []

    markers: list[str] = []
    child_dirs = sorted(path.name for path in candidate.iterdir() if path.is_dir())
    child_files = sorted(path.name for path in candidate.iterdir() if path.is_file())
    wrapper_files = {
        path.relative_to(wrapper_root).as_posix()
        for path in wrapper_root.rglob("*")
        if path.is_file()
    }
    candidate_files = {
        path.relative_to(candidate).as_posix()
        for path in candidate.rglob("*")
        if path.is_file()
    }

    for marker in sorted(RICH_MARKERS):
        if (candidate / marker).exists():
            markers.append(marker)

    sibling_matches = sorted(name for name in child_dirs if name in RICH_SIBLING_HINTS)
    if len(sibling_matches) >= 2:
        markers.append(f"siblings:{','.join(sibling_matches)}")

    extra_files = sorted(path for path in candidate_files if path not in wrapper_files)
    if len(extra_files) >= 3:
        markers.append("extra-files")

    extra_markdown = [name for name in child_files if name.endswith(".md") and name != "SKILL.md"]
    if extra_markdown:
        markers.append("companion-docs")

    if any(name.endswith(".tmpl") for name in child_files):
        markers.append("template-assets")

    return markers


def repo_runtime_dependency_status(workspace_root: Path, name: str, configured_path: str) -> dict[str, object]:
    wrapper_root = HOME_SKILLS_ROOT / name
    candidate_relpaths = repo_runtime_candidate_relpaths(name, configured_path)
    thin_candidate: Path | None = None
    thin_reason = "missing SKILL.md"

    for relpath in candidate_relpaths:
        candidate = workspace_relative_path(workspace_root, relpath)
        markers = richer_skill_markers(candidate, wrapper_root)
        if markers:
            return {
                "name": name,
                "contract": "repo-owned dependency/submodule/vendor path",
                "configured_path": normalize_path_string(configured_path) or REPO_RUNTIME_DEFAULT_PATHS[name],
                "candidate_paths": candidate_relpaths,
                "status": "detected",
                "detected_path": relative_or_absolute_path(candidate, workspace_root),
                "markers": markers,
                "manual_install_required": True,
            }
        if candidate.exists() and thin_candidate is None:
            thin_candidate = candidate
            if (candidate / "SKILL.md").exists():
                thin_reason = "wrapper-like or incomplete runtime"

    return {
        "name": name,
        "contract": "repo-owned dependency/submodule/vendor path",
        "configured_path": normalize_path_string(configured_path) or REPO_RUNTIME_DEFAULT_PATHS[name],
        "candidate_paths": candidate_relpaths,
        "status": "present-but-thin" if thin_candidate else "missing",
        "detected_path": relative_or_absolute_path(thin_candidate, workspace_root) if thin_candidate else None,
        "markers": [],
        "reason": thin_reason if thin_candidate else "not present",
        "manual_install_required": True,
    }


def repo_runtime_preflight_line(status: dict[str, object]) -> str:
    name = status["name"]
    configured = status["configured_path"]
    detected = status.get("detected_path")
    state = status["status"]
    if state == "detected":
        markers = ", ".join(status.get("markers", []))
        suffix = f" ({markers})" if markers else ""
        return f"preflight {name} runtime: repo-owned dependency {detected}{suffix}"
    if state == "present-but-thin":
        reason = status.get("reason", "wrapper-like or incomplete runtime")
        return f"preflight {name} runtime: present but thin at {detected} ({reason}; configured path {configured})"
    return f"preflight {name} runtime: missing (expected repo-owned dependency at {configured})"


def build_preflight_report(
    vault: Path,
    home_root: Path,
    *,
    install_home_skills: bool,
    run_setup: bool,
    allow_global_tool_install: bool,
    install_scope: str,
    g_kade_dependency_path: str,
    gstack_dependency_path: str,
    qmd_source_checkout: str = "",
) -> list[str]:
    node = shutil.which("node")
    npm = shutil.which("npm")
    git = shutil.which("git")
    docker = shutil.which("docker")
    local_qmd = first_existing(qmd_managed_candidates(vault, home_root, install_scope))
    local_brv = first_existing(brv_managed_candidates(vault, home_root, install_scope))
    global_qmd = shutil.which("pk-qmd")
    global_brv = shutil.which("brv")
    g_kade_runtime = repo_runtime_dependency_status(vault, "g-kade", g_kade_dependency_path)
    gstack_runtime = repo_runtime_dependency_status(vault, "gstack", gstack_dependency_path)
    managed_root = managed_tool_root(vault, home_root, install_scope)
    submodule_root = vault / PK_SKILLS_SUBMODULE_PATH
    qmd_source_checkout_path_value = qmd_source_checkout_path(qmd_source_checkout)

    lines = [
        "Preflight:",
        f"preflight target-root: {vault}",
        f"preflight home-root: {home_root}",
        f"preflight install-scope: {install_scope}",
        f"preflight managed-tool-root: {managed_root}",
        f"preflight home-skill-install: {'enabled' if install_home_skills else 'disabled (default)'}",
        f"preflight global-tool-install: {'enabled' if allow_global_tool_install else 'disabled (default)'}",
        f"preflight g-kade wrapper: {'enabled' if install_home_skills else 'available (home install opt-in)'}",
        f"preflight gstack wrapper: {'enabled' if install_home_skills else 'available (home install opt-in)'}",
        repo_runtime_preflight_line(g_kade_runtime),
        repo_runtime_preflight_line(gstack_runtime),
        tool_status_line("python", Path(sys.executable), missing_note="running interpreter unavailable"),
        tool_status_line("git", git, missing_note="required for git-based npm dependencies"),
        tool_status_line("node", node, missing_note="optional for qmd embed runner"),
        tool_status_line("npm", npm, missing_note="required when pk-qmd or brv must be installed"),
        tool_status_line("docker", docker, missing_note="optional unless you manage GitVizz locally"),
        f"preflight pk-qmd pin: {DEFAULT_QMD_REPO_REF}",
        (
            f"preflight pk-qmd source checkout: {qmd_source_checkout_path_value}"
            if qmd_source_checkout_path_value
            else "preflight pk-qmd source checkout: none (managed git fallback)"
        ),
        (
            f"preflight pk-skills1 source: {submodule_root}"
            if submodule_root.exists()
            else f"preflight pk-skills1 source: missing ({PK_SKILLS_SUBMODULE_PATH} from {PK_SKILLS_REPO_URL})"
        ),
    ]

    if local_qmd:
        lines.append(f"preflight pk-qmd: managed {local_qmd}")
    elif global_qmd:
        lines.append(f"preflight pk-qmd: global {global_qmd}")
    elif run_setup and npm and git:
        lines.append(f"preflight pk-qmd: missing (setup can clone/build a {install_scope} managed checkout)")
    else:
        lines.append("preflight pk-qmd: missing (install npm and git before running setup)")

    if local_brv:
        lines.append(f"preflight brv: managed {local_brv}")
    elif global_brv:
        lines.append(f"preflight brv: global {global_brv}")
    elif run_setup and npm:
        fallback = f"{install_scope} managed install preferred"
        if allow_global_tool_install:
            fallback += "; global npm fallback allowed"
        lines.append(f"preflight brv: missing ({fallback})")
    else:
        lines.append("preflight brv: missing (install npm before running setup)")

    if run_setup:
        lines.append("preflight setup-helper: enabled")
    else:
        lines.append("preflight setup-helper: not run by this entrypoint")

    return lines


def write_text(dst: Path, text: str, force: bool, dry_run: bool) -> str:
    if dst.exists() and not force:
        return f"skip   {dst} (exists)"
    if dry_run:
        return f"write  {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return f"write  {dst}"


def write_json(dst: Path, data: dict[str, object], force: bool, dry_run: bool) -> str:
    if dst.exists() and not force:
        return f"skip   {dst} (exists)"
    if dry_run:
        return f"write  {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"write  {dst}"


def merge_managed_config(existing: dict[str, object], desired: dict[str, object], path: tuple[str, ...] = ()) -> dict[str, object]:
    managed_overwrite_paths = {
        ("toolset", "preferred_project_runtime_commands"),
        ("stack", "retrieval_planner"),
    }
    if path in managed_overwrite_paths:
        return desired
    merged: dict[str, object] = dict(existing)
    for key, desired_value in desired.items():
        current_path = (*path, key)
        existing_value = merged.get(key)
        if isinstance(existing_value, dict) and isinstance(desired_value, dict):
            merged[key] = merge_managed_config(existing_value, desired_value, current_path)
        elif key not in merged or current_path in managed_overwrite_paths:
            merged[key] = desired_value
    return merged


def write_stack_config(dst: Path, data: dict[str, object], force: bool, dry_run: bool) -> str:
    payload = data
    action = "write"
    if dst.exists() and not force:
        try:
            existing = json.loads(dst.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if isinstance(existing, dict):
            payload = merge_managed_config(existing, data)
            action = "update"
            if json.dumps(existing, sort_keys=True) == json.dumps(payload, sort_keys=True):
                return f"skip   {dst} (config current)"
    if dry_run:
        return f"{action:<6} {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return f"{action:<6} {dst}"


def copy_file(src: Path, dst: Path, force: bool, dry_run: bool) -> str:
    if dst.exists() and not force:
        return f"skip   {dst} (exists)"
    if dry_run:
        return f"copy   {src} -> {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"copy   {src} -> {dst}"


def install_map(vault: Path, mapping: dict[str, Path], force: bool, dry_run: bool) -> list[str]:
    results = []
    for rel, src in mapping.items():
        results.append(copy_file(src, vault / rel, force=force, dry_run=dry_run))
    return results


def merge_agents_guidance(existing: str) -> str:
    normalized = existing.replace("\r\n", "\n")
    section = AGENTS_GUIDANCE_SECTION.strip()
    if AGENTS_GUIDANCE_START in normalized and AGENTS_GUIDANCE_END in normalized:
        before, remainder = normalized.split(AGENTS_GUIDANCE_START, 1)
        _, after = remainder.split(AGENTS_GUIDANCE_END, 1)
        return before.rstrip() + "\n\n" + section + "\n\n" + after.lstrip("\n")

    insert_heading = "\n## Done when"
    if insert_heading in normalized:
        before, after = normalized.split(insert_heading, 1)
        return before.rstrip() + "\n\n" + section + "\n" + insert_heading + after

    return normalized.rstrip() + "\n\n" + section + "\n"


def ensure_agents_guidance(vault: Path, *, dry_run: bool) -> str:
    agents_path = vault / "AGENTS.md"
    existing = ""
    if agents_path.exists():
        existing = agents_path.read_text(encoding="utf-8")
    updated = merge_agents_guidance(existing)
    if existing.replace("\r\n", "\n") == updated.replace("\r\n", "\n"):
        return f"skip   {agents_path} (AGENTS guidance current)"
    if dry_run:
        return f"update {agents_path} (merge KADE/memory/retrieval guidance)"
    agents_path.parent.mkdir(parents=True, exist_ok=True)
    agents_path.write_text(updated, encoding="utf-8")
    return f"update {agents_path} (merged KADE/memory/retrieval guidance)"


def has_richer_existing_skill(dst_root: Path, src_root: Path) -> bool:
    if not dst_root.exists():
        return False

    source_files = {
        path.relative_to(src_root).as_posix()
        for path in src_root.rglob("*")
        if path.is_file()
    }
    dest_files = {
        path.relative_to(dst_root).as_posix()
        for path in dst_root.rglob("*")
        if path.is_file()
    }
    return any(path not in source_files for path in dest_files)


def home_skill_owner_marker_path(dst_root: Path) -> Path:
    return dst_root / HOME_SKILL_OWNER_MARKER


def is_packet_owned_home_skill(dst_root: Path) -> bool:
    marker_path = home_skill_owner_marker_path(dst_root)
    if not marker_path.exists():
        return False
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return marker.get("owner") == PACKET_OWNER and marker.get("kind") == "home-skill-wrapper"


def write_home_skill_owner_marker(dst_root: Path, src_root: Path, dry_run: bool) -> str:
    marker_path = home_skill_owner_marker_path(dst_root)
    marker = {
        "owner": PACKET_OWNER,
        "kind": "home-skill-wrapper",
        "skill": src_root.name,
    }
    if dry_run:
        return f"write  {marker_path}"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    return f"write  {marker_path}"


def install_tree(dst_root: Path, rel_root: str, src_root: Path, force: bool, dry_run: bool) -> list[str]:
    results = []
    target_root = dst_root / rel_root
    if target_root.exists() and not is_packet_owned_home_skill(target_root):
        if has_richer_existing_skill(target_root, src_root):
            return [f"skip   {target_root} (existing richer skill)"]
        return [f"skip   {target_root} (existing unowned skill root)"]
    for src in sorted(src_root.rglob("*")):
        if not src.is_file():
            continue
        rel_path = src.relative_to(src_root)
        results.append(copy_file(src, target_root / rel_path, force=force, dry_run=dry_run))
    results.append(write_home_skill_owner_marker(target_root, src_root, dry_run=dry_run))
    return results


def install_home_skills(home_root: Path, force: bool, dry_run: bool) -> list[str]:
    results = []
    for rel_root, src_root in HOME_SKILL_TARGETS.items():
        results.extend(install_tree(home_root, rel_root, src_root, force=force, dry_run=dry_run))
    return results


def bootstrap_vault(vault: Path, force: bool, dry_run: bool) -> list[str]:
    results = []
    for rel, text in BOOTSTRAP_FILES.items():
        results.append(write_text(vault / rel, text, force=force, dry_run=dry_run))
    return results


def normalize_targets(raw: str) -> list[str]:
    targets = [x.strip().lower() for x in raw.split(",") if x.strip()]
    invalid = [x for x in targets if x not in TARGETS_ALL]
    if invalid:
        raise SystemExit(f"Unknown target(s): {', '.join(invalid)}")
    ordered = []
    for x in TARGETS_ALL:
        if x in targets:
            ordered.append(x)
    return ordered


def build_stack_config(args: argparse.Namespace) -> dict[str, object]:
    frontend_url = normalize_url(args.gitvizz_frontend_url)
    backend_url = normalize_url(args.gitvizz_backend_url)
    qmd_mcp_url = normalize_url(args.qmd_mcp_url)
    workspace_root = Path(args.vault).expanduser().resolve()
    home_root = Path(args.home_root).expanduser().resolve()
    install_scope = normalize_install_scope(getattr(args, "install_scope", DEFAULT_INSTALL_SCOPE))
    managed_root = managed_tool_root(workspace_root, home_root, install_scope)
    memory_vault_path_raw = normalize_path_string(getattr(args, "memory_vault_path", "")) or default_memory_vault_path(workspace_root)
    memory_vault_path = workspace_relative_path(workspace_root, memory_vault_path_raw).resolve()
    memory_vault_name = getattr(args, "memory_vault_name", "").strip() or default_memory_vault_name(memory_vault_path)
    memory_vault_id = getattr(args, "memory_vault_id", "").strip() or default_memory_vault_id(memory_vault_path)
    qmd_context = f"Official {memory_vault_name} memory base at {memory_vault_path}"
    if memory_vault_id:
        qmd_context += f" (vault id: {memory_vault_id})"
    install_home_skills = resolve_home_skill_install(args)
    g_kade_runtime = repo_runtime_dependency_status(workspace_root, "g-kade", args.g_kade_dependency_path)
    gstack_runtime = repo_runtime_dependency_status(workspace_root, "gstack", args.gstack_dependency_path)
    qmd_local_candidates = [
        relative_or_absolute_path(candidate, workspace_root)
        for candidate in qmd_managed_candidates(workspace_root, home_root, install_scope)
    ]
    brv_local_candidates = [
        relative_or_absolute_path(candidate, workspace_root)
        for candidate in brv_managed_candidates(workspace_root, home_root, install_scope)
    ]
    obsidian_local_candidates = [
        relative_or_absolute_path(candidate, workspace_root)
        for candidate in obsidian_managed_candidates(workspace_root, home_root, install_scope)
    ]
    gitvizz_checkout = args.gitvizz_checkout_path or relative_or_absolute_path(managed_root / "gitvizz", workspace_root)
    qmd_source_checkout = qmd_source_checkout_path(getattr(args, "qmd_source_checkout", ""))

    return {
        "version": 1,
        "tooling": {
            "install_scope": install_scope,
            "managed_tool_root": relative_or_absolute_path(managed_root, workspace_root),
        },
        "toolset": {
            "cli": {
                "python": "scripts/llm_wiki_packet.py",
                "powershell": "scripts/llm_wiki_packet.ps1",
                "shell": "scripts/llm_wiki_packet.sh",
                "cmd": "scripts/llm_wiki_packet.cmd",
            },
            "preferred_project_bootstrap_command": "init",
            "preferred_project_runtime_commands": [
                "setup",
                "check",
                "context",
                "evidence",
                "manifest",
                "reduce",
                "evaluate",
                "promote",
                "improve",
                "pokemon-benchmark",
            ],
        },
        "memory_base": {
            "name": memory_vault_name,
            "vault_path": str(memory_vault_path),
            "vault_id": memory_vault_id,
        },
        "obsidian": {
            "mcp_server_key": "obsidian",
            "package_name": DEFAULT_OBSIDIAN_PACKAGE,
            "wrapper_script_path": "scripts/llm_wiki_obsidian_mcp.py",
            "install_root": relative_or_absolute_path(managed_root / "obsidian-mcp", workspace_root),
            "local_command_candidates": obsidian_local_candidates,
            "vault_path": str(memory_vault_path),
        },
        "stack": {
            "retrieval": {
                "primary": "pk-qmd",
                "memory": "byterover",
                "graph": "gitvizz",
            },
            "retrieval_planner": {
                "default_context_mode": "default",
                "default_evidence_plane": "all",
                "planes": ["source", "skills", "preference", "graph", "local"],
                "default_timeout_sec": 20,
                "default_max_results_per_plane": 5,
                "broad_retrieval": "explicit-only",
                "source_precedence": "current source evidence overrides memory",
                "fallback_policy": "degrade to local lexical/config hints without blocking task completion",
            },
            "policy": {
                "hide_tool_names_from_end_users": True,
                "prefer_source_evidence_over_memory": True,
                "qmd_for_repo_specific_tasks": True,
                "brv_for_durable_preferences_and_decisions": True,
                "skills_for_reusable_execution_shortcuts": True,
            },
        },
        "docs": {
            "contract_path": "SYSTEM_CONTRACT.md",
            "known_issues_path": "KNOWN_ISSUES.md",
        },
        "agent_runtimes": {
            "packet_wrappers": {
                "kade-hq": {
                    "owner": PACKET_OWNER,
                    "source_path": "skills/home/kade-hq",
                    "status": "home-install-enabled" if install_home_skills else "available-home-install-opt-in",
                    "manual_install_required": False,
                },
                "g-kade": {
                    "owner": PACKET_OWNER,
                    "source_path": "skills/home/g-kade",
                    "status": "home-install-enabled" if install_home_skills else "available-home-install-opt-in",
                    "manual_install_required": False,
                },
                "gstack": {
                    "owner": PACKET_OWNER,
                    "source_path": "skills/home/gstack",
                    "status": "home-install-enabled" if install_home_skills else "available-home-install-opt-in",
                    "manual_install_required": False,
                },
                "llm-wiki-skills": {
                    "owner": PACKET_OWNER,
                    "source_path": "skills/home/llm-wiki-skills",
                    "status": "home-install-enabled" if install_home_skills else "available-home-install-opt-in",
                    "manual_install_required": False,
                },
            },
            "repo_dependencies": {
                "g-kade": g_kade_runtime,
                "gstack": gstack_runtime,
            },
            "source_of_truth": {
                "submodule_path": PK_SKILLS_SUBMODULE_PATH,
                "repo_url": PK_SKILLS_REPO_URL,
            },
        },
        "pk_qmd": {
            "command": args.qmd_command,
            "local_command_candidates": qmd_local_candidates,
            "repo_url": args.qmd_repo_url,
            "repo_ref": args.qmd_repo_ref,
            "checkout_path": relative_or_absolute_path(managed_root / "pk-qmd", workspace_root),
            "source_checkout_path": (
                relative_or_absolute_path(qmd_source_checkout, workspace_root)
                if qmd_source_checkout
                else ""
            ),
            "config_dir": ".llm-wiki/qmd-config",
            "manual_install_required": False,
            "global_install_allowed": global_tool_install_allowed(args),
            "mcp_url": qmd_mcp_url,
            "collection_name": memory_vault_name,
            "context": qmd_context,
            "source_path": str(memory_vault_path),
            "local_dependency_manifest": STACK_DEPENDENCY_MANIFEST_PATH,
        },
        "byterover": {
            "command": args.brv_command,
            "install_root": relative_or_absolute_path(managed_root / "brv", workspace_root),
            "local_command_candidates": brv_local_candidates,
            "package_name": DEFAULT_BRV_PACKAGE,
            "global_install_allowed": global_tool_install_allowed(args),
            "api_key_env": "BYTEROVER_API_KEY",
            "working_dir": ".brv",
            "context_tree_dir": ".brv/context-tree",
            "default_provider": "openrouter",
            "default_model": "google/gemini-3.1-flash-lite-preview",
            "query_experiment_provider": "google",
            "query_experiment_model": "google/gemini-3.1-flash-lite-preview",
            "curate_preferred_provider": "openrouter",
            "curate_preferred_model": "google/gemini-3.1-flash-lite-preview",
            "candidate_models": [
                "google/gemini-3.1-flash-lite-preview",
                "openai/gpt-oss-safeguard-20b",
                "x-ai/grok-4.20-multi-agent",
                "liquid/lfm-2.5-1.2b-thinking:free",
                "openai/gpt-5-nano",
                "arcee-ai/trinity-large-thinking",
            ],
            "query_format": "json",
            "curate_format": "json",
        },
        "gitvizz": {
            "frontend_url": frontend_url,
            "backend_url": backend_url,
            "api_base_url": f"{backend_url}/api",
            "homepage_url": f"{frontend_url}/",
            "setup_url": f"{frontend_url}/",
            "github_callback_url": f"{frontend_url}/api/auth/callback/github",
            "repo_url": args.gitvizz_repo_url or None,
            "checkout_path": gitvizz_checkout,
            "repo_path": args.gitvizz_repo_path or None,
        },
        "skills": {
            "mcp_server_key": "llm-wiki-skills",
            "script_path": "scripts/llm_wiki_skill_mcp.py",
            "failure_collector_script_path": "scripts/llm_wiki_failure_collector.py",
            "failure_hook_script_path": "scripts/llm_wiki_failure_hook.py",
            "registry_path": ".llm-wiki/skills-registry.json",
            "index_path": "wiki/skills/index.md",
            "log_path": "wiki/log.md",
            "active_dir": "wiki/skills/active",
            "feedback_dir": "wiki/skills/feedback",
            "retired_dir": "wiki/skills/retired",
            "retire_below_score": -3,
            "pipeline": {
                "pipeline_dir": ".llm-wiki/skill-pipeline",
                "brief_dir": ".llm-wiki/skill-pipeline/briefs",
                "delta_dir": ".llm-wiki/skill-pipeline/deltas",
                "validation_dir": ".llm-wiki/skill-pipeline/validations",
                "packet_dir": ".llm-wiki/skill-pipeline/packets",
                "run_dir": ".llm-wiki/skill-pipeline/runs",
                "proposal_dir": ".llm-wiki/skill-pipeline/proposals",
                "surrogate_review_dir": ".llm-wiki/skill-pipeline/surrogate-reviews",
                "evolution_run_dir": ".llm-wiki/skill-pipeline/evolution-runs",
                "frontier_path": ".llm-wiki/skill-pipeline/frontier.json",
                "failure_dir": ".llm-wiki/skill-pipeline/failures",
                "failure_event_dir": ".llm-wiki/skill-pipeline/failures/events",
                "failure_cluster_dir": ".llm-wiki/skill-pipeline/failures/clusters",
                "failure_benchmark_dir": ".llm-wiki/skill-pipeline/failures/benchmarks",
                "min_validation_score": 7,
                "dedupe_similarity_threshold": 0.72,
                "auto_merge_duplicates": True,
                "long_task_brief_min_chars": 280,
                "max_hops_default": 2,
                "max_retries_default": 1,
                "enforce_summary_only": True,
                "frontier_size": 3,
                "min_frontier_delta": 1,
                "surrogate_fail_blocks": True,
                "failure_auto_promote": True,
                "failure_promotion_threshold": 3,
                "failure_promotion_window_hours": 168,
                "failure_promotion_min_unique_sessions": 2,
            },
        },
        "agent_failure_capture": {
            "script_path": "scripts/llm_wiki_agent_failure_capture.py",
            "launcher_paths": {
                "powershell": "scripts/run_llm_wiki_agent.ps1",
                "shell": "scripts/run_llm_wiki_agent.sh",
                "cmd": "scripts/run_llm_wiki_agent.cmd",
            },
            "wrapper_supported_agents": ["claude", "codex", "droid", "pi"],
            "native_hook_agents": ["claude"],
            "commands": {
                "claude": "claude",
                "codex": "codex",
                "droid": "droid",
                "pi": "pi",
            },
        },
    }


def build_stack_dependency_manifest(args: argparse.Namespace) -> dict[str, object]:
    return {
        "name": "llm-wiki-memory-local-tools",
        "private": True,
        "version": "0.1.0",
        "description": "Managed local dependency bundle for llm-wiki-memory",
        "dependencies": {
            "@kingkillery/pk-qmd": qmd_package_spec(args.qmd_repo_url, getattr(args, "qmd_repo_ref", DEFAULT_QMD_REPO_REF)),
            DEFAULT_BRV_PACKAGE: "^3.3.0",
            DEFAULT_OBSIDIAN_PACKAGE: "^0.11.0",
        },
    }


def install_packet_workspace(
    vault: Path,
    targets: list[str],
    home_root: Path,
    *,
    force: bool,
    dry_run: bool,
    skip_home_skills: bool,
    args: argparse.Namespace,
) -> list[str]:
    actions: list[str] = []
    actions.extend(bootstrap_vault(vault, force=force, dry_run=dry_run))

    actions.extend(install_map(vault, ROOT_FILES, force=force, dry_run=dry_run))
    actions.append(ensure_agents_guidance(vault, dry_run=dry_run))

    if "claude" in targets:
        actions.extend(install_map(vault, CLAUDE_FILES, force=force, dry_run=dry_run))

    if "antigravity" in targets:
        actions.extend(install_map(vault, ANTIGRAVITY_FILES, force=force, dry_run=dry_run))

    if "codex" in targets:
        actions.extend(install_map(vault, CODEX_FILES, force=force, dry_run=dry_run))

    actions.extend(install_map(vault, STACK_FILES, force=force, dry_run=dry_run))
    actions.append(
        write_stack_config(vault / STACK_CONFIG_PATH, build_stack_config(args), force=force, dry_run=dry_run)
    )
    actions.append(
        write_json(vault / STACK_DEPENDENCY_MANIFEST_PATH, build_stack_dependency_manifest(args), force=force, dry_run=dry_run)
    )

    if skip_home_skills:
        actions.append("info   Packet-owned home skill install skipped")
    else:
        actions.extend(install_home_skills(home_root, force=force, dry_run=dry_run))

    if "droid" in targets:
        actions.append("info   Droid target uses root AGENTS.md")
    if "pi" in targets:
        actions.append("info   pi target uses root AGENTS.md plus the shared agent failure wrapper")

    return actions


def packet_required_paths(vault: Path) -> list[Path]:
    return [
        vault / "AGENTS.md",
        vault / "CLAUDE.md",
        vault / "LLM_WIKI_MEMORY.md",
        vault / "SYSTEM_CONTRACT.md",
        vault / "KNOWN_ISSUES.md",
        vault / STACK_CONFIG_PATH,
        vault / "scripts" / "llm_wiki_packet.py",
        vault / "scripts" / "llm_wiki_packet.ps1",
        vault / "scripts" / "llm_wiki_packet.sh",
        vault / "scripts" / "llm_wiki_packet.cmd",
        vault / "scripts" / "llm_wiki_memory_runtime.py",
        vault / "scripts" / "llm_wiki_obsidian_mcp.py",
        vault / "scripts" / "llm_wiki_failure_hook.py",
        vault / "scripts" / "llm_wiki_agent_failure_capture.py",
        vault / "scripts" / "pokemon_benchmark_adapter.py",
        vault / "scripts" / "run_llm_wiki_agent.ps1",
        vault / "scripts" / "run_llm_wiki_agent.sh",
        vault / "scripts" / "run_llm_wiki_agent.cmd",
        vault / "scripts" / "run_pokemon_benchmark.ps1",
        vault / "scripts" / "setup_llm_wiki_memory.ps1",
        vault / "scripts" / "setup_llm_wiki_memory.sh",
        vault / "scripts" / "setup_llm_wiki_memory.cmd",
        vault / "scripts" / "check_llm_wiki_memory.ps1",
        vault / "scripts" / "check_llm_wiki_memory.sh",
        vault / "scripts" / "check_llm_wiki_memory.cmd",
    ]


def main() -> int:
    args = parse_args()
    vault = Path(args.vault).expanduser().resolve()
    home_root = Path(args.home_root).expanduser().resolve()
    targets = normalize_targets(args.targets)
    install_home_skills = resolve_home_skill_install(args)
    skip_home_skills = not install_home_skills
    allow_home_root = args.allow_home_root or env_flag("LLM_WIKI_ALLOW_HOME_ROOT")

    if not vault.exists():
        raise SystemExit(f"Vault does not exist: {vault}")
    if not vault.is_dir():
        raise SystemExit(f"Vault is not a directory: {vault}")

    ensure_safe_install_root(vault, home_root, allow_home_root=allow_home_root)

    preflight = build_preflight_report(
        vault,
        home_root,
        install_home_skills=install_home_skills,
        run_setup=False,
        allow_global_tool_install=global_tool_install_allowed(args),
        install_scope=normalize_install_scope(getattr(args, "install_scope", DEFAULT_INSTALL_SCOPE)),
        g_kade_dependency_path=args.g_kade_dependency_path,
        gstack_dependency_path=args.gstack_dependency_path,
        qmd_source_checkout=args.qmd_source_checkout,
    )

    if args.preflight_only:
        print("\n".join([f"Vault:   {vault}", f"Home:    {home_root}", f"Targets: {', '.join(targets)}", "Mode:    preflight", "", *preflight]))
        return 0

    actions = install_packet_workspace(
        vault,
        targets,
        home_root,
        force=args.force,
        dry_run=args.dry_run,
        skip_home_skills=skip_home_skills,
        args=args,
    )

    summary = [
        f"Vault:   {vault}",
        f"Home:    {home_root}",
        f"Targets: {', '.join(targets)}",
        f"Mode:    {'dry-run' if args.dry_run else 'write'}",
        "",
        *preflight,
        "",
        *actions,
    ]
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
