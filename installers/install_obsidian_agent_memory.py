#!/usr/bin/env python3
"""
Install the LLM Wiki prompt packet into an Obsidian vault for Claude Code,
Antigravity, Codex, and Droid-compatible setups.

Usage:
  python3 install_obsidian_agent_memory.py --vault "/path/to/Vault"
  python3 install_obsidian_agent_memory.py --vault "/path/to/Vault" --targets claude,antigravity,codex,droid --force
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

PACKET_ROOT = Path(__file__).resolve().parents[1]
PROMPTS = PACKET_ROOT / "prompts"
ASSET_ROOT = PACKET_ROOT / "installers" / "assets" / "vault"
SUPPORT = PACKET_ROOT / "support"

TARGETS_ALL = ("claude", "antigravity", "codex", "droid")
STACK_CONFIG_PATH = ".llm-wiki/config.json"
STACK_DEPENDENCY_MANIFEST_PATH = ".llm-wiki/package.json"
STACK_GITIGNORE_PATH = ".llm-wiki/.gitignore"

ROOT_FILES = {
    "AGENTS.md": PROMPTS / "01-AGENTS.md",
    "CLAUDE.md": PROMPTS / "02-CLAUDE.md",
    "LLM_WIKI_MEMORY.md": SUPPORT / "LLM_WIKI_MEMORY.md",
}

CLAUDE_FILES = {
    ".claude/commands/wiki-ingest.md": PROMPTS / "09-claude-command-ingest.md",
    ".claude/commands/wiki-query.md": PROMPTS / "10-claude-command-query.md",
    ".claude/commands/wiki-lint.md": PROMPTS / "11-claude-command-lint.md",
}

ANTIGRAVITY_FILES = {
    ".agent/workflows/wiki-ingest.md": PROMPTS / "06-antigravity-ingest-workflow.md",
    ".agent/workflows/wiki-query.md": PROMPTS / "07-antigravity-query-workflow.md",
    ".agent/workflows/wiki-lint.md": PROMPTS / "08-antigravity-lint-workflow.md",
}

CODEX_FILES = {
    ".agents/skills/llm-wiki-organizer/SKILL.md": PROMPTS / "03-codex-skill-SKILL.md",
    ".agents/skills/llm-wiki-organizer/assets/system-prompt.md": PROMPTS / "00-system-prompt.md",
    ".agents/skills/llm-wiki-organizer/assets/tool-directives.md": PROMPTS / "04-tool-directives.md",
    ".agents/skills/llm-wiki-organizer/assets/output-contract.md": PROMPTS / "05-output-contract.md",
}

STACK_FILES = {
    "scripts/check_llm_wiki_memory.ps1": ASSET_ROOT / "scripts" / "check_llm_wiki_memory.ps1",
    "scripts/check_llm_wiki_memory.sh": ASSET_ROOT / "scripts" / "check_llm_wiki_memory.sh",
    "scripts/setup_llm_wiki_memory.ps1": SUPPORT / "scripts" / "setup_llm_wiki_memory.ps1",
    "scripts/setup_llm_wiki_memory.sh": SUPPORT / "scripts" / "setup_llm_wiki_memory.sh",
    "scripts/qmd_embed_runner.mjs": SUPPORT / "scripts" / "qmd_embed_runner.mjs",
    "scripts/invoke_bash_helper.ps1": SUPPORT / "scripts" / "invoke_bash_helper.ps1",
    "scripts/brv_query.ps1": SUPPORT / "scripts" / "brv_query.ps1",
    "scripts/brv_query.sh": SUPPORT / "scripts" / "brv_query.sh",
    "scripts/brv_curate.ps1": SUPPORT / "scripts" / "brv_curate.ps1",
    "scripts/brv_curate.sh": SUPPORT / "scripts" / "brv_curate.sh",
    "scripts/brv_benchmark.py": SUPPORT / "scripts" / "brv_benchmark.py",
    "scripts/brv_benchmark.ps1": SUPPORT / "scripts" / "brv_benchmark.ps1",
    "scripts/brv_benchmark.sh": SUPPORT / "scripts" / "brv_benchmark.sh",
    "scripts/gitvizz_api.ps1": SUPPORT / "scripts" / "gitvizz_api.ps1",
    "scripts/gitvizz_api.sh": SUPPORT / "scripts" / "gitvizz_api.sh",
    "scripts/launch_gitvizz.ps1": SUPPORT / "scripts" / "launch_gitvizz.ps1",
    "scripts/launch_gitvizz.sh": SUPPORT / "scripts" / "launch_gitvizz.sh",
}

BOOTSTRAP_FILES = {
    "wiki/index.md": "# Wiki Index\n\n",
    "wiki/log.md": "# Wiki Log\n\n",
    "raw/.gitkeep": "",
    "raw/assets/.gitkeep": "",
    "wiki/sources/.gitkeep": "",
    "wiki/entities/.gitkeep": "",
    "wiki/concepts/.gitkeep": "",
    "wiki/syntheses/.gitkeep": "",
    "wiki/comparisons/.gitkeep": "",
    "wiki/timelines/.gitkeep": "",
    "wiki/questions/.gitkeep": "",
    "templates/.gitkeep": "",
    "scripts/.gitkeep": "",
    ".llm-wiki/.gitkeep": "",
    ".llm-wiki/.gitignore": "node_modules/\npackage-lock.json\n",
    ".brv/.gitkeep": "",
    ".brv/context-tree/.gitkeep": "",
    ".llm-wiki/qmd-embed-state.json": "{\n  \"status\": \"not-run\"\n}\n",
}


def env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def normalize_url(value: str) -> str:
    return value.rstrip("/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, help="Path to the Obsidian vault")
    parser.add_argument(
        "--targets",
        default="claude,antigravity,codex,droid",
        help="Comma-separated targets: claude,antigravity,codex,droid",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files managed by this installer",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing files",
    )
    parser.add_argument(
        "--qmd-command",
        default=env_or_default("LLM_WIKI_QMD_COMMAND", "pk-qmd"),
        help="Command name for the custom QMD fork",
    )
    parser.add_argument(
        "--qmd-repo-url",
        default=env_or_default("LLM_WIKI_QMD_REPO_URL", "https://github.com/kingkillery/pk-qmd"),
        help="Packet fallback source for the custom pk-qmd fork",
    )
    parser.add_argument(
        "--qmd-mcp-url",
        default=env_or_default("LLM_WIKI_QMD_MCP_URL", "http://localhost:8181/mcp"),
        help="HTTP MCP endpoint for the shared pk-qmd server",
    )
    parser.add_argument(
        "--brv-command",
        default=env_or_default("LLM_WIKI_BRV_COMMAND", "brv"),
        help="Command name for the Byterover CLI",
    )
    parser.add_argument(
        "--gitvizz-frontend-url",
        default=env_or_default("LLM_WIKI_GITVIZZ_FRONTEND_URL", "http://localhost:3000"),
        help="Frontend URL for the GitVizz web app",
    )
    parser.add_argument(
        "--gitvizz-backend-url",
        default=env_or_default("LLM_WIKI_GITVIZZ_BACKEND_URL", "http://localhost:8003"),
        help="Backend URL for the GitVizz API service",
    )
    parser.add_argument(
        "--gitvizz-repo-path",
        default=env_or_default("LLM_WIKI_GITVIZZ_REPO_PATH", ""),
        help="Optional local checkout path for launching GitVizz via docker-compose",
    )
    return parser.parse_args()


def write_text(dst: Path, text: str, force: bool, dry_run: bool) -> str:
    if dst.exists() and not force:
        return f"skip   {dst} (exists)"
    if dry_run:
        return f"write  {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return f"write  {dst}"


def write_json(dst: Path, data: dict[str, object], force: bool, dry_run: bool) -> str:
    if dst.exists() and not force:
        return f"skip   {dst} (exists)"
    if dry_run:
        return f"write  {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"write  {dst}"


def copy_file(src: Path, dst: Path, force: bool, dry_run: bool) -> str:
    if dst.exists() and not force:
        return f"skip   {dst} (exists)"
    if dry_run:
        return f"copy   {src} -> {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"copy   {src} -> {dst}"


def install_map(vault: Path, mapping: dict[str, Path], force: bool, dry_run: bool) -> list[str]:
    results = []
    for rel, src in mapping.items():
        results.append(copy_file(src, vault / rel, force=force, dry_run=dry_run))
    return results


def bootstrap_vault(vault: Path, force: bool, dry_run: bool) -> list[str]:
    results = []
    for rel, text in BOOTSTRAP_FILES.items():
        results.append(write_text(vault / rel, text, force=force, dry_run=dry_run))
    return results


def normalize_targets(raw: str) -> list[str]:
    targets = [x.strip().lower() for x in raw.split(",") if x.strip()]
    invalid = [x for x in targets if x not in TARGETS_ALL]
    if invalid:
        raise SystemExit(f"Unknown target(s): {', '.join(invalid)}")
    ordered = []
    for x in TARGETS_ALL:
        if x in targets:
            ordered.append(x)
    return ordered


def build_stack_config(args: argparse.Namespace) -> dict[str, object]:
    frontend_url = normalize_url(args.gitvizz_frontend_url)
    backend_url = normalize_url(args.gitvizz_backend_url)
    qmd_mcp_url = normalize_url(args.qmd_mcp_url)
    vault_name = Path(args.vault).expanduser().resolve().name.lower().replace(" ", "-")
    qmd_context = f"Primary llm-wiki-memory vault for {Path(args.vault).expanduser().resolve()}"

    return {
        "version": 1,
        "stack": {
            "retrieval": {
                "primary": "pk-qmd",
                "memory": "byterover",
                "graph": "gitvizz",
            },
            "policy": {
                "hide_tool_names_from_end_users": True,
                "prefer_source_evidence_over_memory": True,
                "qmd_for_repo_specific_tasks": True,
                "brv_for_durable_preferences_and_decisions": True,
            },
        },
        "pk_qmd": {
            "command": args.qmd_command,
            "local_command_candidates": [
                ".llm-wiki/node_modules/.bin/pk-qmd",
                ".llm-wiki/node_modules/.bin/pk-qmd.cmd",
                ".llm-wiki/node_modules/.bin/pk-qmd.ps1",
            ],
            "repo_url": args.qmd_repo_url,
            "manual_install_required": True,
            "mcp_url": qmd_mcp_url,
            "collection_name": vault_name,
            "context": qmd_context,
            "local_dependency_manifest": STACK_DEPENDENCY_MANIFEST_PATH,
        },
        "byterover": {
            "command": args.brv_command,
            "api_key_env": "BYTEROVER_API_KEY",
            "working_dir": ".brv",
            "context_tree_dir": ".brv/context-tree",
            "default_provider": "openrouter",
            "default_model": "google/gemini-3.1-flash-lite-preview",
            "query_experiment_provider": "google",
            "query_experiment_model": "google/gemini-3.1-flash-lite-preview",
            "curate_preferred_provider": "openrouter",
            "curate_preferred_model": "google/gemini-3.1-flash-lite-preview",
            "candidate_models": [
                "google/gemini-3.1-flash-lite-preview",
                "openai/gpt-oss-safeguard-20b",
                "x-ai/grok-4.20-multi-agent",
                "liquid/lfm-2.5-1.2b-thinking:free",
                "openai/gpt-5-nano",
                "arcee-ai/trinity-large-thinking",
            ],
            "query_format": "json",
            "curate_format": "json",
        },
        "gitvizz": {
            "frontend_url": frontend_url,
            "backend_url": backend_url,
            "api_base_url": f"{backend_url}/api",
            "homepage_url": f"{frontend_url}/",
            "setup_url": f"{frontend_url}/",
            "github_callback_url": f"{frontend_url}/api/auth/callback/github",
            "repo_path": args.gitvizz_repo_path or None,
        },
    }


def build_stack_dependency_manifest(args: argparse.Namespace) -> dict[str, object]:
    repo_url = args.qmd_repo_url
    dependency_spec = repo_url if repo_url.startswith("git+") else f"git+{repo_url}.git" if repo_url.startswith("https://github.com/") and not repo_url.endswith(".git") else f"git+{repo_url}" if repo_url.startswith("https://") else repo_url
    if dependency_spec.endswith(".git.git"):
        dependency_spec = dependency_spec[:-4]

    return {
        "name": "llm-wiki-memory-local",
        "private": True,
        "version": "0.1.0",
        "description": "Local dependency bundle for llm-wiki-memory",
        "dependencies": {
            "@kingkillery/pk-qmd": dependency_spec,
        },
    }


def main() -> int:
    args = parse_args()
    vault = Path(args.vault).expanduser().resolve()
    targets = normalize_targets(args.targets)

    if not vault.exists():
        raise SystemExit(f"Vault does not exist: {vault}")
    if not vault.is_dir():
        raise SystemExit(f"Vault is not a directory: {vault}")

    actions: list[str] = []
    actions.extend(bootstrap_vault(vault, force=args.force, dry_run=args.dry_run))

    actions.extend(install_map(vault, ROOT_FILES, force=args.force, dry_run=args.dry_run))

    if "claude" in targets:
        actions.extend(install_map(vault, CLAUDE_FILES, force=args.force, dry_run=args.dry_run))

    if "antigravity" in targets:
        actions.extend(install_map(vault, ANTIGRAVITY_FILES, force=args.force, dry_run=args.dry_run))

    if "codex" in targets:
        actions.extend(install_map(vault, CODEX_FILES, force=args.force, dry_run=args.dry_run))

    actions.extend(install_map(vault, STACK_FILES, force=args.force, dry_run=args.dry_run))
    actions.append(
        write_json(vault / STACK_CONFIG_PATH, build_stack_config(args), force=args.force, dry_run=args.dry_run)
    )
    actions.append(
        write_json(vault / STACK_DEPENDENCY_MANIFEST_PATH, build_stack_dependency_manifest(args), force=args.force, dry_run=args.dry_run)
    )

    if "droid" in targets:
        actions.append("info   Droid target uses root AGENTS.md")

    summary = [
        f"Vault:   {vault}",
        f"Targets: {', '.join(targets)}",
        f"Mode:    {'dry-run' if args.dry_run else 'write'}",
        "",
        *actions,
    ]
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
