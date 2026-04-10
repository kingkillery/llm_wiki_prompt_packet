#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_INSTALLER_PATH = Path(__file__).resolve().parent / "install_obsidian_agent_memory.py"

SKILL_LAYOUTS = (".agents", ".codex", ".claude")
RICH_MARKERS = {"bin", "browse", "qa", "review", "kade"}
RICH_SIBLING_HINTS = {"debug", "debugging", "deploy", "deployment", "design", "dogfood", "dx", "investigate", "ship", "workflows"}


def load_packet_installer():
    spec = importlib.util.spec_from_file_location("install_obsidian_agent_memory", PACKET_INSTALLER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PACKET = load_packet_installer()


@dataclass
class UpstreamSkill:
    name: str
    root: Path
    skill_md: Path
    markers: list[str]
    summary: str


def env_flag(name: str) -> bool:
    value = os.getenv(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


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


def ordered_candidate_entries(workspace_root: Path, home_root: Path) -> list[tuple[str, Path]]:
    ordered = [
        ("g-kade", home_root / ".codex" / "skills" / "g-kade"),
        ("g-kade", home_root / ".claude" / "skills" / "g-kade"),
        ("g-kade", home_root / ".agents" / "skills" / "g-kade"),
        ("gstack", home_root / ".codex" / "skills" / "gstack"),
        ("gstack", home_root / ".claude" / "skills" / "gstack"),
        ("gstack", home_root / ".agents" / "skills" / "gstack"),
        ("g-kade", workspace_root / ".codex" / "skills" / "g-kade"),
        ("g-kade", workspace_root / ".claude" / "skills" / "g-kade"),
        ("g-kade", workspace_root / ".agents" / "skills" / "g-kade"),
        ("gstack", workspace_root / ".codex" / "skills" / "gstack"),
        ("gstack", workspace_root / ".claude" / "skills" / "gstack"),
        ("gstack", workspace_root / ".agents" / "skills" / "gstack"),
    ]
    seen: set[str] = set()
    result: list[tuple[str, Path]] = []
    for name, candidate in ordered:
        key = f"{name}:{str(candidate.expanduser()).lower()}"
        if key in seen:
            continue
        seen.add(key)
        expanded = candidate.expanduser()
        result.append((name, expanded))
    return result


def skill_markers(candidate: Path, wrapper_root: Path) -> list[str]:
    if not candidate.exists() or not candidate.is_dir():
        return []
    if not (candidate / "SKILL.md").exists():
        return []

    markers: list[str] = []
    child_dirs = sorted(path.name for path in candidate.iterdir() if path.is_dir())
    child_files = sorted(path.name for path in candidate.iterdir() if path.is_file())
    source_files = {
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

    extra_files = sorted(path for path in candidate_files if path not in source_files)
    if len(extra_files) >= 3:
        markers.append("extra-files")

    extra_markdown = [name for name in child_files if name.endswith(".md") and name != "SKILL.md"]
    if extra_markdown:
        markers.append("companion-docs")

    return markers


def read_skill_summary(skill_md: Path) -> str:
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


def detect_richer_upstreams(workspace_root: Path, home_root: Path) -> tuple[UpstreamSkill | None, UpstreamSkill | None]:
    found: dict[str, UpstreamSkill | None] = {"g-kade": None, "gstack": None}
    for name, candidate in ordered_candidate_entries(workspace_root, home_root):
        if found[name] is not None:
            continue
        wrapper_root = PACKET.HOME_SKILLS_ROOT / name
        markers = skill_markers(candidate, wrapper_root)
        if not markers:
            continue
        found[name] = UpstreamSkill(
            name=name,
            root=candidate.resolve(),
            skill_md=(candidate / "SKILL.md").resolve(),
            markers=markers,
            summary=read_skill_summary(candidate / "SKILL.md"),
        )
        if found["g-kade"] is not None and found["gstack"] is not None:
            break
    return found["g-kade"], found["gstack"]


def layering_result(gkade: UpstreamSkill | None, gstack: UpstreamSkill | None) -> str:
    if gkade and gstack:
        return "both richer external installs"
    if gkade:
        return "richer external g-kade"
    if gstack:
        return "richer external gstack"
    return "packet wrapper only"


def repo_skill_text(name: str, workspace_root: Path, upstream: UpstreamSkill | None) -> str:
    if name == "g-kade":
        description = "Repo-local KADE bridge layered on top of the llm-wiki-memory packet."
        workflow_lines = [
            "- treat this repo root as the workspace root",
            "- prefer packet helpers for search, memory, and MCP wiring",
            "- use `kade/AGENTS.md` and `kade/KADE.md` as the project overlay",
            "- if richer upstream guidance is listed below, read it before routing work",
        ]
        install_notes = [
            "## Fastest Successful Install",
            "",
            "- run `python installers/install_g_kade_workspace.py --workspace <repo-root>` from the packet checkout when available",
            "- if using the hosted installer fallback, set `LLM_WIKI_INSTALL_MODE=g-kade` before invoking `install.sh` or `install.ps1`",
            "- let setup and health run with GitVizz skipped until a real GitVizz repo path is configured",
            "",
            "## Roadblocks And Corrections",
            "",
            "- packet file copy alone is not enough; this workspace also needs repo-local skill surfaces, KADE overlays, setup, and health verification",
            "- home skill installs are optional overlays, not proof the repo is bootstrapped",
            "- thin wrappers do not count as richer upstream runtimes",
            "",
            "## Wish I Knew Before Install",
            "",
            "- `xyz`: the repo root is the real workspace target",
            "- `xyz`: `/g-kade install` must keep going after packet file install",
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

    upstream_lines = [
        f"- path: `{upstream.root}`",
        f"- skill: `{upstream.skill_md}`",
        f"- markers: `{', '.join(upstream.markers)}`",
        f"- summary: `{upstream.summary}`",
    ] if upstream else ["- none detected; use the packet wrapper behavior"]

    workflow_block = "\n".join(workflow_lines)
    upstream_block = "\n".join(upstream_lines)

    return (
        f"---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"---\n\n"
        f"# {name}\n\n"
        f"This is the repo-local `{name}` surface for the packet-backed workspace rooted at `{workspace_root}`.\n\n"
        f"## Upstream Guidance\n\n"
        f"{upstream_block}\n\n"
        f"## Local Routing\n\n"
        f"{workflow_block}\n\n"
        f"Do not treat global skill installs as sufficient for this repo. Use the packet root files, `.llm-wiki/config.json`, and the repo-local `kade/` overlay as the first-class workspace contract.\n"
        + ("\n" + "\n".join(install_notes) + "\n" if install_notes else "")
    )


def scaffold_repo_local_skills(
    workspace_root: Path,
    *,
    gkade_upstream: UpstreamSkill | None,
    gstack_upstream: UpstreamSkill | None,
    force: bool,
    dry_run: bool,
) -> list[str]:
    actions: list[str] = []
    for layout in SKILL_LAYOUTS:
        skill_root = workspace_root / layout / "skills"
        actions.extend(
            [
                PACKET.write_text(
                    skill_root / "g-kade" / "SKILL.md",
                    repo_skill_text("g-kade", workspace_root, gkade_upstream),
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
                    repo_skill_text("gstack", workspace_root, gstack_upstream),
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


def kade_agents_text(workspace_root: Path, gkade: UpstreamSkill | None, gstack: UpstreamSkill | None) -> str:
    upstream_lines = []
    if gkade:
        upstream_lines.append(f"- richer external `g-kade`: `{gkade.skill_md}`")
    if gstack:
        upstream_lines.append(f"- richer external `gstack`: `{gstack.skill_md}`")
    if not upstream_lines:
        upstream_lines.append("- no richer external `g-kade` or `gstack` install detected")

    upstream_block = "\n".join(upstream_lines)
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
        "- do not overwrite root packet files with KADE-specific content\n\n"
        "Detected upstream guidance:\n\n"
        f"{upstream_block}\n\n"
        f"Workspace root: `{workspace_root}`\n"
    )


def kade_md_text(workspace_root: Path, layer_result: str, gkade: UpstreamSkill | None, gstack: UpstreamSkill | None) -> str:
    upstream_lines = []
    if gkade:
        upstream_lines.append(f"- `g-kade`: `{gkade.skill_md}`")
    if gstack:
        upstream_lines.append(f"- `gstack`: `{gstack.skill_md}`")
    if not upstream_lines:
        upstream_lines.append("- packet wrapper only")

    upstream_block = "\n".join(upstream_lines)
    return (
        "# KADE.md\n\n"
        "## Workspace\n\n"
        f"- root: `{workspace_root}`\n"
        f"- layering result: `{layer_result}`\n\n"
        "## Upstream Guidance\n\n"
        f"{upstream_block}\n\n"
        "## Handoff Log\n\n"
    )


def human_md_text() -> str:
    return (
        "# HUMAN.md\n\n"
        "This is the global KADE human profile.\n\n"
        "- preferred style: concise, checkpoint-driven, direct\n"
        "- expectation: keep one next action visible\n"
        "- note: replace this starter with real user-specific guidance\n"
    )


def scaffold_kade_overlays(
    workspace_root: Path,
    home_root: Path,
    *,
    layer_result_label: str,
    gkade_upstream: UpstreamSkill | None,
    gstack_upstream: UpstreamSkill | None,
    install_home_profile: bool,
    force: bool,
    dry_run: bool,
) -> list[str]:
    actions = [
        PACKET.write_text(
            workspace_root / "kade" / "AGENTS.md",
            kade_agents_text(workspace_root, gkade_upstream, gstack_upstream),
            force=force,
            dry_run=dry_run,
        ),
        PACKET.write_text(
            workspace_root / "kade" / "KADE.md",
            kade_md_text(workspace_root, layer_result_label, gkade_upstream, gstack_upstream),
            force=force,
            dry_run=dry_run,
        ),
    ]

    if install_home_profile:
        human_md = home_root / ".kade" / "HUMAN.md"
        actions.append(
            PACKET.write_text(
                human_md,
                human_md_text(),
                force=False,
                dry_run=dry_run,
            )
        )
    return actions


def required_paths(workspace_root: Path) -> list[Path]:
    return [
        workspace_root / "AGENTS.md",
        workspace_root / "CLAUDE.md",
        workspace_root / "LLM_WIKI_MEMORY.md",
        workspace_root / ".llm-wiki" / "config.json",
        workspace_root / "scripts" / "setup_llm_wiki_memory.ps1",
        workspace_root / "scripts" / "setup_llm_wiki_memory.sh",
        workspace_root / ".agents" / "skills" / "g-kade" / "SKILL.md",
        workspace_root / ".agents" / "skills" / "gstack" / "SKILL.md",
        workspace_root / ".codex" / "skills" / "g-kade" / "SKILL.md",
        workspace_root / ".codex" / "skills" / "gstack" / "SKILL.md",
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
    install_home_skills = PACKET.resolve_home_skill_install(args)
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

    gkade_upstream, gstack_upstream = detect_richer_upstreams(workspace_root, home_root)
    layer_result_label = layering_result(gkade_upstream, gstack_upstream)

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
        allow_global_tool_install=args.allow_global_tool_install,
        gitvizz_frontend_url=args.gitvizz_frontend_url,
        gitvizz_backend_url=args.gitvizz_backend_url,
        gitvizz_repo_path=args.gitvizz_repo_path,
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
            gkade_upstream=gkade_upstream,
            gstack_upstream=gstack_upstream,
            force=args.force,
            dry_run=args.dry_run,
        )
    )
    actions.extend(
        scaffold_kade_overlays(
            workspace_root,
            home_root,
            layer_result_label=layer_result_label,
            gkade_upstream=gkade_upstream,
            gstack_upstream=gstack_upstream,
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
        f"Richer g-kade:  {gkade_upstream.skill_md if gkade_upstream else 'none'}",
        f"Richer gstack:  {gstack_upstream.skill_md if gstack_upstream else 'none'}",
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
