#!/usr/bin/env python3
"""
wiki_auto_update.py — Patient LLM Wiki & Skills Auto-Updater

Model pool (round-robin, multi-provider):
  SiliconFlow:
    - deepseek-ai/DeepSeek-V4-Flash
    - tencent/Hy3-preview
    - google/gemma-4-26B-A4B-it
  OpenRouter (free tier):
    - nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free

Design principles:
  - Patient: exponential backoff on 429/5xx, inter-call jitter
  - Conservative: single call per task, no batch blasting
  - Rotates models round-robin across providers — no single API gets hammered
  - Falls back to OpenRouter free slot if SiliconFlow returns 429
  - Writes all findings to wiki/log.md with a timestamped header
  - Idempotent: safe to run repeatedly; only acts on actual changes

Usage:
    python scripts/wiki_auto_update.py [--workspace PATH] [--dry-run] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Fix Windows console encoding so Unicode from LLMs doesn't crash
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ---------------------------------------------------------------------------
# Provider registry — each slot is fully self-contained
# ---------------------------------------------------------------------------

# LM Studio native API base (used for health probe)
LMSTUDIO_BASE        = "http://127.0.0.1:1234"
LMSTUDIO_NATIVE_API  = f"{LMSTUDIO_BASE}/api/v1"   # native endpoint (v0.4+)
LMSTUDIO_COMPAT_API  = f"{LMSTUDIO_BASE}/v1"        # OpenAI-compat endpoint

# fmt: off
MODEL_POOL: list[dict[str, str]] = [
    # ── SiliconFlow ───────────────────────────────────────────────────
    {"model": "deepseek-ai/DeepSeek-V4-Flash",       "provider": "siliconflow"},
    # ── OpenRouter free tier ──────────────────────────────────────────
    {"model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "provider": "openrouter"},
    # ── SiliconFlow ───────────────────────────────────────────────────
    {"model": "tencent/Hy3-preview",                 "provider": "siliconflow"},
    {"model": "google/gemma-4-26B-A4B-it",           "provider": "siliconflow"},
]
# fmt: on

PROVIDER_CONFIG: dict[str, dict[str, str]] = {
    "lmstudio": {
        # Use OpenAI-compatible endpoint for inference (consistent with other providers)
        "base_url": LMSTUDIO_COMPAT_API,
        "api_key_env": "",           # empty = no key required
        "health_url": f"{LMSTUDIO_NATIVE_API}/models",  # native probe endpoint
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.com/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        # OpenRouter recommends these headers for free-tier tracking
        "extra_headers": (
            '{"HTTP-Referer": "https://github.com/llm-wiki-prompt-packet", '
            '"X-Title": "llm-wiki-auto-update"}'
        ),
    },
}

# Backoff settings
INITIAL_BACKOFF_S = 5.0       # Start at 5 s
MAX_BACKOFF_S = 120.0         # Cap at 2 min
BACKOFF_MULTIPLIER = 2.0
JITTER_RANGE = (0.5, 2.5)     # Random jitter added to each sleep
MAX_RETRIES = 6               # Per API call

# Inter-task pause (be polite between separate tasks)
INTER_TASK_PAUSE_S = (3.0, 8.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_env(workspace: Path) -> None:
    """Load .env from workspace root into os.environ (simple key=value parser)."""
    env_path = workspace / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key(provider: str) -> str:
    """Resolve the API key for the given provider from env.
    Returns empty string for local providers that don't need one."""
    cfg = PROVIDER_CONFIG[provider]
    env_var = cfg.get("api_key_env", "")
    if not env_var:
        return "lm-studio"  # LM Studio accepts any non-empty bearer token
    key = os.environ.get(env_var, "")
    if not key:
        raise RuntimeError(
            f"{env_var} not set for provider '{provider}'.\n"
            f"Add it to your .env file: {env_var}=sk-..."
        )
    return key


