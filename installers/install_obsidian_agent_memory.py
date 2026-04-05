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
import shutil
import sys
from pathlib import Path

PACKET_ROOT = Path(__file__).resolve().parents[1]
PROMPTS = PACKET_ROOT / "prompts"

TARGETS_ALL = ("claude", "antigravity", "codex", "droid")

ROOT_FILES = {
    "AGENTS.md": PROMPTS / "01-AGENTS.md",
    "CLAUDE.md": PROMPTS / "02-CLAUDE.md",
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
}

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
    return parser.parse_args()

def write_text(dst: Path, text: str, force: bool, dry_run: bool) -> str:
    if dst.exists() and not force:
        return f"skip   {dst} (exists)"
    if dry_run:
        return f"write  {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
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

    # Shared roots
    actions.extend(install_map(vault, ROOT_FILES, force=args.force, dry_run=args.dry_run))

    if "claude" in targets:
        actions.extend(install_map(vault, CLAUDE_FILES, force=args.force, dry_run=args.dry_run))

    if "antigravity" in targets:
        actions.extend(install_map(vault, ANTIGRAVITY_FILES, force=args.force, dry_run=args.dry_run))

    if "codex" in targets:
        actions.extend(install_map(vault, CODEX_FILES, force=args.force, dry_run=args.dry_run))

    # Droid uses AGENTS.md at repo root; no extra proprietary path is assumed here.
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
