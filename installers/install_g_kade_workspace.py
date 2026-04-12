#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_INSTALLER_PATH = Path(__file__).resolve().parent / "install_obsidian_agent_memory.py"

SKILL_LAYOUTS = (".agents", ".codex", ".claude")
LEGACY_HUMAN_MD_TEXT = (
    "# HUMAN.md\n\n"
    "This is the global KADE human profile.\n\n"
    "- preferred style: concise, checkpoint-driven, direct\n"
    "- expectation: keep one next action visible\n"
    "- note: replace this starter with real user-specific guidance\n"
)
HUMAN_MD_SOURCE_CANDIDATES = (
    REPO_ROOT / "deps" / "pk-skills1" / "kade-headquarters" / "HUMAN.md",
    REPO_ROOT / "deps" / "pk-skills1" / "kade-hq" / "templates" / "HUMAN.md",
)


def load_packet_installer():
    spec = importlib.util.spec_from_file_location("install_obsidian_agent_memory", PACKET_INSTALLER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PACKET = load_packet_installer()


def env_flag(name: str) -> bool:
    value = os.getenv(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_g_kade_home_skill_install(args: argparse.Namespace) -> bool:
    explicit = (
        getattr(args, "install_home_skills", False)
        or getattr(args, "skip_home_skills", False)
        or env_flag("LLM_WIKI_INSTALL_HOME_SKILLS")
        or env_flag("LLM_WIKI_SKIP_HOME_SKILLS")
    )
    if explicit:
        return PACKET.resolve_home_skill_install(args)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace",
        default=os.getenv("G_KADE_WORKSPACE", "."),
        help="Repo root or a path inside the repo to bootstrap",
    )
    parser.add_argument(
        "--targets",
        default=os.getenv("LLM_WIKI_TARGETS", "claude,antigravity,codex,droid"),
        help="Comma-separated packet targets",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite packet-managed files")
    parser.add_argument("--preflight-only", action="store_true", help="Report bootstrap actions without writing files")
    parser.add_argument(
        "--allow-home-root",
        action="store_true",
        help="Allow installing directly into shared home-control paths such as ~ or ~/.agents/skills",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files")
    home_skill_group = parser.add_mutually_exclusive_group()
    home_skill_group.add_argument(
        "--install-home-skills",
        action="store_true",
        help="Install packet-owned wrapper skills into ~/.agents, ~/.codex, and ~/.claude",
    )
    home_skill_group.add_argument(
        "--skip-home-skills",
        action="store_true",
        help="Skip packet-owned home skill install into the chosen home root",
    )
    parser.add_argument(
        "--home-root",
        default=os.getenv("LLM_WIKI_HOME_ROOT", str(Path.home())),
        help="Home directory used for optional home skill installs and ~/.kade overlays",
    )
    parser.add_argument(
        "--install-scope",
        default=PACKET.default_install_scope(),
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
        "--skip-setup",
        action="store_true",
        help="Skip running setup and health helpers after installing files",
    )
    parser.add_argument(
        "--qmd-command",
        default=os.getenv("LLM_WIKI_QMD_COMMAND", "pk-qmd"),
        help="Command name for the custom QMD fork",
    )
    parser.add_argument(
        "--qmd-repo-url",
        default=os.getenv("LLM_WIKI_QMD_REPO_URL", "https://github.com/kingkillery/pk-qmd"),
        help="Packet fallback source for the custom pk-qmd fork",
    )
    parser.add_argument(
        "--qmd-mcp-url",
        default=os.getenv("LLM_WIKI_QMD_MCP_URL", "http://localhost:8181/mcp"),
        help="HTTP MCP endpoint for the shared pk-qmd server",
    )
    parser.add_argument(
        "--brv-command",
        default=os.getenv("LLM_WIKI_BRV_COMMAND", "brv"),
        help="Command name for the Byterover CLI",
    )
    parser.add_argument(
        "--gitvizz-frontend-url",
        default=os.getenv("LLM_WIKI_GITVIZZ_FRONTEND_URL", "http://localhost:3000"),
        help="Frontend URL for the GitVizz web app",
    )
    parser.add_argument(
        "--gitvizz-backend-url",
        default=os.getenv("LLM_WIKI_GITVIZZ_BACKEND_URL", "http://localhost:8003"),
        help="Backend URL for the GitVizz API service",
    )
    parser.add_argument(
        "--gitvizz-repo-path",
        default=os.getenv("LLM_WIKI_GITVIZZ_REPO_PATH", ""),
        help="Optional GitVizz checkout path",
    )
    parser.add_argument(
        "--gitvizz-repo-url",
        default=os.getenv("LLM_WIKI_GITVIZZ_REPO_URL", PACKET.DEFAULT_GITVIZZ_REPO_URL),
        help="Optional GitVizz repo URL for managed local acquisition",
    )
    parser.add_argument(
        "--gitvizz-checkout-path",
        default=os.getenv("LLM_WIKI_GITVIZZ_CHECKOUT_PATH", ""),
        help="Optional managed local checkout path for GitVizz acquisition or update",
    )
    parser.add_argument(
        "--g-kade-dependency-path",
        default=os.getenv("LLM_WIKI_G_KADE_DEPENDENCY_PATH", PACKET.REPO_RUNTIME_DEFAULT_PATHS["g-kade"]),
        help="Repo-owned richer g-kade dependency, submodule, or vendor path relative to the workspace",
    )
    parser.add_argument(
        "--gstack-dependency-path",
        default=os.getenv("LLM_WIKI_GSTACK_DEPENDENCY_PATH", PACKET.REPO_RUNTIME_DEFAULT_PATHS["gstack"]),
        help="Repo-owned richer gstack dependency, submodule, or vendor path relative to the workspace",
    )
    parser.add_argument(
        "--memory-vault-path",
        default=os.getenv("LLM_WIKI_MEMORY_VAULT_PATH", ""),
        help="Official Obsidian memory-base vault path used for pk-qmd traversal and long-term system memory",
    )
    parser.add_argument(
        "--memory-vault-name",
        default=os.getenv("LLM_WIKI_MEMORY_VAULT_NAME", ""),
        help="Stable name for the official memory-base vault",
    )
    parser.add_argument(
        "--memory-vault-id",
        default=os.getenv("LLM_WIKI_MEMORY_VAULT_ID", ""),
        help="Stable vault identifier for the official memory-base vault",
    )
    return parser.parse_args()


def detect_workspace_root(start: Path) -> Path:
    start = start.expanduser().resolve()
    probe = start if start.is_dir() else start.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return probe
    root = result.stdout.strip()
    return Path(root).resolve() if root else probe


def read_skill_summary(skill_md: Path | None) -> str:
    if skill_md is None:
        return "not detected"
    try:
        text = skill_md.read_text(encoding="utf-8").strip()
    except OSError:
        return "unreadable"

    if not text:
        return "empty"

    lines = [line.strip() for line in text.splitlines()]
    filtered: list[str] = []
    in_front_matter = False
    front_matter_seen = 0
    for line in lines:
        if line == "---":
            front_matter_seen += 1
            in_front_matter = front_matter_seen == 1
            if front_matter_seen >= 2:
                in_front_matter = False
            continue
        if in_front_matter or not line:
            continue
        filtered.append(line)
        if len(filtered) >= 3:
            break

    summary = " ".join(filtered) if filtered else text[:200]
    return summary[:240]


def repo_runtime_dependency(workspace_root: Path, name: str, configured_path: str) -> dict[str, object]:
    status = PACKET.repo_runtime_dependency_status(workspace_root, name, configured_path)
    detected_path = status.get("detected_path")
    detected_root = PACKET.workspace_relative_path(workspace_root, str(detected_path)) if detected_path else None
    skill_md = (detected_root / "SKILL.md").resolve() if detected_root and (detected_root / "SKILL.md").exists() else None
    return {
        **status,
        "root": detected_root.resolve() if detected_root and detected_root.exists() else detected_root,
        "skill_md": skill_md,
        "summary": read_skill_summary(skill_md),
    }


def layering_result(gkade: dict[str, object], gstack: dict[str, object]) -> str:
    statuses = {gkade["name"]: gkade["status"], gstack["name"]: gstack["status"]}
    if statuses["g-kade"] == "detected" and statuses["gstack"] == "detected":
        return "packet wrappers plus repo-owned g-kade and gstack runtimes"
    if statuses["g-kade"] == "detected":
        return "packet wrappers plus repo-owned g-kade runtime"
    if statuses["gstack"] == "detected":
        return "packet wrappers plus repo-owned gstack runtime"
    if "present-but-thin" in statuses.values():
        return "packet wrappers plus thin repo dependency placeholders"
    return "packet wrappers only (repo runtimes missing)"


def runtime_guidance_lines(runtime: dict[str, object]) -> list[str]:
    lines = [
        f"- contract: `{runtime['contract']}`",
        f"- configured path: `{runtime['configured_path']}`",
    ]
    if runtime["status"] == "detected":
        lines.extend(
            [
                f"- status: `detected`",
                f"- detected path: `{runtime['detected_path']}`",
                f"- markers: `{', '.join(runtime.get('markers', []))}`",
                f"- summary: `{runtime['summary']}`",
            ]
        )
    elif runtime["status"] == "present-but-thin":
        lines.extend(
            [
                f"- status: `present-but-thin`",
                f"- detected path: `{runtime['detected_path']}`",
                f"- note: `{runtime.get('reason', 'wrapper-like or incomplete runtime')}`",
            ]
        )
    else:
        lines.extend(
            [
                f"- status: `missing`",
                "- note: `packet wrapper installed; richer repo-owned runtime still needs to be vendored or added as a submodule/dependency`",
            ]
        )
    return lines


def repo_skill_text(name: str, workspace_root: Path, runtime: dict[str, object]) -> str:
    if name == "kade-hq":
        description = "Repo-local KADE System surface layered on top of the llm-wiki-memory packet."
        workflow_lines = [
            "- load Layer 1 from ~/.kade/HUMAN.md when present",
            "- load Layer 2 from kade/AGENTS.md and kade/KADE.md",
            "- preserve the packet root files as the workspace contract",
            "- use g-kade only as the bridge and router across kade-hq plus gstack",
            "- use gstack for execution workflows such as review, QA, debugging, and ship",
        ]
        runtime_block = "\n".join(
            [
                "- contract: `KADE System launcher surface for this repo workspace`",
                "- configured path: `kade/ + ~/.kade + packet root files`",
                "- status: `managed by the workspace installer`",
                "- note: `g-kade is only the unifier skill; install and preserve kade-hq separately from gstack`",
            ]
        )
        install_notes = []
    elif name == "g-kade":
        description = "Repo-local KADE bridge layered on top of the llm-wiki-memory packet."
        workflow_lines = [
            "- treat this repo root as the workspace root",
            "- treat g-kade as the unifier surface only; install and preserve kade-hq plus gstack separately",
            "- prefer packet helpers for search, memory, and MCP wiring",
            "- use `kade/AGENTS.md` and `kade/KADE.md` as the project overlay",
            "- if the richer repo-owned runtime is present, read it before routing work",
        ]
        install_notes = [
            "## Fastest Successful Install",
            "",
            "- run `python installers/install_g_kade_workspace.py --workspace <repo-root>` from the packet checkout when available",
            "- if using the hosted installer fallback, set `LLM_WIKI_INSTALL_MODE=g-kade` before invoking `install.sh` or `install.ps1`",
            "- vendor or submodule the richer runtime into the configured repo dependency path before claiming the full KADE/G-Stack runtime is available",
            "- let setup and health run with GitVizz skipped until a real GitVizz repo path is configured",
            "",
            "## Roadblocks And Corrections",
            "",
            "- packet file copy alone is not enough; this workspace also needs repo-local skill surfaces, KADE overlays, repo-owned runtime dependencies, setup, and health verification",
            "- home skill installs are optional overlays, not proof the repo is bootstrapped",
            "- thin wrappers do not count as richer repo-owned runtimes",
            "",
            "## Wish I Knew Before Install",
            "",
            "- `xyz`: the repo root is the real workspace target",
            "- `xyz`: `/g-kade install` must keep going after packet file install",
            "- `xyz`: the richer runtime belongs in a repo-owned dependency/submodule path, not just a home skill folder",
            "- `xyz`: GitVizz should not block first-run QMD, BRV, and MCP bootstrap",
        ]
    else:
        description = "Repo-local gstack workflow surface layered on top of the llm-wiki-memory packet."
        workflow_lines = [
            "- QA",
            "- browser dogfooding",
            "- code review",
            "- debugging and investigation",
            "- ship and PR prep",
            "- design and DX review",
            "- deployment verification",
            "- verify external binaries before invoking them and fall back to native tools when absent",
        ]
        install_notes = []

    workflow_block = "\n".join(workflow_lines)
    if name != "kade-hq":
        runtime_block = "\n".join(runtime_guidance_lines(runtime))

    return (
        f"---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"---\n\n"
        f"# {name}\n\n"
        f"This is the repo-local `{name}` surface for the packet-backed workspace rooted at `{workspace_root}`.\n\n"
        f"## Repo Runtime Dependency\n\n"
        f"{runtime_block}\n\n"
        f"## Local Routing\n\n"
        f"{workflow_block}\n\n"
        f"Do not treat global skill installs as sufficient for this repo. Use the packet root files, `.llm-wiki/config.json`, the repo-owned dependency paths, and the repo-local `kade/` overlay as the first-class workspace contract.\n"
        + ("\n" + "\n".join(install_notes) + "\n" if install_notes else "")
    )


def scaffold_repo_local_skills(
    workspace_root: Path,
    *,
    gkade_runtime: dict[str, object],
    gstack_runtime: dict[str, object],
    force: bool,
    dry_run: bool,
) -> list[str]:
    actions: list[str] = []
    for layout in SKILL_LAYOUTS:
        skill_root = workspace_root / layout / "skills"
        actions.extend(
            [
                PACKET.write_text(
                    skill_root / "kade-hq" / "SKILL.md",
                    repo_skill_text("kade-hq", workspace_root, gkade_runtime),
                    force=force,
                    dry_run=dry_run,
                ),
                PACKET.copy_file(
                    PACKET.HOME_SKILLS_ROOT / "kade-hq" / "agents" / "openai.yaml",
                    skill_root / "kade-hq" / "agents" / "openai.yaml",
                    force=force,
                    dry_run=dry_run,
                ),
                PACKET.write_text(
                    skill_root / "g-kade" / "SKILL.md",
                    repo_skill_text("g-kade", workspace_root, gkade_runtime),
                    force=force,
                    dry_run=dry_run,
                ),
                PACKET.copy_file(
                    PACKET.HOME_SKILLS_ROOT / "g-kade" / "agents" / "openai.yaml",
                    skill_root / "g-kade" / "agents" / "openai.yaml",
                    force=force,
                    dry_run=dry_run,
                ),
                PACKET.write_text(
                    skill_root / "gstack" / "SKILL.md",
                    repo_skill_text("gstack", workspace_root, gstack_runtime),
                    force=force,
                    dry_run=dry_run,
                ),
                PACKET.copy_file(
                    PACKET.HOME_SKILLS_ROOT / "gstack" / "agents" / "openai.yaml",
                    skill_root / "gstack" / "agents" / "openai.yaml",
                    force=force,
                    dry_run=dry_run,
                ),
            ]
        )
    return actions


def kade_agents_text(workspace_root: Path, gkade: dict[str, object], gstack: dict[str, object]) -> str:
    runtime_lines = [
        f"- `g-kade`: `{gkade['status']}` at `{gkade['configured_path']}`",
        f"- `gstack`: `{gstack['status']}` at `{gstack['configured_path']}`",
    ]
    if gkade.get("detected_path"):
        runtime_lines.append(f"- detected richer `g-kade`: `{gkade['detected_path']}`")
    if gstack.get("detected_path"):
        runtime_lines.append(f"- detected richer `gstack`: `{gstack['detected_path']}`")

    runtime_block = "\n".join(runtime_lines)
    return (
        "# AGENTS.md\n\n"
        "This `kade/AGENTS.md` file is the KADE overlay for a packet-backed workspace.\n\n"
        "Load order:\n\n"
        "- `~/.kade/HUMAN.md` when present\n"
        "- repo root `AGENTS.md`\n"
        "- repo root `LLM_WIKI_MEMORY.md`\n"
        "- repo root `.llm-wiki/config.json`\n"
        "- this file\n"
        "- `kade/KADE.md`\n\n"
        "Boundaries:\n\n"
        "- packet root files own search, memory, MCP wiring, and workspace scaffolding\n"
        "- this overlay owns KADE-specific session structure and handoff expectations\n"
        "- richer g-kade and gstack runtimes belong in repo-owned dependency paths, not home wrappers alone\n"
        "- do not overwrite root packet files with KADE-specific content\n\n"
        "Repo runtime contract:\n\n"
        f"{runtime_block}\n\n"
        f"Workspace root: `{workspace_root}`\n"
    )


def kade_md_text(workspace_root: Path, layer_result: str, gkade: dict[str, object], gstack: dict[str, object]) -> str:
    runtime_lines = [
        f"- `g-kade`: status `{gkade['status']}`, configured `{gkade['configured_path']}`",
        f"- `gstack`: status `{gstack['status']}`, configured `{gstack['configured_path']}`",
    ]
    if gkade.get("detected_path"):
        runtime_lines.append(f"- `g-kade` detected path: `{gkade['detected_path']}`")
    if gstack.get("detected_path"):
        runtime_lines.append(f"- `gstack` detected path: `{gstack['detected_path']}`")

    runtime_block = "\n".join(runtime_lines)
    return (
        "# KADE.md\n\n"
        "## Workspace\n\n"
        f"- root: `{workspace_root}`\n"
        f"- layering result: `{layer_result}`\n\n"
        "## Repo Runtime Contract\n\n"
        f"{runtime_block}\n\n"
        "## Handoff Log\n\n"
    )


def human_md_text() -> str:
    for candidate in HUMAN_MD_SOURCE_CANDIDATES:
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        normalized = text.replace("\r\n", "\n").strip()
        if normalized:
            return normalized + "\n"
    candidate_list = ", ".join(str(path) for path in HUMAN_MD_SOURCE_CANDIDATES)
    raise FileNotFoundError(
        "Unable to locate the packaged Kade-HQ HUMAN.md profile. "
        f"Checked: {candidate_list}. Initialize deps/pk-skills1 or vendor the Kade-HQ profile before installing."
    )


def has_legacy_human_stub(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return text.replace("\r\n", "\n").strip() == LEGACY_HUMAN_MD_TEXT.strip()


def write_home_human_profile(human_md: Path, *, dry_run: bool) -> str:
    if human_md.exists():
        if not has_legacy_human_stub(human_md):
            return f"skip   {human_md} (exists)"
        profile_text = human_md_text()
        if dry_run:
            return f"write  {human_md} (replace legacy stub)"
        human_md.parent.mkdir(parents=True, exist_ok=True)
        human_md.write_text(profile_text, encoding="utf-8")
        return f"write  {human_md} (replaced legacy stub)"
    return PACKET.write_text(human_md, human_md_text(), force=False, dry_run=dry_run)


def scaffold_kade_overlays(
    workspace_root: Path,
    home_root: Path,
    *,
    layer_result_label: str,
    gkade_runtime: dict[str, object],
    gstack_runtime: dict[str, object],
    install_home_profile: bool,
    force: bool,
    dry_run: bool,
) -> list[str]:
    actions = [
        PACKET.write_text(
            workspace_root / "kade" / "AGENTS.md",
            kade_agents_text(workspace_root, gkade_runtime, gstack_runtime),
            force=force,
            dry_run=dry_run,
        ),
        PACKET.write_text(
            workspace_root / "kade" / "KADE.md",
            kade_md_text(workspace_root, layer_result_label, gkade_runtime, gstack_runtime),
            force=force,
            dry_run=dry_run,
        ),
    ]

    if install_home_profile:
        human_md = home_root / ".kade" / "HUMAN.md"
        actions.append(write_home_human_profile(human_md, dry_run=dry_run))
    return actions


def required_paths(workspace_root: Path) -> list[Path]:
    return [
        workspace_root / "AGENTS.md",
        workspace_root / "CLAUDE.md",
        workspace_root / "LLM_WIKI_MEMORY.md",
        workspace_root / ".llm-wiki" / "config.json",
        workspace_root / "scripts" / "setup_llm_wiki_memory.ps1",
        workspace_root / "scripts" / "setup_llm_wiki_memory.sh",
        workspace_root / ".agents" / "skills" / "kade-hq" / "SKILL.md",
        workspace_root / ".agents" / "skills" / "g-kade" / "SKILL.md",
        workspace_root / ".agents" / "skills" / "gstack" / "SKILL.md",
        workspace_root / ".codex" / "skills" / "kade-hq" / "SKILL.md",
        workspace_root / ".codex" / "skills" / "g-kade" / "SKILL.md",
        workspace_root / ".codex" / "skills" / "gstack" / "SKILL.md",
        workspace_root / ".claude" / "skills" / "kade-hq" / "SKILL.md",
        workspace_root / ".claude" / "skills" / "g-kade" / "SKILL.md",
        workspace_root / ".claude" / "skills" / "gstack" / "SKILL.md",
        workspace_root / "kade" / "AGENTS.md",
        workspace_root / "kade" / "KADE.md",
        workspace_root / "scripts" / "check_llm_wiki_memory.ps1",
        workspace_root / "scripts" / "check_llm_wiki_memory.sh",
    ]


def run_helper(
    workspace_root: Path,
    *,
    helper_kind: str,
    allow_global_tool_install: bool,
) -> tuple[list[str], int]:
    if os.name == "nt":
        script_name = f"{helper_kind}_llm_wiki_memory.ps1"
        helper = workspace_root / "scripts" / script_name
        if helper_kind == "setup":
            command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper), "-SkipGitvizz"]
        else:
            command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper), "-SkipGitvizz"]
    else:
        script_name = f"{helper_kind}_llm_wiki_memory.sh"
        helper = workspace_root / "scripts" / script_name
        if helper_kind == "setup":
            command = ["bash", str(helper), "--skip-gitvizz"]
        else:
            command = ["bash", str(helper), "--skip-gitvizz"]

    env = os.environ.copy()
    if allow_global_tool_install:
        env["LLM_WIKI_ALLOW_GLOBAL_TOOL_INSTALL"] = "1"
    result = subprocess.run(command, cwd=workspace_root, capture_output=True, text=True, env=env)
    output: list[str] = [f"$ {' '.join(command)}"]
    if result.stdout.strip():
        output.extend(result.stdout.strip().splitlines())
    if result.stderr.strip():
        output.extend(result.stderr.strip().splitlines())
    return output, result.returncode


