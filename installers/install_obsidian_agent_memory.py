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

TARGETS_ALL = ("claude", "antigravity", "codex", "droid")
STACK_CONFIG_PATH = ".llm-wiki/config.json"
STACK_DEPENDENCY_MANIFEST_PATH = ".llm-wiki/package.json"
STACK_GITIGNORE_PATH = ".llm-wiki/.gitignore"
PACKET_OWNER = "llm-wiki-prompt-packet"
HOME_SKILL_OWNER_MARKER = ".llm-wiki-packet-owner.json"
RICH_MARKERS = {"bin", "browse", "qa", "review", "kade"}
RICH_SIBLING_HINTS = {"debug", "debugging", "deploy", "deployment", "design", "dogfood", "dx", "investigate", "ship", "workflows"}
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

ROOT_FILES = {
    "AGENTS.md": PROMPTS / "01-AGENTS.md",
    "CLAUDE.md": PROMPTS / "02-CLAUDE.md",
    "LLM_WIKI_MEMORY.md": SUPPORT / "LLM_WIKI_MEMORY.md",
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
    "scripts/llm_wiki_skill_mcp.py": SUPPORT / "scripts" / "llm_wiki_skill_mcp.py",
    "scripts/setup_llm_wiki_memory.ps1": SUPPORT / "scripts" / "setup_llm_wiki_memory.ps1",
    "scripts/setup_llm_wiki_memory.sh": SUPPORT / "scripts" / "setup_llm_wiki_memory.sh",
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
    ".llm-wiki/.gitignore": "node_modules/\npackage-lock.json\n",
    ".llm-wiki/skills-registry.json": "{\n  \"skills\": {},\n  \"feedback\": [],\n  \"briefs\": [],\n  \"deltas\": [],\n  \"validations\": [],\n  \"packets\": [],\n  \"events\": []\n}\n",
    ".llm-wiki/skill-pipeline/.gitkeep": "",
    ".llm-wiki/skill-pipeline/briefs/.gitkeep": "",
    ".llm-wiki/skill-pipeline/deltas/.gitkeep": "",
    ".llm-wiki/skill-pipeline/validations/.gitkeep": "",
    ".llm-wiki/skill-pipeline/packets/.gitkeep": "",
    ".brv/.gitkeep": "",
    ".brv/context-tree/.gitkeep": "",
    ".llm-wiki/qmd-embed-state.json": "{\n  \"status\": \"not-run\"\n}\n",
}

HOME_SKILL_TARGETS = {
    ".agents/skills/gstack": HOME_SKILLS_ROOT / "gstack",
    ".agents/skills/g-kade": HOME_SKILLS_ROOT / "g-kade",
    ".codex/skills/gstack": HOME_SKILLS_ROOT / "gstack",
    ".codex/skills/g-kade": HOME_SKILLS_ROOT / "g-kade",
    ".claude/skills/gstack": HOME_SKILLS_ROOT / "gstack",
    ".claude/skills/g-kade": HOME_SKILLS_ROOT / "g-kade",
}

