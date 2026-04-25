#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_TARGETS = "claude,antigravity,codex,droid,pi"
PACKET_ROOT_MARKERS = (
    Path("installers") / "install_g_kade_workspace.py",
    Path("support") / "SYSTEM_CONTRACT.md",
)
WORKSPACE_ROOT_MARKERS = (
    Path(".llm-wiki") / "config.json",
    Path("AGENTS.md"),
)
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".py", ".ps1", ".sh", ".cmd"}
EXCLUDED_SEARCH_PARTS = {
    ".git",
    ".llm-wiki/node_modules",
    ".llm-wiki/tools",
    ".tmp",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "deps",
}
WORD_RE = re.compile(r"[A-Za-z0-9_./:-]+")


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


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_slug(value: str, fallback: str = "run") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug[:80] or fallback


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_text(path: Path, limit: int = 8000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text)}


def lexical_score(query: str, text: str) -> float:
    query_terms = tokenize(query)
    if not query_terms:
        return 0.0
    text_terms = tokenize(text)
    if not text_terms:
        return 0.0
    overlap = len(query_terms & text_terms)
    return overlap / max(1, len(query_terms))


def confidence_for_score(score: float) -> str:
    if score >= 0.5:
        return "high"
    if score >= 0.2:
        return "medium"
    return "low"