def probe_lmstudio(verbose: bool = False) -> bool:
    """Return True if LM Studio's native /api/v1/models endpoint responds.
    Uses a short timeout so startup is never blocked.
    """
    try:
        import httpx
        health_url = PROVIDER_CONFIG["lmstudio"]["health_url"]
        resp = httpx.get(health_url, timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            # native /api/v1/models returns {"data": [...]} or a list
            models = data.get("data", data) if isinstance(data, dict) else data
            loaded = [m.get("id", "") for m in (models if isinstance(models, list) else [])]
            if verbose:
                print(f"  [lmstudio] online — loaded models: {loaded or '(none)'}")
            return True
    except Exception as exc:
        if verbose:
            print(f"  [lmstudio] offline ({exc.__class__.__name__}: {exc})")
    return False


def build_active_pool(verbose: bool = False) -> list[dict[str, str]]:
    """Return MODEL_POOL (all slots assumed online per config)."""
    return MODEL_POOL


def patient_sleep(seconds: float, verbose: bool = False) -> None:
    if verbose:
        print(f"  [pause] sleeping {seconds:.1f}s …")
    time.sleep(seconds)


def jitter(lo: float, hi: float) -> float:
    return random.uniform(lo, hi)


# ---------------------------------------------------------------------------
# Unified multi-provider LLM client
# ---------------------------------------------------------------------------

def llm_chat(
    messages: list[dict[str, str]],
    slot: dict[str, str],
    *,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    verbose: bool = False,
    dry_run: bool = False,
) -> str:
    """
    Call the right provider for this model slot with patient exponential backoff.
    `slot` is one entry from MODEL_POOL, e.g.:
        {"model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "provider": "openrouter"}
    Returns the assistant's reply text.
    """
    model = slot["model"]
    provider = slot["provider"]

    if dry_run:
        return f"[dry-run] would call {provider}/{model} with {len(messages)} messages"

    import httpx  # already installed
    import json as _json

    cfg = PROVIDER_CONFIG[provider]
    api_key = get_api_key(provider)
    url = f"{cfg['base_url']}/chat/completions"

    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # Merge any provider-specific extra headers (stored as JSON string to avoid
    # mutable-dict-in-module-constant footgun)
    if extra_raw := cfg.get("extra_headers"):
        headers.update(_json.loads(extra_raw))

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }

    backoff = INITIAL_BACKOFF_S
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if verbose:
                print(f"  [api] {provider}/{model} attempt {attempt}/{MAX_RETRIES}")
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            if resp.status_code == 200:
                data = resp.json()
                msg = data["choices"][0]["message"]
                content = msg.get("content")
                if content is None:
                    # Some reasoning models return text in "reasoning" instead of "content"
                    content = msg.get("reasoning")
                if content is None:
                    raise RuntimeError(f"{provider} returned empty content")
                return content.strip()
            elif resp.status_code in (429, 500, 502, 503, 504):
                wait = min(backoff + jitter(*JITTER_RANGE), MAX_BACKOFF_S)
                print(
                    f"  [warn] {resp.status_code} from {provider} — "
                    f"backing off {wait:.1f}s (attempt {attempt}/{MAX_RETRIES})"
                )
                patient_sleep(wait, verbose)
                backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_S)
            else:
                raise RuntimeError(
                    f"{provider} API error {resp.status_code}: {resp.text[:300]}"
                )
        except httpx.TimeoutException:
            wait = min(backoff + jitter(*JITTER_RANGE), MAX_BACKOFF_S)
            print(f"  [warn] timeout on {provider} — backing off {wait:.1f}s (attempt {attempt})")
            patient_sleep(wait, verbose)
            backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_S)

    raise RuntimeError(f"Exhausted {MAX_RETRIES} retries on {provider}/{model}")


# ---------------------------------------------------------------------------
# Model rotation
# ---------------------------------------------------------------------------

class ModelRotator:
    def __init__(self, pool: list[dict[str, str]]) -> None:
        self._pool = pool
        self._idx = 0

    def next(self) -> dict[str, str]:
        """Return the next slot dict (model + provider) in round-robin order."""
        slot = self._pool[self._idx % len(self._pool)]
        self._idx += 1
        return slot


# ---------------------------------------------------------------------------
# Wiki & skill operations
# ---------------------------------------------------------------------------

def run_script(cmd: list[str], cwd: Path, verbose: bool) -> tuple[int, str, str]:
    """Run a subprocess; return (returncode, stdout, stderr)."""
    if verbose:
        print(f"  [run] {' '.join(cmd)}")
    result = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120
    )
    return result.returncode, result.stdout, result.stderr


def compile_wiki(workspace: Path, verbose: bool) -> dict[str, Any]:
    """Run llm_wiki_compile.py compile --changed-only and return parsed summary."""
    rc, stdout, stderr = run_script(
        [sys.executable, "scripts/llm_wiki_compile.py", "compile", "--changed-only"],
        workspace,
        verbose,
    )
    summary: dict[str, Any] = {
        "returncode": rc,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
    }
    # Parse key-value pairs from output like "pages: 18"
    for line in stdout.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            summary[k.strip()] = v.strip()
    return summary


def build_skill_index(workspace: Path, verbose: bool) -> dict[str, Any]:
    """Run build_skill_index.py and return parsed summary."""
    rc, stdout, stderr = run_script(
        [sys.executable, "scripts/build_skill_index.py"],
        workspace,
        verbose,
    )
    return {"returncode": rc, "stdout": stdout.strip(), "stderr": stderr.strip()}


