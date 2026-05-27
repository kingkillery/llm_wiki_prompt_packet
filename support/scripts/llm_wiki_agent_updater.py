#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SILICONFLOW_ENDPOINT = "https://api.siliconflow.cn/v1/chat/completions"
DEFAULT_SILICONFLOW_MODEL = "Qwen/Qwen2.5-7B-Instruct"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def event_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("prompt", "user_prompt", "message", "transcript", "stop_reason"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key}: {value.strip()}")
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("command", "description", "prompt"):
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(f"tool_input.{key}: {value.strip()}")
    return "\n".join(parts).strip()


def siliconflow_claims(text: str) -> tuple[list[str], str]:
    api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("LLM_WIKI_SILICONFLOW_API_KEY")
    if not api_key:
        return [], "missing-api-key"
    endpoint = os.getenv("LLM_WIKI_SILICONFLOW_ENDPOINT", DEFAULT_SILICONFLOW_ENDPOINT)
    model = os.getenv("LLM_WIKI_SILICONFLOW_MODEL", DEFAULT_SILICONFLOW_MODEL)
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract durable repo memory candidates from an agent lifecycle event. "
                    "Return only JSON: {\"claims\":[\"...\"]}. Include preferences, decisions, "
                    "implemented changes, verified facts, or follow-up obligations. Exclude secrets."
                ),
            },
            {"role": "user", "content": text[:12000]},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json", "authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError) as exc:
        return [], f"siliconflow-error:{exc}"
    try:
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        claims_payload = json.loads(content)
        claims = claims_payload.get("claims", [])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return [], f"siliconflow-parse-error:{exc}"
    return [str(claim).strip() for claim in claims if str(claim).strip()], "siliconflow"


def run_memory_extract(workspace: Path, text: str, task: str) -> dict[str, Any]:
    controller = workspace / "scripts" / "llm_wiki_memory_controller.py"
    if not controller.exists():
        controller = SCRIPT_DIR / "llm_wiki_memory_controller.py"
    if not controller.exists():
        return {"status": "skipped", "reason": "missing-memory-controller"}
    command = [
        sys.executable,
        str(controller),
        "--workspace-root",
        str(workspace),
        "--json",
        "extract",
        "--text",
        text,
        "--task",
        task,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    return {
        "status": "ok" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Background llm-wiki updater worker for agent lifecycle hooks.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--event-file", required=True)
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve(strict=False)
    payload = read_json(Path(args.event_file))
    event = str(payload.get("hook_event_name") or payload.get("event") or "unknown")
    text = event_text(payload)
    log_path = workspace / ".llm-wiki" / "state" / "agent-updater" / "runs.jsonl"
    task = f"{args.agent} {event} lifecycle updater"

    result: dict[str, Any] = {
        "ts": utc_now(),
        "agent": args.agent,
        "event": event,
        "event_file": str(Path(args.event_file).resolve(strict=False)),
        "provider": "local-rule-based",
        "memory_extract": {"status": "skipped", "reason": "no-candidate-text"},
    }

    if len(text) >= 20 and event in {"UserPromptSubmit", "Stop", "SessionEnd", "SubagentStop", "TaskCompleted"}:
        claims, provider_status = siliconflow_claims(text)
        if claims:
            result["provider"] = "siliconflow"
            extract_text = "\n".join(f"Durable fact: {claim}" for claim in claims)
        else:
            result["provider_status"] = provider_status
            extract_text = text
        result["memory_extract"] = run_memory_extract(workspace, extract_text, task)

    append_jsonl(log_path, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