def workspace_rel(workspace_root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(workspace_root.resolve(strict=False)).as_posix()
    except ValueError:
        return str(path.resolve(strict=False))


def pipeline_root(workspace_root: Path) -> Path:
    return workspace_root / ".llm-wiki" / "skill-pipeline"


def run_root(workspace_root: Path, run_id: str) -> Path:
    return pipeline_root(workspace_root) / "runs" / run_id


def is_search_excluded(path: Path, workspace_root: Path) -> bool:
    rel = workspace_rel(workspace_root, path)
    normalized = rel.replace("\\", "/")
    parts = set(normalized.split("/"))
    if parts & {".git", ".tmp", ".pytest_cache", "__pycache__", "node_modules", "deps"}:
        return True
    return any(normalized.startswith(prefix + "/") for prefix in EXCLUDED_SEARCH_PARTS if "/" in prefix)


def iter_search_files(workspace_root: Path, *, include_raw: bool = False) -> list[Path]:
    roots = [
        workspace_root / "AGENTS.md",
        workspace_root / "LLM_WIKI_MEMORY.md",
        workspace_root / "SYSTEM_CONTRACT.md",
        workspace_root / "SKILL_CREATION_AT_EXPERT_LEVEL.md",
        workspace_root / "kade",
        workspace_root / "wiki",
        workspace_root / "docs",
        workspace_root / "prompts",
        workspace_root / "support",
        workspace_root / "installers",
        workspace_root / "scripts",
        workspace_root / "tests",
    ]
    if include_raw:
        roots.append(workspace_root / "raw")
    out: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix.lower() in TEXT_EXTENSIONS:
            out.append(root)
        elif root.is_dir():
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS and not is_search_excluded(path, workspace_root):
                    out.append(path)
    return sorted(set(out))


def search_workspace(workspace_root: Path, query: str, *, limit: int = 8, include_raw: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in iter_search_files(workspace_root, include_raw=include_raw):
        text = read_text(path)
        score = lexical_score(query, text + " " + workspace_rel(workspace_root, path))
        if score <= 0:
            continue
        snippet = make_snippet(text, query)
        mtime = ""
        try:
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except OSError:
            pass
        results.append(
            {
                "source": workspace_rel(workspace_root, path),
                "retrieval": "local-hybrid-lite",
                "score": round(score, 4),
                "confidence": confidence_for_score(score),
                "last_modified": mtime,
                "snippet": snippet,
            }
        )
    results.sort(key=lambda item: (item["score"], item["last_modified"]), reverse=True)
    return results[:limit]


def make_snippet(text: str, query: str, max_chars: int = 420) -> str:
    if not text:
        return ""
    lowered = text.lower()
    positions = [lowered.find(term) for term in tokenize(query) if lowered.find(term) >= 0]
    start = max(0, min(positions) - 120) if positions else 0
    snippet = " ".join(text[start : start + max_chars].split())
    return snippet


def load_skill_suggestions(workspace_root: Path, task: str, top_n: int = 5) -> list[dict[str, Any]]:
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    try:
        import skill_index  # type: ignore

        return skill_index.suggest_skills(workspace_root, task, top_n=top_n, threshold=0.01)
    except Exception as exc:
        return [{"error": f"skill suggestions unavailable: {exc}"}]


def recent_log_lessons(workspace_root: Path, task: str, limit: int = 5) -> list[dict[str, Any]]:
    log_path = workspace_root / "wiki" / "log.md"
    text = read_text(log_path, limit=50000)
    if not text:
        return []
    chunks = [chunk.strip() for chunk in re.split(r"\n(?=#+\s|\d{4}-\d{2}-\d{2}|- )", text) if chunk.strip()]
    scored = [(lexical_score(task, chunk), chunk) for chunk in chunks]
    scored = [(score, chunk) for score, chunk in scored if score > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "source": "wiki/log.md",
            "score": round(score, 4),
            "confidence": confidence_for_score(score),
            "snippet": " ".join(chunk.split())[:420],
        }
        for score, chunk in scored[:limit]
    ]


def build_context_bundle(workspace_root: Path, task: str, *, mode: str = "default", token_budget: int = 4000) -> dict[str, Any]:
    include_raw = mode in {"deep", "evidence"}
    evidence_limit = 10 if mode in {"deep", "evidence"} else 5
    bundle = {
        "version": 1,
        "generated_at": utc_now(),
        "workspace": str(workspace_root),
        "task": task,
        "mode": mode,
        "token_budget": token_budget,
        "policy": {
            "default_injection": "compact",
            "source_precedence": "current source evidence overrides memory",
            "broad_search": "explicit evidence expansion only",
        },
        "instructions": [
            item
            for item in [
                "AGENTS.md" if (workspace_root / "AGENTS.md").exists() else "",
                "LLM_WIKI_MEMORY.md" if (workspace_root / "LLM_WIKI_MEMORY.md").exists() else "",
                "kade/AGENTS.md" if (workspace_root / "kade" / "AGENTS.md").exists() else "",
                "kade/KADE.md" if (workspace_root / "kade" / "KADE.md").exists() else "",
            ]
            if item
        ],
        "skills": load_skill_suggestions(workspace_root, task, top_n=5) if mode in {"default", "deep", "skills"} else [],
        "evidence": search_workspace(workspace_root, task, limit=evidence_limit, include_raw=include_raw)
        if mode in {"default", "deep", "evidence", "graph"}
        else [],
        "recent_lessons": recent_log_lessons(workspace_root, task, limit=3) if mode in {"default", "deep"} else [],
        "preference_hints": preference_hints(workspace_root, task) if mode in {"default", "deep", "preference"} else [],
        "graph_hints": graph_hints(workspace_root, task) if mode in {"default", "deep", "graph"} else [],
        "expansion_suggestions": [
            f"llm-wiki-packet evidence --query {json.dumps(task)}",
            f"llm-wiki-packet context --mode deep --task {json.dumps(task)}",
            f"llm-wiki-packet context --mode graph --task {json.dumps(task)}",
            f"llm-wiki-packet context --mode skills --task {json.dumps(task)}",
        ],
    }
    return bundle


def preference_hints(workspace_root: Path, task: str) -> list[dict[str, Any]]:
    candidates = [workspace_root / ".factory" / "memories.md", Path.home() / ".kade" / "HUMAN.md"]
    results = []
    for path in candidates:
        if not path.exists():
            continue
        text = read_text(path)
        score = lexical_score(task, text)
        if score <= 0 and path.name == "HUMAN.md":
            score = 0.05
        results.append(
            {
                "source": workspace_rel(workspace_root, path) if path.is_relative_to(workspace_root) else str(path),
                "retrieval": "preference-file",
                "score": round(score, 4),
                "confidence": confidence_for_score(score),
                "snippet": make_snippet(text, task),
            }
        )
    return results[:3]


def graph_hints(workspace_root: Path, task: str) -> list[dict[str, Any]]:
    config = load_json(workspace_root / ".llm-wiki" / "config.json")
    gitvizz = config.get("gitvizz", {}) if isinstance(config.get("gitvizz"), dict) else {}
    hints = []
    if gitvizz:
        hints.append(
            {
                "source": ".llm-wiki/config.json",
                "retrieval": "gitvizz-config",
                "confidence": "medium",
                "frontend_url": gitvizz.get("frontend_url", ""),
                "backend_url": gitvizz.get("backend_url", ""),
                "repo_path": gitvizz.get("repo_path") or gitvizz.get("checkout_path") or "",
                "suggested_next": "Use GitVizz when code topology, routes, or API relationships matter.",
            }
        )
    code_hits = search_workspace(workspace_root, task, limit=3, include_raw=False)
    for hit in code_hits:
        if hit["source"].startswith(("support/", "scripts/", "installers/")):
            hints.append(hit)
    return hints[:5]


def print_payload(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(markdown_payload(payload))


def markdown_payload(payload: dict[str, Any]) -> str:
    lines = [f"# {payload.get('command', 'llm-wiki packet output')}", ""]
    for key in ("task", "query", "run_id", "mode"):
        if payload.get(key):
            lines.append(f"- {key}: `{payload[key]}`")
    if payload.get("policy"):
        lines.extend(["", "## Policy"])
        for key, value in payload["policy"].items():
            lines.append(f"- {key}: {value}")
    for section in ("instructions", "skills", "evidence", "recent_lessons", "preference_hints", "graph_hints", "expansion_suggestions", "artifacts", "decision"):
        value = payload.get(section)
        if not value:
            continue
        lines.extend(["", f"## {section.replace('_', ' ').title()}"])
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    label = item.get("title") or item.get("source") or item.get("id") or item.get("suggested_next") or "item"
                    detail = item.get("snippet") or item.get("fast_path") or item.get("confidence") or ""
                    lines.append(f"- **{label}** {detail}".rstrip())
                else:
                    lines.append(f"- `{item}`" if "/" in str(item) else f"- {item}")
        elif isinstance(value, dict):
            for key, item in value.items():
                lines.append(f"- {key}: {item}")
        else:
            lines.append(str(value))
    return "\n".join(lines) + "\n"


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
    if args.qmd_source_checkout:
        command.extend(["--qmd-source-checkout", args.qmd_source_checkout])
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


def command_context(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    task = args.task or read_text(Path(args.task_file), limit=12000) if args.task_file else args.task
    if not task:
        raise SystemExit("context requires --task or --task-file")
    payload = build_context_bundle(workspace_root, task, mode=args.mode, token_budget=args.token_budget)
    payload["command"] = "llm-wiki-packet context"
    print_payload(payload, args.json)
    return 0


def command_evidence(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    query = args.query or read_text(Path(args.query_file), limit=12000) if args.query_file else args.query
    if not query:
        raise SystemExit("evidence requires --query or --query-file")
    results = search_workspace(workspace_root, query, limit=args.limit, include_raw=args.include_raw or args.deep)
    payload = {
        "command": "llm-wiki-packet evidence",
        "version": 1,
        "generated_at": utc_now(),
        "workspace": str(workspace_root),
        "query": query,
        "mode": "deep" if args.deep else "evidence",
        "policy": {
            "retrieval": "broad search is explicit",
            "injection": "rerank and inject only cited results needed for the task",
            "source_precedence": "current source evidence overrides memory",
        },
        "evidence": results,
        "expansion_suggestions": [
            f"llm-wiki-packet context --mode default --task {json.dumps(query)}",
            f"llm-wiki-packet context --mode graph --task {json.dumps(query)}",
        ],
    }
    print_payload(payload, args.json)
    return 0


def command_manifest(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    seed = args.title or args.task or "agentic-run"
    run_id = args.run_id or f"{safe_slug(seed)}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}"
    root = run_root(workspace_root, run_id)
    manifest = {
        "version": 1,
        "run_id": run_id,
        "created_at": utc_now(),
        "workspace": str(workspace_root),
        "title": args.title or seed,
        "task": args.task,
        "success_criteria": [item for item in args.success_criteria if item],
        "prompt_version": args.prompt_version,
        "tool_version": args.tool_version,
        "model": args.model,
        "skills": args.skill,
        "budget": {
            "tokens": args.token_budget,
            "seconds": args.timeout_sec,
        },
        "artifacts": {
            "root": workspace_rel(workspace_root, root),
            "manifest": workspace_rel(workspace_root, root / "manifest.json"),
            "reducer_packet": workspace_rel(workspace_root, root / "reducer_packet.md"),
            "claims": workspace_rel(workspace_root, root / "claims.json"),
            "evaluation": workspace_rel(workspace_root, root / "evaluation.json"),
            "promotion": workspace_rel(workspace_root, root / "promotion_decision.json"),
            "improvement": workspace_rel(workspace_root, root / "improvement_proposal.json"),
        },
    }
    write_json(root / "manifest.json", manifest)
    payload = {"command": "llm-wiki-packet manifest", "run_id": run_id, "artifacts": manifest["artifacts"]}
    print_payload(payload, args.json)
    return 0


def ensure_manifest(workspace_root: Path, run_id: str, task: str = "") -> dict[str, Any]:
    root = run_root(workspace_root, run_id)
    manifest_path = root / "manifest.json"
    manifest = load_json(manifest_path)
    if manifest:
        return manifest
    manifest = {
        "version": 1,
        "run_id": run_id,
        "created_at": utc_now(),
        "workspace": str(workspace_root),
        "title": run_id,
        "task": task,
        "success_criteria": [],
        "prompt_version": "",
        "tool_version": "",
        "model": "",
        "skills": [],
        "budget": {},
        "artifacts": {
            "root": workspace_rel(workspace_root, root),
            "manifest": workspace_rel(workspace_root, manifest_path),
            "reducer_packet": workspace_rel(workspace_root, root / "reducer_packet.md"),
            "claims": workspace_rel(workspace_root, root / "claims.json"),
            "evaluation": workspace_rel(workspace_root, root / "evaluation.json"),
            "promotion": workspace_rel(workspace_root, root / "promotion_decision.json"),
            "improvement": workspace_rel(workspace_root, root / "improvement_proposal.json"),
        },
    }
    write_json(manifest_path, manifest)
    return manifest


def command_reduce(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    source_text = args.text or read_text(Path(args.source_file), limit=50000) if args.source_file else args.text
    if not source_text:
        raise SystemExit("reduce requires --text or --source-file")
    run_id = args.run_id or f"reduce-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}"
    manifest = ensure_manifest(workspace_root, run_id, task=args.task or source_text[:240])
    claims = extract_claims(source_text, args.task or manifest.get("task", ""))
    root = run_root(workspace_root, run_id)
    packet = render_reducer_packet(manifest, source_text, claims)
    root.mkdir(parents=True, exist_ok=True)
    (root / "raw.txt").write_text(source_text, encoding="utf-8")
    (root / "reducer_packet.md").write_text(packet, encoding="utf-8")
    write_json(root / "claims.json", {"version": 1, "run_id": run_id, "claims": claims})
    payload = {
        "command": "llm-wiki-packet reduce",
        "run_id": run_id,
        "artifacts": {
            "raw": workspace_rel(workspace_root, root / "raw.txt"),
            "reducer_packet": workspace_rel(workspace_root, root / "reducer_packet.md"),
            "claims": workspace_rel(workspace_root, root / "claims.json"),
        },
    }
    print_payload(payload, args.json)
    return 0


def extract_claims(text: str, task: str) -> list[dict[str, Any]]:
    sentences = re.split(r"(?<=[.!?])\s+|\n+-\s+", text)
    claims: list[dict[str, Any]] = []
    for sentence in sentences:
        cleaned = " ".join(sentence.strip().split())
        if len(cleaned) < 24:
            continue
        evidence = re.findall(r"https?://[^\s)>\]]+", cleaned)
        confidence = "medium" if evidence else "low"
        claims.append(
            {
                "claim": cleaned[:700],
                "evidence": evidence,
                "confidence": confidence,
                "claim_type": "finding",
                "verification_method": "citation-present" if evidence else "unverified-reducer",
                "source_diversity": len(set(evidence)),
                "cohort_agreement": "",
                "contradictions": [],
            }
        )
        if len(claims) >= 20:
            break
    if not claims and task:
        claims.append(
            {
                "claim": task,
                "evidence": [],
                "confidence": "low",
                "claim_type": "task-summary",
                "verification_method": "manifest-only",
                "source_diversity": 0,
                "cohort_agreement": "",
                "contradictions": [],
            }
        )
    return claims


def render_reducer_packet(manifest: dict[str, Any], source_text: str, claims: list[dict[str, Any]]) -> str:
    run_id = manifest["run_id"]
    lines = [
        f"# Reducer Packet: {run_id}",
        "",
        "## Task",
        "",
        str(manifest.get("task") or manifest.get("title") or run_id),
        "",
        "## Durable Facts",
        "",
    ]
    for claim in claims:
        marker = "[VERIFY]" if claim["confidence"] == "low" else ""
        lines.append(f"- {marker} {claim['claim']}".strip())
    lines.extend(["", "## Evidence", ""])
    for claim in claims:
        for url in claim.get("evidence", []):
            lines.append(f"- {url}")
    if not any(claim.get("evidence") for claim in claims):
        lines.append("- No citations detected; keep claims out of durable memory until verified.")
    lines.extend(
        [
            "",
            "## Contradictions",
            "",
            "- None detected by the reducer.",
            "",
            "## Skill Candidates",
            "",
            "- Promote only if this run reveals a repeated procedure with validation evidence.",
            "",
            "## Open Questions",
            "",
            "- Review low-confidence or uncited claims before promotion.",
            "",
            "## Raw Summary",
            "",
            " ".join(source_text.split())[:1200],
            "",
        ]
    )
    return "\n".join(lines)


def command_promote(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    root = run_root(workspace_root, args.run_id)
    manifest = ensure_manifest(workspace_root, args.run_id)
    packet_path = root / "reducer_packet.md"
    packet = read_text(packet_path, limit=50000)
    if not packet:
        raise SystemExit(f"Missing reducer packet for run: {args.run_id}")
    target = args.target
    actions: list[dict[str, Any]] = []
    if target in {"auto", "semantic"}:
        title = safe_slug(str(manifest.get("title") or args.run_id), fallback=args.run_id)
        wiki_path = workspace_root / "wiki" / "syntheses" / f"{title}.md"
        if args.apply:
            wiki_path.parent.mkdir(parents=True, exist_ok=True)
            wiki_path.write_text(packet, encoding="utf-8")
        actions.append({"target": "semantic", "path": workspace_rel(workspace_root, wiki_path), "applied": args.apply})
    if target in {"auto", "procedural"}:
        proposal_path = pipeline_root(workspace_root) / "proposals" / f"{args.run_id}-skill-candidate.md"
        if args.apply:
            proposal_path.parent.mkdir(parents=True, exist_ok=True)
            proposal_path.write_text(packet, encoding="utf-8")
        actions.append({"target": "procedural", "path": workspace_rel(workspace_root, proposal_path), "applied": args.apply})
    if target in {"auto", "preference"}:
        actions.append({"target": "preference", "path": ".brv via brv curate", "applied": False, "reason": "BRV promotion remains explicit"})
    decision = {
        "version": 1,
        "run_id": args.run_id,
        "created_at": utc_now(),
        "target": target,
        "applied": args.apply,
        "actions": actions,
        "policy": "verified durable facts to wiki; reusable procedures to skill proposals; preferences require explicit BRV curate",
    }
    write_json(root / "promotion_decision.json", decision)
    print_payload({"command": "llm-wiki-packet promote", "run_id": args.run_id, "decision": decision, "artifacts": {"promotion": workspace_rel(workspace_root, root / "promotion_decision.json")}}, args.json)
    return 0


def command_evaluate(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    root = run_root(workspace_root, args.run_id)
    manifest = ensure_manifest(workspace_root, args.run_id)
    claims_payload = load_json(root / "claims.json")
    claims = claims_payload.get("claims", []) if isinstance(claims_payload.get("claims"), list) else []
    criteria = manifest.get("success_criteria", []) if isinstance(manifest.get("success_criteria"), list) else []
    cited = sum(1 for claim in claims if claim.get("evidence"))
    low = sum(1 for claim in claims if claim.get("confidence") == "low")
    score = 0.4
    if claims:
        score += 0.25 * (cited / len(claims))
        score += 0.15 * max(0, 1 - low / len(claims))
    if criteria:
        score += 0.1
    if (root / "reducer_packet.md").exists():
        score += 0.1
    score = round(min(score, 1.0), 4)
    evaluation = {
        "version": 1,
        "run_id": args.run_id,
        "created_at": utc_now(),
        "score": score,
        "task_success": "unknown" if not args.task_success else args.task_success,
        "citation_quality": "medium" if cited else "low",
        "retrieval_sufficiency": args.retrieval_sufficiency,
        "contradiction_handling": "not-assessed",
        "regressions": [],
        "recommendation": "promote-with-review" if score >= args.threshold else "do-not-promote",
    }
    write_json(root / "evaluation.json", evaluation)
    print_payload({"command": "llm-wiki-packet evaluate", "run_id": args.run_id, "decision": evaluation, "artifacts": {"evaluation": workspace_rel(workspace_root, root / "evaluation.json")}}, args.json)
    return 0


def command_improve(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    root = run_root(workspace_root, args.run_id)
    evaluation = load_json(root / "evaluation.json")
    if not evaluation:
        raise SystemExit(f"Missing evaluation for run: {args.run_id}")
    accepted = bool(args.benchmark_passed and args.no_regression and float(evaluation.get("score", 0.0)) >= args.min_score)
    proposal = {
        "version": 1,
        "run_id": args.run_id,
        "created_at": utc_now(),
        "status": "accepted" if accepted else "blocked",
        "benchmark_passed": args.benchmark_passed,
        "no_regression": args.no_regression,
        "min_score": args.min_score,
        "evaluation_score": evaluation.get("score", 0.0),
        "proposal": args.proposal or "Review reducer packet and failure signals before changing prompts, tools, or skills.",
        "gate": "promotion requires benchmark_passed=true, no_regression=true, and score >= min_score",
    }
    write_json(root / "improvement_proposal.json", proposal)
    print_payload({"command": "llm-wiki-packet improve", "run_id": args.run_id, "decision": proposal, "artifacts": {"improvement": workspace_rel(workspace_root, root / "improvement_proposal.json")}}, args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-wiki-packet",
        description="Packet-owned CLI surface for project init, context/evidence retrieval, run lifecycle artifacts, and benchmarks.",
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
        "--qmd-source-checkout",
        help="Optional local pk-qmd checkout to prefer over the managed git fallback.",
    )
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

    context_parser = subparsers.add_parser(
        "context",
        help="Build a compact task-shaped context bundle with explicit expansion suggestions.",
    )
    context_parser.add_argument("--workspace-root", help="Activated workspace root. Defaults to the current repo.")
    context_parser.add_argument("--task", default="", help="Task text to plan retrieval for.")
    context_parser.add_argument("--task-file", default="", help="Read task text from a file.")
    context_parser.add_argument(
        "--mode",
        choices=("default", "deep", "evidence", "graph", "skills", "preference"),
        default="default",
        help="Context mode. Default stays compact; deep and evidence expand retrieval.",
    )
    context_parser.add_argument("--token-budget", type=int, default=4000, help="Intended context budget for downstream injection.")
    context_parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    context_parser.set_defaults(func=command_context)

    evidence_parser = subparsers.add_parser(
        "evidence",
        help="Run explicit broad local hybrid/source-backed evidence search.",
    )
    evidence_parser.add_argument("--workspace-root", help="Activated workspace root. Defaults to the current repo.")
    evidence_parser.add_argument("--query", default="", help="Evidence query.")
    evidence_parser.add_argument("--query-file", default="", help="Read evidence query from a file.")
    evidence_parser.add_argument("--limit", type=int, default=10, help="Maximum result count.")
    evidence_parser.add_argument("--deep", action="store_true", help="Include raw source folders in search.")
    evidence_parser.add_argument("--include-raw", action="store_true", help="Include raw source folders in search.")
    evidence_parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    evidence_parser.set_defaults(func=command_evidence)

    manifest_parser = subparsers.add_parser("manifest", help="Create a versioned run manifest.")
    manifest_parser.add_argument("--workspace-root", help="Activated workspace root. Defaults to the current repo.")
    manifest_parser.add_argument("--run-id", default="", help="Optional stable run id.")
    manifest_parser.add_argument("--title", default="", help="Run title.")
    manifest_parser.add_argument("--task", default="", help="Run task.")
    manifest_parser.add_argument("--success-criteria", action="append", default=[], help="Repeatable success criterion.")
    manifest_parser.add_argument("--prompt-version", default="", help="Prompt version id.")
    manifest_parser.add_argument("--tool-version", default="", help="Tool version id.")
    manifest_parser.add_argument("--model", default="", help="Model id.")
    manifest_parser.add_argument("--skill", action="append", default=[], help="Skill id used in the run.")
    manifest_parser.add_argument("--token-budget", type=int, default=0, help="Optional token budget.")
    manifest_parser.add_argument("--timeout-sec", type=int, default=0, help="Optional run timeout.")
    manifest_parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    manifest_parser.set_defaults(func=command_manifest)

    reduce_parser = subparsers.add_parser("reduce", help="Reduce raw run output into a structured memory packet.")
    reduce_parser.add_argument("--workspace-root", help="Activated workspace root. Defaults to the current repo.")
    reduce_parser.add_argument("--run-id", default="", help="Run id. Created if omitted.")
    reduce_parser.add_argument("--task", default="", help="Task summary.")
    reduce_parser.add_argument("--text", default="", help="Raw text to reduce.")
    reduce_parser.add_argument("--source-file", default="", help="Read raw text from a file.")
    reduce_parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    reduce_parser.set_defaults(func=command_reduce)

    promote_parser = subparsers.add_parser("promote", help="Route a reducer packet to the correct memory layer.")
    promote_parser.add_argument("--workspace-root", help="Activated workspace root. Defaults to the current repo.")
    promote_parser.add_argument("--run-id", required=True, help="Run id to promote.")
    promote_parser.add_argument("--target", choices=("auto", "semantic", "procedural", "preference"), default="auto")
    promote_parser.add_argument("--apply", action="store_true", help="Actually write promoted artifacts; default is decision only.")
    promote_parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    promote_parser.set_defaults(func=command_promote)

    evaluate_parser = subparsers.add_parser("evaluate", help="Score a run for promotion and improvement gating.")
    evaluate_parser.add_argument("--workspace-root", help="Activated workspace root. Defaults to the current repo.")
    evaluate_parser.add_argument("--run-id", required=True, help="Run id to evaluate.")
    evaluate_parser.add_argument("--task-success", choices=("pass", "fail", "unknown"), default="")
    evaluate_parser.add_argument("--retrieval-sufficiency", choices=("sufficient", "insufficient", "unknown"), default="unknown")
    evaluate_parser.add_argument("--threshold", type=float, default=0.7, help="Promotion recommendation threshold.")
    evaluate_parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    evaluate_parser.set_defaults(func=command_evaluate)

    improve_parser = subparsers.add_parser("improve", help="Create a gated prompt/tool/skill improvement proposal.")
    improve_parser.add_argument("--workspace-root", help="Activated workspace root. Defaults to the current repo.")
    improve_parser.add_argument("--run-id", required=True, help="Run id to improve from.")
    improve_parser.add_argument("--proposal", default="", help="Optional improvement proposal text.")
    improve_parser.add_argument("--benchmark-passed", action="store_true", help="Required for accepted improvement.")
    improve_parser.add_argument("--no-regression", action="store_true", help="Required for accepted improvement.")
    improve_parser.add_argument("--min-score", type=float, default=0.7, help="Required evaluation score.")
    improve_parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    improve_parser.set_defaults(func=command_improve)

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
