#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_EVENTS = {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "SessionEnd", "SubagentStop", "TaskCompleted"}
WORKER_LAUNCH_EVENTS = {"SessionStart", "UserPromptSubmit", "Stop", "SessionEnd", "SubagentStop", "TaskCompleted"}
CONTEXT_LAYER_EVENTS = HOOK_EVENTS
CONTEXT_TRIGGER_EVENTS = {"UserPromptSubmit", "PostToolUse"}
CONTEXT_OBSERVER_TOOLS = {"Bash", "Glob", "Grep", "LS", "Read"}
LONG_CONTEXT_CHARS = 32000
MAX_POST_TOOL_FIELD_CHARS = 4000
MAX_POST_TOOL_SEQUENCE_ITEMS = 20
PATH_PATTERN = re.compile(r"(?:(?:\.{1,2}[\\/]|~[\\/]|[A-Za-z]:[\\/]|/)[^\s\"'<>|`]+)")
URL_PATTERN = re.compile(r"https?://[^\s\"'<>|`]+")
MEDIA_PATTERN = re.compile(r"\.(?:png|jpe?g|gif|webp|mp4|mov|avi|mkv|mp3|wav|m4a|flac)(?:$|[?#])", re.IGNORECASE)
SENSITIVE_KEY_PATTERN = re.compile(r"(?:api[_-]?key|authorization|cookie|password|secret|token)", re.IGNORECASE)


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


def read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def compact_string(value: str, *, limit: int = 4000) -> str:
    stripped = value.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[:limit] + "\n...[truncated]"


def compact_value(value: Any, *, limit: int = 4000) -> str:
    if isinstance(value, str):
        return compact_string(value, limit=limit)
    try:
        return compact_string(json.dumps(value, sort_keys=True), limit=limit)
    except (TypeError, ValueError):
        return compact_string(str(value), limit=limit)


def sanitize_post_tool_value(value: Any, *, key: str = "", depth: int = 0) -> Any:
    if SENSITIVE_KEY_PATTERN.search(key):
        return "[redacted]"
    if isinstance(value, str):
        return compact_string(value, limit=MAX_POST_TOOL_FIELD_CHARS)
    if depth >= 4:
        return compact_value(value, limit=MAX_POST_TOOL_FIELD_CHARS)
    if isinstance(value, dict):
        return {str(item_key): sanitize_post_tool_value(item_value, key=str(item_key), depth=depth + 1) for item_key, item_value in value.items()}
    if isinstance(value, list):
        items = [sanitize_post_tool_value(item, depth=depth + 1) for item in value[:MAX_POST_TOOL_SEQUENCE_ITEMS]]
        if len(value) > MAX_POST_TOOL_SEQUENCE_ITEMS:
            items.append({"truncated_items": len(value) - MAX_POST_TOOL_SEQUENCE_ITEMS})
        return items
    return value


def sanitize_event_payload(payload: dict[str, Any], event: str) -> dict[str, Any]:
    if event != "PostToolUse":
        return payload
    sanitized = {str(key): sanitize_post_tool_value(value, key=str(key)) for key, value in payload.items()}
    sanitized["llm_wiki_payload_sanitized"] = True
    sanitized["llm_wiki_payload_sanitized_reason"] = "PostToolUse payload is capped/redacted before persistence."
    return sanitized


def unique_sorted(values: list[str]) -> list[str]:
    return sorted({value.strip().rstrip(".,);]") for value in values if value.strip()})


def payload_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("prompt", "user_prompt", "userPrompt", "input", "message", "transcript", "tool_output", "tool_response", "output", "result"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
        elif isinstance(value, (dict, list)):
            text = compact_value(value, limit=MAX_POST_TOOL_FIELD_CHARS)
            if text:
                parts.append(text)
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for value in tool_input.values():
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    return "\n".join(parts).strip()


def context_layer_manifest(workspace: Path) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "version": 1,
        "workspace": str(workspace),
        "created_at": now,
        "updated_at": now,
        "counters": {
            "events_recorded": 0,
            "jobs_enqueued": 0,
            "queue_depth": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "workers_spawned": 0,
            "tokens_saved": 0,
            "files_summarized": 0,
        },
        "agents": {},
        "files_summarized": [],
        "recent_jobs": [],
        "last_event": None,
    }


def context_layer_job(
    workspace: Path,
    agent: str,
    event: str,
    payload: dict[str, Any],
    event_file: Path,
) -> dict[str, Any] | None:
    if event not in CONTEXT_TRIGGER_EVENTS:
        return None

    text = payload_text(payload)
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")
    explicit_paths: list[str] = []
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "paths", "directory", "cwd"):
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                explicit_paths.append(value.strip())
            elif isinstance(value, list):
                explicit_paths.extend(item.strip() for item in value if isinstance(item, str) and item.strip())
    urls = unique_sorted(URL_PATTERN.findall(text))
    text_without_urls = URL_PATTERN.sub(" ", text)
    paths = unique_sorted([*PATH_PATTERN.findall(text_without_urls), *explicit_paths])
    media_refs = [item for item in [*paths, *urls] if MEDIA_PATTERN.search(item)]
    triggers: list[str] = []

    if paths:
        triggers.append("path-reference")
    if urls:
        triggers.append("url-reference")
    if media_refs:
        triggers.append("media-reference")
    if len(text) >= LONG_CONTEXT_CHARS:
        triggers.append("long-context")
    if event == "PostToolUse" and tool_name in CONTEXT_OBSERVER_TOOLS:
        triggers.append(f"tool-observation:{tool_name}")

    if not triggers:
        return None

    job_id = f"{utc_stamp()}-{agent}-{event}-{uuid.uuid4().hex[:8]}"
    return {
        "version": 1,
        "id": job_id,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "agent-hook",
        "agent": agent,
        "event": event,
        "tool_name": tool_name or None,
        "workspace": str(workspace),
        "event_file": str(event_file.resolve(strict=False)),
        "triggers": unique_sorted(triggers),
        "references": {
            "paths": paths,
            "urls": urls,
            "media": unique_sorted(media_refs),
            "long_context": len(text) >= LONG_CONTEXT_CHARS,
        },
        "content_preview": compact_string(text),
        "payload_keys": sorted(payload.keys()),
    }


