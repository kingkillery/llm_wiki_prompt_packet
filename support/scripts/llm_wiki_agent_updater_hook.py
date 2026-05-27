#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_EVENTS = {"SessionStart", "UserPromptSubmit", "Stop", "SessionEnd", "SubagentStop", "TaskCompleted"}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def truthy(value: str | None, *, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_stdin": raw}
    return parsed if isinstance(parsed, dict) else {"stdin": parsed}


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def launch_worker(workspace: Path, agent: str, event_file: Path) -> dict[str, Any]:
    worker = workspace / "scripts" / "llm_wiki_agent_updater.py"
    if not worker.exists():
        worker = SCRIPT_DIR / "llm_wiki_agent_updater.py"
    if not worker.exists():
        return {"launched": False, "reason": "missing-worker"}

    log_dir = workspace / ".llm-wiki" / "state" / "agent-updater"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout = (log_dir / "worker.out.log").open("a", encoding="utf-8")
    stderr = (log_dir / "worker.err.log").open("a", encoding="utf-8")
    command = [sys.executable, str(worker), "--workspace", str(workspace), "--agent", agent, "--event-file", str(event_file)]
    env = dict(os.environ)
    env["LLM_WIKI_UPDATER_HOOK_ACTIVE"] = "1"

    kwargs: dict[str, Any] = {
        "cwd": str(workspace),
        "stdin": subprocess.DEVNULL,
        "stdout": stdout,
        "stderr": stderr,
        "env": env,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    else:
        kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen(command, **kwargs)
    except OSError as exc:
        stdout.close()
        stderr.close()
        return {"launched": False, "reason": str(exc)}
    stdout.close()
    stderr.close()
    return {"launched": True, "pid": process.pid}


def main() -> int:
    parser = argparse.ArgumentParser(description="Lifecycle hook that enforces the llm-wiki updater worker.")
    parser.add_argument("--workspace", default=os.getenv("CLAUDE_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--agent", choices=("claude", "codex"), required=True)
    parser.add_argument("--event", default="")
    parser.add_argument("--inline", action="store_true", help="Run the worker inline for tests/debugging.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve(strict=False)
    payload = load_stdin_json()
    event = args.event or str(
        payload.get("hook_event_name")
        or payload.get("hook_event")
        or payload.get("event_name")
        or payload.get("event")
        or "unknown"
    )
    payload.setdefault("hook_event_name", event)
    payload["llm_wiki_agent"] = args.agent
    payload["llm_wiki_workspace"] = str(workspace)
    payload["llm_wiki_hook_received_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    state_dir = workspace / ".llm-wiki" / "state" / "agent-updater"
    event_dir = state_dir / "events"
    event_dir.mkdir(parents=True, exist_ok=True)
    event_file = event_dir / f"{utc_stamp()}-{args.agent}-{event}-{uuid.uuid4().hex[:8]}.json"
    event_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    launch: dict[str, Any]
    if not truthy(os.getenv("LLM_WIKI_UPDATER_ENABLED"), default=True):
        launch = {"launched": False, "reason": "disabled"}
    elif os.getenv("LLM_WIKI_UPDATER_HOOK_ACTIVE") == "1":
        launch = {"launched": False, "reason": "recursive-hook"}
    elif event not in HOOK_EVENTS:
        launch = {"launched": False, "reason": "ignored-event"}
    elif args.inline:
        worker = workspace / "scripts" / "llm_wiki_agent_updater.py"
        if not worker.exists():
            worker = SCRIPT_DIR / "llm_wiki_agent_updater.py"
        completed = subprocess.run(
            [sys.executable, str(worker), "--workspace", str(workspace), "--agent", args.agent, "--event-file", str(event_file)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        launch = {"launched": True, "inline": True, "returncode": completed.returncode}
    else:
        launch = launch_worker(workspace, args.agent, event_file)

    audit = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "agent": args.agent,
        "event": event,
        "event_file": str(event_file),
        **launch,
    }
    append_jsonl(state_dir / "hook-events.jsonl", audit)

    additional_context = (
        f"llm-wiki updater hook recorded {event} and "
        f"{'launched updater worker' if launch.get('launched') else 'did not launch updater worker: ' + str(launch.get('reason'))}."
    )
    print(
        json.dumps(
            {
                "continue": True,
                "hookSpecificOutput": {"additionalContext": additional_context},
                "additionalContext": additional_context,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
