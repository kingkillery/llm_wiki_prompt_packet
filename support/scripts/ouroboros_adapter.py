#!/usr/bin/env python3
"""Optional Ouroboros compatibility adapter for dashboard session discovery.

The dashboard should not require Ouroboros as a dependency. This module borrows
the useful concept: scan known Ouroboros state roots and normalize session-like
artifacts into the dashboard provider/session model.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

PROVIDER = "Ouroboros"
SESSION_SUFFIXES = {".jsonl", ".json", ".log", ".db", ".sqlite", ".sqlite3"}


def discover_ouroboros_sessions(workspace: Path, home: Path | None = None, limit: int = 80) -> tuple[dict, list[dict]]:
    home = home or Path.home()
    roots = _candidate_roots(workspace, home)
    existing = [root for root in roots if root.exists()]
    command = _resume_command_name()

    if not existing:
        return {
            "provider": PROVIDER,
            "available": False,
            "message": "No Ouroboros state directory found",
        }, []

    files = _candidate_files(existing, limit)
    sessions = [_session_from_file(path, command) for path in files]
    sessions = [item for item in sessions if item]
    return {
        "provider": PROVIDER,
        "available": True,
        "message": f"{len(sessions)} candidate session artifacts found",
    }, sessions


def _candidate_roots(workspace: Path, home: Path) -> list[Path]:
    roots: list[Path] = []
    for name in ("OUROBOROS_HOME", "OUROBOROS_STATE_DIR"):
        value = os.environ.get(name, "").strip()
        if value:
            roots.append(Path(value).expanduser())
    roots.extend(
        [
            workspace / ".ouroboros",
            home / ".ouroboros",
            home / ".config" / "ouroboros",
            home / "AppData" / "Roaming" / "Ouroboros",
            home / "AppData" / "Local" / "Ouroboros",
        ]
    )
    return _unique_paths(roots)


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path.resolve()) if path.exists() else str(path.absolute())
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _candidate_files(roots: list[Path], limit: int) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        try:
            files.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SESSION_SUFFIXES)
        except OSError:
            continue
    return sorted(files, key=lambda path: _mtime(path), reverse=True)[:limit]


def _session_from_file(path: Path, command_name: str) -> dict:
    records = _jsonl_records(path, head=20, tail=80) if path.suffix.lower() == ".jsonl" else []
    data = _json_object(path) if path.suffix.lower() == ".json" else {}

    session_id = _first_text(data, records, ("id", "session_id", "sessionId", "run_id", "conversation_id", "uuid"))
    if not session_id:
        session_id = path.stem

    cwd = _first_text(data, records, ("cwd", "workspace", "workspace_path", "project_path", "repo_path"))
    title = _first_text(data, records, ("title", "name", "summary", "prompt", "goal", "lastPrompt", "text", "thread_name"))
    if not title:
        title = path.name

    command = f"{command_name} resume {session_id}" if command_name else ""
    if command and cwd:
        command = f'cd "{cwd}" && {command}'

    updated = _mtime(path)
    size = _size(path)
    return {
        "provider": PROVIDER,
        "id": session_id,
        "title": title[:90],
        "path": str(path),
        "cwd": cwd,
        "updated_at": updated,
        "updated_label": _short_time(updated) if updated else "unknown",
        "size": size,
        "resume_command": command,
        "status": "available" if command else "detected",
    }


def _resume_command_name() -> str:
    if shutil.which("ooo"):
        return "ooo"
    if shutil.which("ouroboros"):
        return "ouroboros"
    return ""


def _json_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _jsonl_records(path: Path, head: int = 20, tail: int = 80) -> list[dict]:
    try:
        lines: list[str] = []
        if head:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for _ in range(head):
                    line = handle.readline()
                    if not line:
                        break
                    lines.append(line.rstrip("\r\n"))
        if tail:
            with path.open("rb") as handle:
                size = handle.seek(0, os.SEEK_END)
                handle.seek(max(0, size - 262144))
                tail_text = handle.read().decode("utf-8", errors="ignore")
            lines.extend(tail_text.splitlines()[-tail:])
    except OSError:
        return []

    records: list[dict] = []
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def _first_text(data: dict, records: list[dict], keys: tuple[str, ...]) -> str:
    for source in [data, *records]:
        value = _nested_first_text(source, keys)
        if value:
            return value
    return ""


def _nested_first_text(source: Any, keys: tuple[str, ...]) -> str:
    if not isinstance(source, dict):
        return ""
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("payload", "metadata", "session", "run", "conversation"):
        value = _nested_first_text(source.get(key), keys)
        if value:
            return value
    message = source.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = [item.get("text", "").strip() for item in content if isinstance(item, dict)]
            text = " ".join(part for part in parts if part)
            if text:
                return text
    return ""


def _short_time(timestamp: float) -> str:
    age = max(0, time.time() - timestamp)
    if age < 60:
        return "just now"
    if age < 3600:
        return f"{int(age // 60)}m ago"
    if age < 86400:
        return f"{int(age // 3600)}h ago"
    return f"{int(age // 86400)}d ago"


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
