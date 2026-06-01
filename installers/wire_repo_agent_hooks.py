#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PACKET_ROOT = Path(__file__).resolve().parents[1]
HOOK_SCRIPT_NAMES = ("llm_wiki_agent_updater.py", "llm_wiki_agent_updater_hook.py")
CLAUDE_EVENTS = ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "SessionEnd")
CODEX_EVENTS = ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd")
MANAGED_START = "# llm-wiki-agent-updater:start"
MANAGED_END = "# llm-wiki-agent-updater:end"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup(path: Path, *, dry_run: bool) -> Path | None:
    if not path.exists():
        return None
    backup_path = path.with_name(f"{path.name}.bak.{timestamp()}")
    if not dry_run:
        shutil.copy2(path, backup_path)
    return backup_path


def copy_hook_scripts(workspace: Path, *, force: bool, dry_run: bool) -> list[str]:
    actions: list[str] = []
    src_root = PACKET_ROOT / "support" / "scripts"
    dst_root = workspace / "scripts"
    for name in HOOK_SCRIPT_NAMES:
        src = src_root / name
        dst = dst_root / name
        if dst.exists() and not force:
            actions.append(f"skip   {dst} (exists)")
            continue
        actions.append(f"copy   {src} -> {dst}")
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return actions


def command_for(agent: str) -> str:
    if agent == "claude":
        return 'python "$CLAUDE_PROJECT_DIR/scripts/llm_wiki_agent_updater_hook.py" --agent claude --workspace "$CLAUDE_PROJECT_DIR"'
    return 'python "scripts/llm_wiki_agent_updater_hook.py" --agent codex --workspace "."'


def command_windows_for(agent: str) -> str:
    if agent == "claude":
        return 'python "%CLAUDE_PROJECT_DIR%\\scripts\\llm_wiki_agent_updater_hook.py" --agent claude --workspace "%CLAUDE_PROJECT_DIR%"'
    return 'python "scripts\\llm_wiki_agent_updater_hook.py" --agent codex --workspace "."'


def claude_hook_block() -> dict[str, list[dict[str, object]]]:
    command = command_for("claude")
    return {
        event: [
            {
                **({"matcher": "*"} if event == "PostToolUse" else {}),
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": 5,
                    }
                ]
            }
        ]
        for event in CLAUDE_EVENTS
    }


def is_managed_claude_hook(hook: object) -> bool:
    if not isinstance(hook, dict):
        return False
    command = hook.get("command")
    return isinstance(command, str) and "llm_wiki_agent_updater_hook.py" in command and "--agent claude" in command


