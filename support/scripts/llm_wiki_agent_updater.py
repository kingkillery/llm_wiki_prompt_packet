#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SILICONFLOW_ENDPOINT = "https://api.siliconflow.com/v1/chat/completions"
DEFAULT_SILICONFLOW_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
DEFAULT_PROVIDER_ORDER = "siliconflow,openrouter"
DEFAULT_CONTEXT_TIMEOUT_SEC = 8.0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def event_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("prompt", "user_prompt", "userPrompt", "input", "message", "transcript", "stop_reason", "stopReason"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key}: {value.strip()}")
    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in messages[-3:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role", "message")
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                parts.append(f"{role}: {content.strip()}")
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("command", "description", "prompt"):
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(f"tool_input.{key}: {value.strip()}")
    return "\n".join(parts).strip()


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def claims_from_response(raw: str) -> list[str]:
    parsed = json.loads(raw)
    content = parsed["choices"][0]["message"].get("content") or parsed["choices"][0]["message"].get("reasoning") or ""
    claims_payload = extract_json_object(str(content))
    claims = claims_payload.get("claims", [])
    return [str(claim).strip() for claim in claims if str(claim).strip()]


def provider_claims(provider: str, text: str) -> tuple[list[str], str]:
    if provider == "siliconflow":
        api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("LLM_WIKI_SILICONFLOW_API_KEY")
        endpoint = os.getenv("LLM_WIKI_SILICONFLOW_ENDPOINT", DEFAULT_SILICONFLOW_ENDPOINT)
        model = os.getenv("LLM_WIKI_SILICONFLOW_MODEL", DEFAULT_SILICONFLOW_MODEL)
        headers = {"content-type": "application/json", "authorization": f"Bearer {api_key}"}
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_WIKI_OPENROUTER_API_KEY")
        endpoint = os.getenv("LLM_WIKI_OPENROUTER_ENDPOINT", DEFAULT_OPENROUTER_ENDPOINT)
        model = os.getenv("LLM_WIKI_OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("LLM_WIKI_OPENROUTER_REFERER", "https://github.com/kingkillery/llm_wiki_prompt_packet"),
            "X-Title": os.getenv("LLM_WIKI_OPENROUTER_TITLE", "llm-wiki-context-agent"),
        }
    else:
        return [], f"unsupported-provider:{provider}"

    if not api_key:
        return [], f"{provider}:missing-api-key"

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
        headers=headers,
        method="POST",
    )
    timeout = float(os.getenv("LLM_WIKI_CONTEXT_TIMEOUT_SEC", str(DEFAULT_CONTEXT_TIMEOUT_SEC)))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError) as exc:
        return [], f"{provider}:error:{exc}"
    try:
        claims = claims_from_response(raw)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return [], f"{provider}:parse-error:{exc}"
    return claims, provider


def configured_provider_order() -> list[str]:
    raw = os.getenv("LLM_WIKI_CONTEXT_PROVIDERS", DEFAULT_PROVIDER_ORDER)
    providers = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return providers or ["local"]


def context_claims(text: str) -> tuple[list[str], str, list[str]]:
    statuses: list[str] = []
    for provider in configured_provider_order():
        if provider == "local":
            return [], "local-rule-based", statuses
        claims, status = provider_claims(provider, text)
        statuses.append(status)
        if claims:
            return claims, provider, statuses
    return [], "local-rule-based", statuses


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
        claims, provider, provider_statuses = context_claims(text)
        if claims:
            result["provider"] = provider
            result["provider_statuses"] = provider_statuses
            extract_text = "\n".join(f"Durable fact: {claim}" for claim in claims)
        else:
            result["provider_statuses"] = provider_statuses
            extract_text = text
        result["memory_extract"] = run_memory_extract(workspace, extract_text, task)

    append_jsonl(log_path, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