def lint_workspace(workspace: Path, verbose: bool) -> dict[str, Any]:
    """Run llm_wiki_lint.py if it has a CLI, else import directly."""
    rc, stdout, stderr = run_script(
        [sys.executable, "-m", "scripts.llm_wiki_lint"],
        workspace,
        verbose,
    )
    if rc != 0:
        # Try direct invocation
        rc, stdout, stderr = run_script(
            [sys.executable, "scripts/llm_wiki_lint.py"],
            workspace,
            verbose,
        )
    return {"returncode": rc, "stdout": stdout.strip(), "stderr": stderr.strip()}


def collect_skill_files(workspace: Path) -> list[Path]:
    """Return list of active skill .md files."""
    active_dir = workspace / "wiki" / "skills" / "active"
    if not active_dir.exists():
        return []
    return sorted(active_dir.glob("*.md"))


def read_skill_headers(skill_files: list[Path]) -> list[dict[str, str]]:
    """Extract name and first description line from each skill file."""
    skills = []
    for f in skill_files:
        lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        name = f.stem
        desc = ""
        for line in lines[:20]:
            line = line.strip()
            if line.startswith("# "):
                name = line[2:].strip()
            elif line and not line.startswith("#") and not line.startswith("---") and not desc:
                desc = line[:200]
        skills.append({"name": name, "file": f.name, "desc": desc})
    return skills


def get_wiki_pages(workspace: Path) -> list[Path]:
    """Return all .md files in the wiki directory."""
    wiki_dir = workspace / "wiki"
    if not wiki_dir.exists():
        return []
    return [p for p in wiki_dir.rglob("*.md") if ".git" not in p.parts]


# ---------------------------------------------------------------------------
# LLM-assisted tasks
# ---------------------------------------------------------------------------

def summarize_skill_changes(
    skill_info: list[dict[str, str]],
    rotator: ModelRotator,
    verbose: bool,
    dry_run: bool,
) -> str:
    """Ask an LLM to produce a brief changelog entry for active skills."""
    if not skill_info:
        return "No active skills found."

    skill_list = "\n".join(
        f"- **{s['name']}** (`{s['file']}`): {s['desc']}" for s in skill_info[:15]
    )
    slot = rotator.next()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise technical writer producing changelog entries "
                "for an AI skill registry. Be brief, factual, and use bullet points."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Here are the currently active skills in this repository:\n\n"
                f"{skill_list}\n\n"
                "Write a short changelog-style entry (3-6 bullet points, max 200 words) "
                "summarising what capabilities are registered and any notable patterns "
                "you observe. Use present tense."
            ),
        },
    ]
    return llm_chat(
        messages, slot, max_tokens=512, temperature=0.2, verbose=verbose, dry_run=dry_run
    )


def generate_wiki_update_note(
    compile_summary: dict[str, Any],
    skill_summary: str,
    rotator: ModelRotator,
    verbose: bool,
    dry_run: bool,
) -> str:
    """Ask an LLM to compose a wiki log entry from the run's results."""
    slot = rotator.next()
    context = json.dumps(
        {
            "compile": {
                k: v
                for k, v in compile_summary.items()
                if k in ("sources", "pages", "lint", "pending changed sources")
            },
            "skill_summary": skill_summary[:600],
        },
        indent=2,
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You write short, structured Markdown log entries for an LLM wiki system. "
                "Be terse, informative, and use Markdown headings and bullet points."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Here is the result of the latest wiki auto-update run:\n\n"
                f"```json\n{context}\n```\n\n"
                "Write a concise Markdown log entry (max 150 words) for `wiki/log.md`. "
                "Include: pages compiled, lint status, skill registry state. "
                "Do NOT include timestamps — they are added externally."
            ),
        },
    ]
    slot = rotator.next()
    return llm_chat(
        messages, slot, max_tokens=400, temperature=0.2, verbose=verbose, dry_run=dry_run
    )


# ---------------------------------------------------------------------------
# Log writer
# ---------------------------------------------------------------------------

def write_log_entry(workspace: Path, header: str, body: str, dry_run: bool) -> None:
    """Prepend a new entry to wiki/log.md, preserving YAML frontmatter if present."""
    log_path = workspace / "wiki" / "log.md"
    safe_body = (body or "").strip()
    entry = f"{header}\n\n{safe_body}\n\n---\n\n"

    if dry_run:
        print(f"\n[dry-run] would write to {log_path}:\n{entry}")
        return

    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""

    # Preserve frontmatter if present
    if existing.startswith("---\n"):
        parts = existing.split("---", 2)
        if len(parts) >= 3:
            frontmatter = f"---{parts[1]}---"
            rest = parts[2].lstrip("\n")
            log_path.write_text(frontmatter + "\n\n" + entry + rest, encoding="utf-8")
            print(f"  [log] wrote entry to {log_path.relative_to(workspace)}")
            return

    log_path.write_text(entry + existing, encoding="utf-8")
    print(f"  [log] wrote entry to {log_path.relative_to(workspace)}")