def verify_paths(paths: list[Path]) -> list[str]:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit("Missing expected bootstrap paths:\n" + "\n".join(missing))
    return [f"verified {path}" for path in paths]


def main() -> int:
    args = parse_args()
    workspace_root = detect_workspace_root(Path(args.workspace))
    home_root = Path(args.home_root).expanduser().resolve()
    targets = PACKET.normalize_targets(args.targets)
    install_home_skills = resolve_g_kade_home_skill_install(args)
    skip_home_skills = not install_home_skills
    allow_home_root = args.allow_home_root or env_flag("LLM_WIKI_ALLOW_HOME_ROOT")

    if not workspace_root.exists():
        raise SystemExit(f"Workspace does not exist: {workspace_root}")
    if not workspace_root.is_dir():
        raise SystemExit(f"Workspace is not a directory: {workspace_root}")

    PACKET.ensure_safe_install_root(workspace_root, home_root, allow_home_root=allow_home_root)

    preflight = PACKET.build_preflight_report(
        workspace_root,
        home_root,
        install_home_skills=install_home_skills,
        run_setup=not args.skip_setup,
        allow_global_tool_install=PACKET.global_tool_install_allowed(args),
        install_scope=PACKET.normalize_install_scope(getattr(args, "install_scope", PACKET.DEFAULT_INSTALL_SCOPE)),
        g_kade_dependency_path=args.g_kade_dependency_path,
        gstack_dependency_path=args.gstack_dependency_path,
    )

    if args.preflight_only:
        print(
            "\n".join(
                [
                    f"Workspace root: {workspace_root}",
                    f"Home root:      {home_root}",
                    f"Targets:        {', '.join(targets)}",
                    "Mode:           preflight",
                    "",
                    *preflight,
                ]
            )
        )
        return 0

    gkade_runtime = repo_runtime_dependency(workspace_root, "g-kade", args.g_kade_dependency_path)
    gstack_runtime = repo_runtime_dependency(workspace_root, "gstack", args.gstack_dependency_path)
    layer_result_label = layering_result(gkade_runtime, gstack_runtime)

    packet_args = argparse.Namespace(
        vault=str(workspace_root),
        targets=args.targets,
        force=args.force,
        dry_run=args.dry_run,
        skip_home_skills=skip_home_skills,
        home_root=str(home_root),
        preflight_only=args.preflight_only,
        allow_home_root=args.allow_home_root,
        install_home_skills=install_home_skills,
        qmd_command=args.qmd_command,
        qmd_repo_url=args.qmd_repo_url,
        qmd_mcp_url=args.qmd_mcp_url,
        brv_command=args.brv_command,
        install_scope=args.install_scope,
        allow_global_tool_install=args.allow_global_tool_install,
        gitvizz_frontend_url=args.gitvizz_frontend_url,
        gitvizz_backend_url=args.gitvizz_backend_url,
        gitvizz_repo_url=args.gitvizz_repo_url,
        gitvizz_checkout_path=args.gitvizz_checkout_path,
        gitvizz_repo_path=args.gitvizz_repo_path,
        g_kade_dependency_path=args.g_kade_dependency_path,
        gstack_dependency_path=args.gstack_dependency_path,
        memory_vault_path=args.memory_vault_path,
        memory_vault_name=args.memory_vault_name,
        memory_vault_id=args.memory_vault_id,
    )

    actions = PACKET.install_packet_workspace(
        workspace_root,
        targets,
        home_root,
        force=args.force,
        dry_run=args.dry_run,
        skip_home_skills=skip_home_skills,
        args=packet_args,
    )
    actions.extend(
        scaffold_repo_local_skills(
            workspace_root,
            gkade_runtime=gkade_runtime,
            gstack_runtime=gstack_runtime,
            force=args.force,
            dry_run=args.dry_run,
        )
    )
    actions.extend(
        scaffold_kade_overlays(
            workspace_root,
            home_root,
            layer_result_label=layer_result_label,
            gkade_runtime=gkade_runtime,
            gstack_runtime=gstack_runtime,
            install_home_profile=install_home_skills,
            force=args.force,
            dry_run=args.dry_run,
        )
    )

    verification: list[str] = []
    if not args.dry_run:
        verification.extend(verify_paths(required_paths(workspace_root)))
        if args.skip_setup:
            verification.append("setup skipped (--skip-setup)")
        else:
            setup_output, setup_code = run_helper(
                workspace_root,
                helper_kind="setup",
                allow_global_tool_install=PACKET.global_tool_install_allowed(args),
            )
            verification.extend(setup_output)
            if setup_code != 0:
                raise SystemExit("\n".join(setup_output))
            health_output, health_code = run_helper(
                workspace_root,
                helper_kind="check",
                allow_global_tool_install=PACKET.global_tool_install_allowed(args),
            )
            verification.extend(health_output)
            if health_code != 0:
                raise SystemExit("\n".join(health_output))

    lines = [
        f"Workspace root: {workspace_root}",
        f"Home root:      {home_root}",
        f"Targets:        {', '.join(targets)}",
        f"Layering:       {layer_result_label}",
        f"Repo g-kade:    {gkade_runtime.get('detected_path') or gkade_runtime['status']}",
        f"Repo gstack:    {gstack_runtime.get('detected_path') or gstack_runtime['status']}",
        f"Mode:           {'dry-run' if args.dry_run else 'write'}",
        "",
        *preflight,
        "",
        *actions,
    ]
    if verification:
        lines.extend(["", *verification])
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
