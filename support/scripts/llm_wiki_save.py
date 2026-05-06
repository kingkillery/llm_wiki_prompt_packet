#!/usr/bin/env python3
"""Save durable answers and research findings into the canonical wiki layer."""
from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_wiki_provider import DirectFileWikiProvider, load_config, provider_from_workspace


DEFAULT_FOLDERS = {
    "source": "wiki/sources",
    "concept": "wiki/concepts",
    "entity": "wiki/entities",
    "question": "wiki/questions",
    "synthesis": "wiki/syntheses",
    "decision": "wiki/decisions",
    "session": "wiki/sessions",
}


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def slug_title(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "Untitled"


def yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "\n" + "".join(f"  - {item}\n" for item in items)


def frontmatter(note_type: str, title: str, tags: list[str], sources: list[str], related: list[str], args: argparse.Namespace) -> str:
    lines = [
        "---",
        f"type: {note_type}",
        f'title: "{title}"',
        f"created: {today()}",
        f"updated: {today()}",
        f"tags: {yaml_list(tags).rstrip()}",
        "status: developing",
        f"related: {yaml_list(related).rstrip()}",
        f"sources: {yaml_list(sources).rstrip()}",
    ]
    if note_type == "question" and args.question:
        lines.append(f'question: "{args.question}"')
        lines.append(f"answer_quality: {args.answer_quality}")
    if note_type == "source":
        if args.url:
            lines.append(f"url: {args.url}")
        lines.append(f"confidence: {args.confidence}")
    if note_type == "decision":
        lines.append(f"decision_date: {today()}")
        lines.append("decision_status: active")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def parse_frontmatter_title(text: str) -> str:
    match = re.search(r'(?m)^title:\s*"?(.+?)"?\s*$', text)
    return match.group(1).strip() if match else ""


def configured_folders(workspace: str | Path) -> dict[str, str]:
    config = load_config(Path(workspace).expanduser().resolve(strict=False))
    wiki_layer = config.get("wiki_layer") if isinstance(config.get("wiki_layer"), dict) else {}
    folders = wiki_layer.get("folders") if isinstance(wiki_layer.get("folders"), dict) else {}
    return {**DEFAULT_FOLDERS, **{str(key): str(value) for key, value in folders.items()}}


def note_folder(note_type: str, folders: dict[str, str]) -> str:
    key = {
        "source": "sources",
        "concept": "concepts",
        "entity": "entities",
        "question": "questions",
        "synthesis": "syntheses",
        "decision": "decisions",
        "session": "sessions",
    }.get(note_type, "syntheses")
    return folders.get(key) or DEFAULT_FOLDERS.get(note_type, "wiki/syntheses")


def find_existing(provider: DirectFileWikiProvider, folders: dict[str, str], note_type: str, title: str, sources: list[str], question: str) -> str | None:
    folder = note_folder(note_type, folders)
    desired_stem = slug_title(title).lower()
    root = provider.resolve_path(folder)
    if not root.exists():
        return None
    for note in root.glob("*.md"):
        text = note.read_text(encoding="utf-8")
        if note.stem.lower() == desired_stem or parse_frontmatter_title(text).lower() == title.lower():
            return note.relative_to(provider.vault_path).as_posix()
        if question and re.search(rf'(?m)^question:\s*"?{re.escape(question)}"?\s*$', text):
            return note.relative_to(provider.vault_path).as_posix()
        if sources and any(source in text for source in sources):
            source_title = parse_frontmatter_title(text).lower()
            if source_title == title.lower():
                return note.relative_to(provider.vault_path).as_posix()
    return None


def merge_existing(existing_text: str, body: str, sources: list[str], related: list[str]) -> str:
    updated = re.sub(r"(?m)^updated:\s*.+$", f"updated: {today()}", existing_text, count=1)
    additions: list[str] = []
    if sources:
        additions.append("Sources revisited: " + ", ".join(sources))
    if related:
        additions.append("Related: " + ", ".join(related))
    additions.append(body.rstrip())
    return updated.rstrip() + "\n\n## Update " + today() + "\n\n" + "\n".join(additions).rstrip() + "\n"


def ensure_index(provider: DirectFileWikiProvider, note_type: str, title: str, path: str) -> None:
    index_path = "wiki/index.md"
    section = {
        "source": "Sources",
        "concept": "Concepts",
        "entity": "Entities",
        "question": "Questions",
        "synthesis": "Syntheses",
        "decision": "Decisions",
        "session": "Sessions",
    }.get(note_type, "Syntheses")
    try:
        text = provider.read(index_path)
    except FileNotFoundError:
        text = "# Wiki Index\n\n"
    line = f"- [[{Path(path).stem}]]: {note_type} (status: developing)"
    if line in text:
        return
    heading = f"## {section}"
    if heading not in text:
        text = text.rstrip() + f"\n\n{heading}\n{line}\n"
    else:
        text = text.replace(heading, f"{heading}\n{line}", 1)
    provider.write(index_path, text if text.endswith("\n") else text + "\n")


def prepend_log(provider: DirectFileWikiProvider, note_type: str, title: str, path: str, action: str, sources: list[str]) -> None:
    log_path = "wiki/log.md"
    try:
        text = provider.read(log_path)
    except FileNotFoundError:
        text = "# Wiki Log\n\n"
    entry = (
        f"## [{today()}] save | {title}\n"
        f"- Type: {note_type}\n"
        f"- Location: {path}\n"
        f"- Action: {action}\n"
        f"- Sources: {', '.join(sources) if sources else 'none'}\n\n"
    )
    if text.startswith("# Wiki Log"):
        lines = text.splitlines()
        text = "\n".join(lines[:1]) + "\n\n" + entry + "\n".join(lines[1:]).lstrip() + ("\n" if text.endswith("\n") else "")
    else:
        text = entry + text
    provider.write(log_path, text)


def update_hot(provider: DirectFileWikiProvider, title: str, path: str, action: str) -> None:
    content = (
        "---\n"
        'type: meta\n'
        'title: "Hot Cache"\n'
        f"updated: {now_iso()}\n"
        "---\n\n"
        "# Recent Context\n\n"
        f"## Last Updated {today()}\n\n"
        "## Key Recent Facts\n"
        f"- {action.title()}: [[{Path(path).stem}]]\n\n"
        "## Recent Changes\n"
        f"- {action.title()}: [[{Path(path).stem}]] ({title})\n\n"
        "## Active Threads\n"
        "- No active thread recorded by this save.\n"
    )
    provider.write("wiki/hot.md", content)


def save_note(args: argparse.Namespace) -> dict[str, Any]:
    provider = provider_from_workspace(args.workspace)
    folders = configured_folders(args.workspace)
    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else args.body
    title = slug_title(args.title)
    note_type = args.type
    sources = args.source or []
    related = args.related or []
    tags = args.tag or []
    existing = None if args.mode == "create-only" else find_existing(provider, folders, note_type, title, sources, args.question)
    if existing and args.mode != "create-only":
        content = merge_existing(provider.read(existing), body, sources, related)
        result = provider.write(existing, content)
    else:
        path = f"{note_folder(note_type, folders)}/{title}.md"
        content = frontmatter(note_type, title, tags, sources, related, args) + body.rstrip() + "\n"
        result = provider.write(path, content)
    ensure_index(provider, note_type, title, result.path)
    prepend_log(provider, note_type, title, result.path, result.action, sources)
    update_hot(provider, title, result.path, result.action)
    return {"path": result.path, "action": result.action, "transport": result.transport}


def main() -> int:
    parser = argparse.ArgumentParser(description="Save a durable note to the canonical Obsidian wiki layer.")
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("--title", required=True)
    parser.add_argument("--type", default="synthesis", choices=["synthesis", "concept", "source", "decision", "session", "entity", "question"])
    parser.add_argument("--body", default="")
    parser.add_argument("--body-file", default="")
    parser.add_argument("--source", action="append")
    parser.add_argument("--related", action="append")
    parser.add_argument("--tag", action="append")
    parser.add_argument("--question", default="")
    parser.add_argument("--answer-quality", default="solid")
    parser.add_argument("--confidence", default="medium")
    parser.add_argument("--url", default="")
    parser.add_argument("--mode", choices=["create-or-update", "create-only", "update-only"], default="create-or-update")
    args = parser.parse_args()
    result = save_note(args)
    print(f"{result['action']}: {result['path']} ({result['transport']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