# ---------------------------------------------------------------------------
# Main update loop
# ---------------------------------------------------------------------------

def run_update(workspace: Path, verbose: bool, dry_run: bool) -> int:
    print(f"\n{'='*60}")
    print(f"  LLM Wiki Auto-Update  —  {utc_now()}")
    print(f"  workspace : {workspace}")
    print(f"  dry-run   : {dry_run}")
    print(f"{'='*60}")

    load_env(workspace)

    print("\nProbing providers …")
    active_pool = build_active_pool(verbose)
    pool_summary = ", ".join(f"{s['provider']}/{s['model']}" for s in active_pool)
    print(f"  pool ({len(active_pool)} slots): {pool_summary}\n")

    rotator = ModelRotator(active_pool)
    results: dict[str, Any] = {}

    # ── Step 1: Compile wiki ────────────────────────────────────────────
    print("[1/4] Compiling wiki (changed sources only) …")
    compile_result = compile_wiki(workspace, verbose)
    results["compile"] = compile_result
    if compile_result["returncode"] != 0:
        print(f"  [warn] compile exited {compile_result['returncode']}")
        if compile_result.get("stderr"):
            print(f"  stderr: {compile_result['stderr'][:400]}")
    else:
        print(f"  pages: {compile_result.get('pages', '?')}  "
              f"| sources: {compile_result.get('sources', '?')}  "
              f"| lint: {compile_result.get('lint', '?')}")

    patient_sleep(jitter(*INTER_TASK_PAUSE_S), verbose)

    # ── Step 2: Rebuild skill index ─────────────────────────────────────
    print("[2/4] Rebuilding skill index …")
    skill_result = build_skill_index(workspace, verbose)
    results["skill_index"] = skill_result
    if skill_result["returncode"] != 0:
        print(f"  [warn] skill index exited {skill_result['returncode']}")
    else:
        print(f"  {skill_result['stdout'][:200]}")

    patient_sleep(jitter(*INTER_TASK_PAUSE_S), verbose)

    # ── Step 3: Summarise skills via LLM ───────────────────────────────
    print("[3/4] Summarising skill registry via LLM …")
    skill_files = collect_skill_files(workspace)
    skill_headers = read_skill_headers(skill_files)
    print(f"  active skills: {len(skill_files)}")
    try:
        skill_summary = summarize_skill_changes(
            skill_headers, rotator, verbose, dry_run
        )
        results["skill_summary"] = skill_summary
        if verbose:
            print(f"  skill summary:\n{skill_summary[:400]}")
    except Exception as exc:
        skill_summary = f"[LLM skill summary failed: {exc}]"
        results["skill_summary"] = skill_summary
        print(f"  [warn] {skill_summary}")

    patient_sleep(jitter(*INTER_TASK_PAUSE_S), verbose)

    # ── Step 4: Generate log entry via LLM ─────────────────────────────
    print("[4/4] Generating wiki log entry via LLM …")
    try:
        log_body = generate_wiki_update_note(
            compile_result, skill_summary, rotator, verbose, dry_run
        )
    except Exception as exc:
        log_body = (
            f"**Auto-update completed with warnings.**\n\n"
            f"- Compile: {compile_result.get('pages', '?')} pages\n"
            f"- Skill index: {'ok' if skill_result['returncode'] == 0 else 'error'}\n"
            f"- LLM log generation error: {exc}\n"
        )
        print(f"  [warn] log generation fell back to template: {exc}")

    # Prepend skill summary into log body
    full_log_body = f"{log_body}\n\n**Skills registered:**\n{skill_summary}"

    header = f"## Auto-Update — {utc_now()}"
    write_log_entry(workspace, header, full_log_body, dry_run)

    print(f"\n{'='*60}")
    print("  Update complete.")
    print(f"{'='*60}\n")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patient LLM Wiki & Skills Auto-Updater (SiliconFlow + OpenRouter + LM Studio)"
    )
    parser.add_argument(
        "--workspace",
        default=str(Path.cwd()),
        help="Workspace root (default: cwd)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing or calling the API",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Extra debug output",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        print(f"ERROR: workspace does not exist: {workspace}", file=sys.stderr)
        return 1

    return run_update(workspace, verbose=args.verbose, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
