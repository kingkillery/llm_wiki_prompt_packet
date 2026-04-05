#!/usr/bin/env python3
"""
Build release-specific bootstrap installers from the main-branch templates.

The checked-in root installers default to `main` for direct/raw usage. Release
assets should default to the release tag instead so `releases/latest/download/*`
installs remain pinned to the published version.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Expected marker not found in {label}: {old!r}")
    return text.replace(old, new, 1)


def build_ps1(tag: str) -> str:
    source = (REPO_ROOT / "install.ps1").read_text(encoding="utf-8")
    return replace_once(source, 'else { "main" }', f'else {{ "{tag}" }}', "install.ps1")


def build_sh(tag: str) -> str:
    source = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
    return replace_once(source, "LLM_WIKI_REF:-main", f"LLM_WIKI_REF:-{tag}", "install.sh")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True, help="Release tag to bake into installer defaults")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the generated release assets should be written",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()

    write_text(output_dir / "install.ps1", build_ps1(args.tag))
    write_text(output_dir / "install.sh", build_sh(args.tag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
