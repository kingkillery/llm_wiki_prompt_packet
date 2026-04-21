#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_TARGETS = "claude,antigravity,codex,droid,pi"
PACKET_ROOT_MARKERS = (
    Path("installers") / "install_g_kade_workspace.py",
    Path("support") / "SYSTEM_CONTRACT.md",
)
WORKSPACE_ROOT_MARKERS = (
    Path(".llm-wiki") / "config.json",
    Path("AGENTS.md"),
)


def python_command() -> list[str]:
    python = shutil.which("python")
    if python:
        return [python]
    py = shutil.which("py")
    if py:
        return [py, "-3"]
    python3 = shutil.which("python3")
    if python3:
        return [python3]
    raise SystemExit("Python is required but was not found in PATH.")


def find_root(start: Path, markers: tuple[Path, ...]) -> Path | None:
    resolved = start.expanduser().resolve()
    probe = resolved if resolved.is_dir() else resolved.parent
    for candidate in (probe, *probe.parents):
        if all((candidate / marker).exists() for marker in markers):
            return candidate
    return None


def resolve_packet_root(explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env_root = os.getenv("LLM_WIKI_PACKET_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    candidates.extend([Path(__file__).resolve(), Path.cwd()])

    seen: set[Path] = set()
    for candidate in candidates:
        root = find_root(candidate, PACKET_ROOT_MARKERS)
        if root and root not in seen:
            seen.add(root)
            return root
    return None


def resolve_workspace_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()

    for candidate in (Path.cwd(), Path(__file__).resolve()):
        root = find_root(candidate, WORKSPACE_ROOT_MARKERS)
        if root:
            return root
    return Path.cwd().resolve()


def run_command(command: list[str], *, cwd: Path | None = None) -> int:
    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False)
    return completed.returncode


def add_gitvizz_flag(command: list[str], enable_gitvizz: bool) -> None:
    if not enable_gitvizz:
        command.append("--skip-gitvizz")


def packet_script(workspace_root: Path, packet_root: Path | None, relative_path: str) -> Path:
    workspace_candidate = workspace_root / relative_path
    if workspace_candidate.exists():
        return workspace_candidate

    if packet_root is not None:
        source_relative = relative_path
        if relative_path.startswith("scripts" + os.sep):
            source_relative = os.path.join("support", relative_path)
        packet_candidate = packet_root / source_relative
        if packet_candidate.exists():
            return packet_candidate

    raise SystemExit(f"Missing required script: {workspace_candidate}")


def command_init(args: argparse.Namespace) -> int:
    packet_root = resolve_packet_root(args.packet_root)
    if packet_root is None:
        raise SystemExit(
            "Unable to locate the llm_wiki_prompt_packet checkout. "
            "Run this command from the packet repo or pass --packet-root."
        )

    installer = packet_root / "installers" / "install_g_kade_workspace.py"
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists():
        raise SystemExit(f"Project root does not exist: {project_root}")

    home_root = Path(args.home_root).expanduser()
    home_root_arg = str(home_root.resolve()) if home_root.exists() else str(home_root)

    command = python_command() + [
        str(installer),
        "--workspace",
        str(project_root),
        "--targets",
        args.targets,
        "--home-root",
        home_root_arg,
        "--install-scope",
        args.install_scope,
    ]
    if args.skip_home_skills:
        command.append("--skip-home-skills")
    else:
        command.append("--install-home-skills")
    if args.allow_global_tool_install:
        command.append("--allow-global-tool-install")
    if args.enable_gitvizz:
        command.append("--enable-gitvizz")
    if args.skip_setup:
        command.append("--skip-setup")
    if args.preflight_only:
        command.append("--preflight-only")
    if args.force:
        command.append("--force")
    return run_command(command)


def command_runtime_helper(args: argparse.Namespace, helper_kind: str) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    runtime_script = packet_script(workspace_root, None, os.path.join("scripts", "llm_wiki_memory_runtime.py"))
    command = python_command() + [str(runtime_script), helper_kind]
    add_gitvizz_flag(command, args.enable_gitvizz)
    if args.allow_global_tool_install:
        command.append("--allow-global-tool-install")
    return run_command(command, cwd=workspace_root)


def command_setup(args: argparse.Namespace) -> int:
    return command_runtime_helper(args, "setup")


def command_check(args: argparse.Namespace) -> int:
    return command_runtime_helper(args, "check")


def command_pokemon_benchmark(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    packet_root = resolve_packet_root(args.packet_root)
    adapter = packet_script(workspace_root, packet_root, os.path.join("scripts", "pokemon_benchmark_adapter.py"))
    mode = args.mode_flag or args.mode or "framework"
    if args.mode_flag and args.mode and args.mode_flag != args.mode:
        raise SystemExit("Conflicting Pokemon benchmark modes supplied. Use either the positional mode or --mode.")
    command = python_command() + [
        str(adapter),
        mode,
        "--gym-repo",
        args.gym_repo,
        "--env-dir",
        args.env_dir,
        "--task-json",
        args.task_json,
        "--seed",
        str(args.seed),
    ]
    if args.output_root:
        command.extend(["--output-root", args.output_root])
    if args.keep_session:
        command.append("--keep-session")
    if mode == "framework":
        command.extend(["--agent", args.agent, "--timeout-sec", str(args.timeout_sec)])
    return run_command(command, cwd=workspace_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-wiki-packet",
        description="Packet-owned CLI surface for project init, runtime helpers, and Pokemon benchmark runs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Activate a target project with the llm_wiki_prompt_packet harness surfaces.",
    )
    init_parser.add_argument("--project-root", required=True, help="Target repo root to activate.")
    init_parser.add_argument("--packet-root", help="Optional llm_wiki_prompt_packet checkout path.")
    init_parser.add_argument("--targets", default=DEFAULT_TARGETS, help="Comma-separated target surfaces.")
    init_parser.add_argument("--home-root", default=str(Path.home()), help="Home root used for home skill installs.")
    init_parser.add_argument(
        "--install-scope",
        choices=("local", "global"),
        default="local",
        help="Managed tool install scope.",
    )
    init_parser.add_argument("--skip-home-skills", action="store_true", help="Skip home skill installs.")
    init_parser.add_argument(
        "--allow-global-tool-install",
        action="store_true",
        help="Allow setup helpers to fall back to global installs when needed.",
    )
    init_parser.add_argument("--enable-gitvizz", action="store_true", help="Do not skip GitVizz during setup/check.")
    init_parser.add_argument("--skip-setup", action="store_true", help="Install files but skip setup/check.")
    init_parser.add_argument("--preflight-only", action="store_true", help="Print the installer preflight and stop.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite packet-managed files.")
    init_parser.set_defaults(func=command_init)

    for helper_name, helper_func in (("setup", command_setup), ("check", command_check)):
        helper_parser = subparsers.add_parser(helper_name, help=f"Run the workspace {helper_name} helper.")
        helper_parser.add_argument("--workspace-root", help="Workspace root. Defaults to the current repo.")
        helper_parser.add_argument(
            "--allow-global-tool-install",
            action="store_true",
            help="Allow runtime helpers to fall back to global installs when needed.",
        )
        helper_parser.add_argument(
            "--enable-gitvizz",
            action="store_true",
            help="Do not skip GitVizz during the helper run.",
        )
        helper_parser.set_defaults(func=helper_func)

    benchmark_parser = subparsers.add_parser(
        "pokemon-benchmark",
        help="Run the packet-owned Pokemon benchmark surface from an activated workspace.",
    )
    benchmark_parser.add_argument("mode", nargs="?", choices=("smoke", "framework"))
    benchmark_parser.add_argument(
        "--mode",
        dest="mode_flag",
        choices=("smoke", "framework"),
        help="Benchmark run mode. Accepts the same values as the positional mode argument.",
    )
    benchmark_parser.add_argument("--workspace-root", help="Activated workspace root. Defaults to the current repo.")
    benchmark_parser.add_argument("--packet-root", help="Optional packet checkout path for source-repo fallback.")
    benchmark_parser.add_argument("--agent", choices=("claude", "codex", "droid", "pi"), default="codex")
    benchmark_parser.add_argument(
        "--gym-repo",
        default=r"C:\dev\Desktop-Benchmarks\Gym-Anything\gym-anything",
        help="Gym-Anything checkout path.",
    )
    benchmark_parser.add_argument(
        "--env-dir",
        default=r"C:\dev\Desktop-Benchmarks\Gym-Anything\gym-anything\benchmarks\cua_world\environments\pokemon_agent_env",
        help="Pokemon environment directory.",
    )
    benchmark_parser.add_argument(
        "--task-json",
        default=r"C:\dev\Desktop-Benchmarks\Gym-Anything\gym-anything\benchmarks\cua_world\environments\pokemon_agent_env\tasks\start_server_capture_state\task.json",
        help="Pokemon task contract JSON path.",
    )
    benchmark_parser.add_argument("--output-root", default="", help="Optional run artifact directory root.")
    benchmark_parser.add_argument("--seed", type=int, default=42, help="Deterministic benchmark seed.")
    benchmark_parser.add_argument("--timeout-sec", type=int, default=1800, help="Framework mode timeout.")
    benchmark_parser.add_argument("--keep-session", action="store_true", help="Keep the Gym session alive after the run.")
    benchmark_parser.set_defaults(func=command_pokemon_benchmark)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return main_from_args(args)


def main_from_args(args: argparse.Namespace) -> int:
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