def remove_managed_claude_hooks(groups: object) -> list[dict[str, object]]:
    if not isinstance(groups, list):
        return []
    cleaned: list[dict[str, object]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        hooks = group.get("hooks")
        if not isinstance(hooks, list):
            cleaned.append(dict(group))
            continue
        filtered_hooks = [hook for hook in hooks if not is_managed_claude_hook(hook)]
        if not filtered_hooks:
            continue
        replacement = dict(group)
        replacement["hooks"] = filtered_hooks
        cleaned.append(replacement)
    return cleaned


def merge_claude_settings(workspace: Path, *, force: bool, dry_run: bool) -> list[str]:
    settings_path = workspace / ".claude" / "settings.json"
    existing: dict[str, object] = {}
    if settings_path.exists():
        try:
            parsed = json.loads(settings_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                existing = parsed
        except json.JSONDecodeError as exc:
            if not force:
                return [f"skip   {settings_path} (invalid JSON: {exc}; pass --force to replace)"]
    hooks = existing.get("hooks") if isinstance(existing.get("hooks"), dict) else {}
    merged_hooks = dict(hooks)
    managed = claude_hook_block()
    changed = False
    for event, desired_groups in managed.items():
        current_groups = merged_hooks.get(event)
        desired_event_groups = [*remove_managed_claude_hooks(current_groups), *desired_groups]
        if current_groups != desired_event_groups:
            merged_hooks[event] = desired_event_groups
            changed = True
    existing["hooks"] = merged_hooks
    if not changed and settings_path.exists():
        return [f"skip   {settings_path} (Claude hooks current)"]
    backup_path = backup(settings_path, dry_run=dry_run)
    if not dry_run:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    suffix = f" backup={backup_path}" if backup_path else ""
    return [f"write  {settings_path} (Claude hooks){suffix}"]


def codex_managed_block() -> str:
    lines = [
        MANAGED_START,
    ]
    command = json.dumps(command_for("codex"))
    command_windows = json.dumps(command_windows_for("codex"))
    for event in CODEX_EVENTS:
        lines.extend(
            [
                f"[[hooks.{event}]]",
                "hooks = [",
                f'  {{ type = "command", command = {command}, commandWindows = {command_windows}, timeout = 5, statusMessage = "llm-wiki updater" }}',
                "]",
                "",
            ]
        )
    lines.append(MANAGED_END)
    return "\n".join(lines).rstrip() + "\n"


def ensure_codex_hooks_feature(text: str) -> str:
    normalized = text.replace("\r\n", "\n").rstrip()
    lines = normalized.splitlines() if normalized else []
    features_start: int | None = None
    next_table = len(lines)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[features]":
            features_start = idx
            continue
        if features_start is not None and idx > features_start and stripped.startswith("[") and stripped.endswith("]"):
            next_table = idx
            break
    if features_start is None:
        if normalized:
            return normalized + "\n\n[features]\nhooks = true\n"
        return "[features]\nhooks = true\n"

    for idx in range(features_start + 1, next_table):
        stripped = lines[idx].strip()
        if stripped.startswith("hooks"):
            prefix = lines[idx][: len(lines[idx]) - len(lines[idx].lstrip())]
            lines[idx] = f"{prefix}hooks = true"
            return "\n".join(lines).rstrip() + "\n"
    lines.insert(features_start + 1, "hooks = true")
    return "\n".join(lines).rstrip() + "\n"


def strip_managed_block(text: str) -> str:
    if MANAGED_START not in text or MANAGED_END not in text:
        return text.rstrip() + ("\n" if text.strip() else "")
    before, rest = text.split(MANAGED_START, 1)
    _, after = rest.split(MANAGED_END, 1)
    return (before.rstrip() + "\n\n" + after.lstrip()).strip() + "\n"


def merge_codex_config(workspace: Path, *, dry_run: bool) -> list[str]:
    config_path = workspace / ".codex" / "config.toml"
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    desired = ensure_codex_hooks_feature(strip_managed_block(existing)).rstrip()
    if desired:
        desired += "\n\n"
    desired += codex_managed_block()
    if existing.replace("\r\n", "\n") == desired.replace("\r\n", "\n"):
        return [f"skip   {config_path} (Codex hooks current)"]
    backup_path = backup(config_path, dry_run=dry_run)
    if not dry_run:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(desired, encoding="utf-8")
    suffix = f" backup={backup_path}" if backup_path else ""
    return [f"write  {config_path} (Codex hooks){suffix}"]


def run_self_test(workspace: Path, agent: str) -> tuple[bool, str]:
    hook = workspace / "scripts" / "llm_wiki_agent_updater_hook.py"
    if not hook.exists():
        return False, f"missing hook script: {hook}"
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Remember that llm-wiki updater hooks should stay wired for Claude and Codex.",
        "source": "wire_repo_agent_hooks self-test",
    }
    env = dict(os.environ)
    env["LLM_WIKI_UPDATER_ENABLED"] = "0"
    completed = subprocess.run(
        [sys.executable, str(hook), "--workspace", str(workspace), "--agent", agent],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(workspace),
        env=env,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        return False, f"hook exited {completed.returncode}: {completed.stderr.strip()[:500]}"
    state_file = workspace / ".llm-wiki" / "state" / "agent-updater" / "hook-events.jsonl"
    if not state_file.exists():
        return False, f"hook returned success but did not write {state_file}"
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return False, f"hook stdout was not JSON: {exc}: {completed.stdout[:500]}"
    if response.get("continue") is not True:
        return False, f"hook response did not allow continuation: {completed.stdout[:500]}"
    return True, f"self-test ok ({agent}); state={state_file}"


def normalize_agents(raw: str) -> list[str]:
    agents = [item.strip().lower() for item in raw.split(",") if item.strip()]
    invalid = [item for item in agents if item not in {"claude", "codex"}]
    if invalid:
        raise SystemExit(f"Unknown hook agent(s): {', '.join(invalid)}")
    return agents


def main() -> int:
    parser = argparse.ArgumentParser(description="Install llm-wiki updater hooks into a Claude/Codex repo workspace.")
    parser.add_argument("--workspace", default=".", help="Target repo workspace root.")
    parser.add_argument("--agents", default="claude,codex", help="Comma-separated agents: claude,codex")
    parser.add_argument("--force", action="store_true", help="Overwrite existing hook scripts and invalid Claude settings.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing files.")
    parser.add_argument("--self-test", action="store_true", help="After writing, invoke the installed hook with a Codex-style payload.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise SystemExit(f"Workspace does not exist: {workspace}")

    agents = normalize_agents(args.agents)
    actions = [f"Workspace: {workspace}", f"Agents:    {', '.join(agents)}"]
    actions.extend(copy_hook_scripts(workspace, force=args.force, dry_run=args.dry_run))
    if "claude" in agents:
        actions.extend(merge_claude_settings(workspace, force=args.force, dry_run=args.dry_run))
    if "codex" in agents:
        actions.extend(merge_codex_config(workspace, dry_run=args.dry_run))
    if args.self_test and not args.dry_run:
        for agent in agents:
            ok, message = run_self_test(workspace, agent)
            actions.append(("ok     " if ok else "fail   ") + message)
            if not ok:
                print("\n".join(actions))
                return 1
    print("\n".join(actions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
