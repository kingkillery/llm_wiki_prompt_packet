#!/usr/bin/env python3
"""
Wire the LLM Wiki packet into the user's global Claude Code config.

This automates the post-install steps that previously had to be done by an
agent following the README "Agent Easy Install" prompt:

  1. Ensure ~/.claude/commands/ contains wiki-{ingest,query,lint,skill}.md,
     copying any missing files from <vault>/.claude/commands/.
  2. Insert or update the "## LLM Wiki" section in ~/.claude/CLAUDE.md so the
     "Configured vault:" line points at the freshly installed vault.

Idempotent. Safe to re-run. Designed to be called by install.sh / install.ps1
when --global-wire is passed (default-on for --wire-repo).

Usage:
  python3 wire_global_claude.py --vault "/path/to/vault" [--home-root ~] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

WIKI_COMMANDS = ("wiki-ingest.md", "wiki-query.md", "wiki-lint.md", "wiki-skill.md")
SECTION_HEADER = "## LLM Wiki"
SECTION_END_MARKER = "<!-- /llm-wiki -->"


def render_section(vault: Path) -> str:
    return f"""{SECTION_HEADER}

A persistent knowledge base is available from any project via `/wiki-query`, `/wiki-ingest`, `/wiki-skill`, `/wiki-lint`.

**First-time setup:** clone `llm_wiki_prompt_packet`, run `.\\scripts\\setup_llm_wiki_memory.ps1` (Windows) or `./scripts/setup_llm_wiki_memory.sh` (shell), then update the vault path in `~/.claude/commands/wiki-*.md` to match your install location.

**Configured vault:** `{vault}`
(If this path doesn't exist, the wiki stack is not yet set up — run setup above.)

Each command auto-detects the current project (`basename $(pwd)`) and scopes storage + retrieval to `wiki/projects/<PROJECT>/`.
Use these proactively: surface past knowledge before answering research questions, ingest durable findings, create reusable skills.
{SECTION_END_MARKER}
"""


def upsert_section(claude_md: Path, vault: Path, *, dry_run: bool) -> str:
    new_section = render_section(vault).rstrip() + "\n"
    existing = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""

    if SECTION_HEADER in existing:
        # Replace from the header to the end-marker (or to the next top-level heading
        # if the marker is missing — e.g. an older hand-written section).
        before, _, rest = existing.partition(SECTION_HEADER)
        if SECTION_END_MARKER in rest:
            _, _, after = rest.partition(SECTION_END_MARKER)
            after = after.lstrip("\r\n")
        else:
            lines = rest.splitlines(keepends=True)
            after_lines: list[str] = []
            consuming = True
            for line in lines:
                if consuming and line.startswith("## ") and line.strip() != SECTION_HEADER:
                    consuming = False
                if not consuming:
                    after_lines.append(line)
            after = "".join(after_lines)
        merged = before.rstrip() + ("\n\n" if before.strip() else "") + new_section
        if after.strip():
            merged = merged.rstrip() + "\n\n" + after.lstrip()
        action = "updated"
    else:
        sep = "\n\n" if existing.strip() and not existing.endswith("\n\n") else ""
        merged = existing + sep + new_section
        action = "inserted"

    if not dry_run:
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(merged, encoding="utf-8")
    return action


def copy_commands(src_dir: Path, dest_dir: Path, *, dry_run: bool, force: bool) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    if not src_dir.is_dir():
        for name in WIKI_COMMANDS:
            results.append((name, f"skipped (source missing: {src_dir / name})"))
        return results
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
    for name in WIKI_COMMANDS:
        src = src_dir / name
        dest = dest_dir / name
        if not src.exists():
            results.append((name, f"skipped (source missing: {src})"))
            continue
        if dest.exists() and not force:
            if dest.read_text(encoding="utf-8") == src.read_text(encoding="utf-8"):
                results.append((name, "unchanged"))
            else:
                results.append((name, "kept (existing differs; pass --force to overwrite)"))
            continue
        if not dry_run:
            shutil.copy2(src, dest)
        results.append((name, "copied"))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wire LLM Wiki into global Claude config.")
    parser.add_argument("--vault", required=True, help="Absolute path to the installed vault.")
    parser.add_argument(
        "--home-root",
        default=str(Path.home()),
        help="Override home directory (defaults to current user home).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing wiki-*.md commands.")
    args = parser.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"[wire-global] vault does not exist: {vault}", file=sys.stderr)
        return 1

    home = Path(args.home_root).expanduser().resolve()
    claude_dir = home / ".claude"
    claude_md = claude_dir / "CLAUDE.md"
    commands_dir = claude_dir / "commands"
    src_commands = vault / ".claude" / "commands"

    prefix = "[wire-global][dry-run]" if args.dry_run else "[wire-global]"
    print(f"{prefix} vault       = {vault}")
    print(f"{prefix} home        = {home}")
    print(f"{prefix} CLAUDE.md   = {claude_md}")
    print(f"{prefix} commands -> = {commands_dir}")

    results = copy_commands(src_commands, commands_dir, dry_run=args.dry_run, force=args.force)
    for name, status in results:
        print(f"{prefix}   {name}: {status}")

    action = upsert_section(claude_md, vault, dry_run=args.dry_run)
    print(f"{prefix} CLAUDE.md section: {action}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