DANGEROUS_HOME_TARGETS = (
    ".agents",
    ".agents/skills",
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


def env_flag(name: str) -> bool:
    value = os.getenv(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, help="Path to the Obsidian vault")
    parser.add_argument(
        "--targets",
        default="claude,antigravity,codex,droid",
        help="Comma-separated targets: claude,antigravity,codex,droid",
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
        help="Install packet-owned wrapper skills into ~/.agents, ~/.codex, and ~/.claude",
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
        default=env_or_default("LLM_WIKI_GITVIZZ_REPO_URL", ""),
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


def local_qmd_candidates(vault: Path) -> list[Path]:
    return [
        vault / ".llm-wiki" / "node_modules" / ".bin" / "pk-qmd",
        vault / ".llm-wiki" / "node_modules" / ".bin" / "pk-qmd.cmd",
        vault / ".llm-wiki" / "node_modules" / ".bin" / "pk-qmd.ps1",
        vault / ".llm-wiki" / "node_modules" / "@kingkillery" / "pk-qmd" / "dist" / "cli" / "qmd.js",
    ]


def local_brv_candidates(vault: Path) -> list[Path]:
    return [
        vault / ".llm-wiki" / "node_modules" / ".bin" / "brv",
        vault / ".llm-wiki" / "node_modules" / ".bin" / "brv.cmd",
        vault / ".llm-wiki" / "node_modules" / ".bin" / "brv.ps1",
    ]


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
    g_kade_dependency_path: str,
    gstack_dependency_path: str,
) -> list[str]:
    node = shutil.which("node")
    npm = shutil.which("npm")
    git = shutil.which("git")
    docker = shutil.which("docker")
    local_qmd = first_existing(local_qmd_candidates(vault))
    local_brv = first_existing(local_brv_candidates(vault))
    global_qmd = shutil.which("pk-qmd")
    global_brv = shutil.which("brv")
    g_kade_runtime = repo_runtime_dependency_status(vault, "g-kade", g_kade_dependency_path)
    gstack_runtime = repo_runtime_dependency_status(vault, "gstack", gstack_dependency_path)

    lines = [
        "Preflight:",
        f"preflight target-root: {vault}",
        f"preflight home-root: {home_root}",
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
    ]

    if local_qmd:
        lines.append(f"preflight pk-qmd: packet-local {local_qmd}")
    elif global_qmd:
        lines.append(f"preflight pk-qmd: global {global_qmd}")
    elif run_setup and npm:
        lines.append("preflight pk-qmd: missing (setup can install packet-local)")
    else:
        lines.append("preflight pk-qmd: missing (install npm before running setup)")

    if local_brv:
        lines.append(f"preflight brv: packet-local {local_brv}")
    elif global_brv:
        lines.append(f"preflight brv: global {global_brv}")
    elif run_setup and npm:
        fallback = "packet-local preferred"
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
    vault_name = workspace_root.name.lower().replace(" ", "-")
    qmd_context = f"Primary llm-wiki-memory vault for {workspace_root}"
    install_home_skills = resolve_home_skill_install(args)
    g_kade_runtime = repo_runtime_dependency_status(workspace_root, "g-kade", args.g_kade_dependency_path)
    gstack_runtime = repo_runtime_dependency_status(workspace_root, "gstack", args.gstack_dependency_path)

    return {
        "version": 1,
        "stack": {
            "retrieval": {
                "primary": "pk-qmd",
                "memory": "byterover",
                "graph": "gitvizz",
            },
            "policy": {
                "hide_tool_names_from_end_users": True,
                "prefer_source_evidence_over_memory": True,
                "qmd_for_repo_specific_tasks": True,
                "brv_for_durable_preferences_and_decisions": True,
                "skills_for_reusable_execution_shortcuts": True,
            },
        },
        "agent_runtimes": {
            "packet_wrappers": {
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
            },
            "repo_dependencies": {
                "g-kade": g_kade_runtime,
                "gstack": gstack_runtime,
            },
        },
        "pk_qmd": {
            "command": args.qmd_command,
            "local_command_candidates": [
                ".llm-wiki/node_modules/.bin/pk-qmd",
                ".llm-wiki/node_modules/.bin/pk-qmd.cmd",
                ".llm-wiki/node_modules/.bin/pk-qmd.ps1",
            ],
            "repo_url": args.qmd_repo_url,
            "manual_install_required": False,
            "global_install_allowed": global_tool_install_allowed(args),
            "mcp_url": qmd_mcp_url,
            "collection_name": vault_name,
            "context": qmd_context,
            "local_dependency_manifest": STACK_DEPENDENCY_MANIFEST_PATH,
        },
        "byterover": {
            "command": args.brv_command,
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
            "checkout_path": args.gitvizz_checkout_path or args.gitvizz_repo_path or None,
            "repo_path": args.gitvizz_repo_path or None,
        },
        "skills": {
            "mcp_server_key": "llm-wiki-skills",
            "script_path": "scripts/llm_wiki_skill_mcp.py",
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
                "min_validation_score": 7,
                "dedupe_similarity_threshold": 0.72,
                "auto_merge_duplicates": True,
                "long_task_brief_min_chars": 280,
                "max_hops_default": 2,
                "max_retries_default": 1,
                "enforce_summary_only": True,
            },
        },
    }


def build_stack_dependency_manifest(args: argparse.Namespace) -> dict[str, object]:
    repo_url = args.qmd_repo_url
    dependency_spec = repo_url if repo_url.startswith("git+") else f"git+{repo_url}.git" if repo_url.startswith("https://github.com/") and not repo_url.endswith(".git") else f"git+{repo_url}" if repo_url.startswith("https://") else repo_url
    if dependency_spec.endswith(".git.git"):
        dependency_spec = dependency_spec[:-4]

    return {
        "name": "llm-wiki-memory-local",
        "private": True,
        "version": "0.1.0",
        "description": "Local dependency bundle for llm-wiki-memory",
        "dependencies": {
            "@kingkillery/pk-qmd": dependency_spec,
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

    if "claude" in targets:
        actions.extend(install_map(vault, CLAUDE_FILES, force=force, dry_run=dry_run))

    if "antigravity" in targets:
        actions.extend(install_map(vault, ANTIGRAVITY_FILES, force=force, dry_run=dry_run))

    if "codex" in targets:
        actions.extend(install_map(vault, CODEX_FILES, force=force, dry_run=dry_run))

    actions.extend(install_map(vault, STACK_FILES, force=force, dry_run=dry_run))
    actions.append(
        write_json(vault / STACK_CONFIG_PATH, build_stack_config(args), force=force, dry_run=dry_run)
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

    return actions


def packet_required_paths(vault: Path) -> list[Path]:
    return [
        vault / "AGENTS.md",
        vault / "CLAUDE.md",
        vault / "LLM_WIKI_MEMORY.md",
        vault / STACK_CONFIG_PATH,
        vault / "scripts" / "setup_llm_wiki_memory.ps1",
        vault / "scripts" / "setup_llm_wiki_memory.sh",
        vault / "scripts" / "check_llm_wiki_memory.ps1",
        vault / "scripts" / "check_llm_wiki_memory.sh",
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
        g_kade_dependency_path=args.g_kade_dependency_path,
        gstack_dependency_path=args.gstack_dependency_path,
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