def record_context_layer(workspace: Path, agent: str, event: str, payload: dict[str, Any], event_file: Path) -> dict[str, Any]:
    if event not in CONTEXT_LAYER_EVENTS:
        return {"recorded": False, "jobs_enqueued": 0, "reason": "ignored-event"}

    state_dir = workspace / ".llm-wiki" / "state" / "context-layer"
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    context_event = {
        "ts": now,
        "agent": agent,
        "event": event,
        "event_file": str(event_file.resolve(strict=False)),
        "payload_keys": sorted(payload.keys()),
    }
    append_jsonl(state_dir / "events.jsonl", context_event)

    job_paths: list[str] = []
    job = context_layer_job(workspace, agent, event, payload, event_file)
    if job is not None:
        job_path = state_dir / "queue" / f"{job['id']}.json"
        write_json(job_path, job)
        job_paths.append(str(job_path.relative_to(state_dir)))

    manifest_path = state_dir / "manifest.json"
    manifest = read_json(manifest_path) or context_layer_manifest(workspace)
    counters = manifest.setdefault("counters", {})
    counters["events_recorded"] = int(counters.get("events_recorded", 0)) + 1
    counters["jobs_enqueued"] = int(counters.get("jobs_enqueued", 0)) + len(job_paths)
    counters.setdefault("cache_hits", 0)
    counters.setdefault("cache_misses", 0)
    counters.setdefault("workers_spawned", 0)
    counters.setdefault("tokens_saved", 0)
    counters.setdefault("files_summarized", 0)
    counters["queue_depth"] = len(list((state_dir / "queue").glob("*.json"))) if (state_dir / "queue").exists() else 0

    agents = manifest.setdefault("agents", {})
    agent_stats = agents.setdefault(agent, {"events_recorded": 0, "jobs_enqueued": 0})
    agent_stats["events_recorded"] = int(agent_stats.get("events_recorded", 0)) + 1
    agent_stats["jobs_enqueued"] = int(agent_stats.get("jobs_enqueued", 0)) + len(job_paths)

    recent_jobs = [*manifest.get("recent_jobs", []), *job_paths]
    manifest["recent_jobs"] = recent_jobs[-20:]
    manifest["updated_at"] = now
    manifest["last_event"] = context_event
    manifest.setdefault("files_summarized", [])
    write_json(manifest_path, manifest)
    return {"recorded": True, "jobs_enqueued": len(job_paths), "manifest": str(manifest_path)}


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
    persisted_payload = sanitize_event_payload(payload, event)
    event_file.write_text(json.dumps(persisted_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    launch: dict[str, Any]
    if not truthy(os.getenv("LLM_WIKI_UPDATER_ENABLED"), default=True):
        launch = {"launched": False, "reason": "disabled"}
    elif os.getenv("LLM_WIKI_UPDATER_HOOK_ACTIVE") == "1":
        launch = {"launched": False, "reason": "recursive-hook"}
    elif event not in HOOK_EVENTS:
        launch = {"launched": False, "reason": "ignored-event"}
    elif event not in WORKER_LAUNCH_EVENTS:
        launch = {"launched": False, "reason": "context-layer-only-event"}
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
    try:
        context_layer = record_context_layer(workspace, args.agent, event, persisted_payload, event_file)
    except Exception as exc:
        context_layer = {"recorded": False, "jobs_enqueued": 0, "reason": str(exc)}

    additional_context = (
        f"llm-wiki updater hook recorded {event} and "
        f"{'launched updater worker' if launch.get('launched') else 'did not launch updater worker: ' + str(launch.get('reason'))}."
    )
    if context_layer.get("recorded"):
        additional_context += f" Context layer queued {context_layer.get('jobs_enqueued', 0)} job(s)."
    elif context_layer.get("reason"):
        additional_context += f" Context layer did not record the event: {context_layer.get('reason')}."
    # Claude Code requires `hookEventName` inside `hookSpecificOutput` whenever
    # it is present, and only UserPromptSubmit / SessionStart / PostToolUse
    # support injecting `additionalContext`. For other events (Stop, SessionEnd,
    # SubagentStop, ...) emit a bare `continue` so output validation passes.
    context_events = {"UserPromptSubmit", "SessionStart", "PostToolUse"}
    output: dict[str, Any] = {"continue": True}
    if event in context_events:
        output["hookSpecificOutput"] = {
            "hookEventName": event,
            "additionalContext": additional_context,
        }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
