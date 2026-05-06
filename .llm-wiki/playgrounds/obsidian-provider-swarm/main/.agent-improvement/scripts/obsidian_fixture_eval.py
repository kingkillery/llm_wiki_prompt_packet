from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_provider_search(repo_root: Path, query: str) -> list[dict]:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "llm_wiki_provider.py"),
        "--workspace",
        str(repo_root),
        "search",
        query,
        "--limit",
        "10",
    ]
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return []
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []


def run_packet_evidence(repo_root: Path, query: str) -> str:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "llm_wiki_packet.py"),
        "evidence",
        "--workspace-root",
        str(repo_root),
        "--query",
        query,
        "--plane",
        "local",
        "--deep",
        "--limit",
        "12",
        "--json",
    ]
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=False)
    return completed.stdout if completed.returncode == 0 else completed.stderr


def evaluate(repo_root: Path, task_id: str) -> dict:
    aliases = {
        "save": "click_deprecation_saved",
        "retrieval": "packet_local_fixture_retrieval",
    }
    task_id = aliases.get(task_id, task_id)
    click_repo = repo_root / "fixtures" / "click"
    saved_note = repo_root / "vault" / "wiki" / "syntheses" / "Click Deprecation Handling Source-Backed Synthesis.md"

    if task_id == "click_deprecation_saved":
        search_results = run_provider_search(repo_root, "Click Deprecation Handling Source-Backed Synthesis")
        passed = (
            click_repo.is_dir()
            and (click_repo / "src" / "click" / "core.py").exists()
            and (click_repo / "tests" / "test_options.py").exists()
            and saved_note.exists()
            and any("Click Deprecation Handling Source-Backed Synthesis.md" in item.get("path", "") for item in search_results)
        )
        return {
            "verifier_passed": passed,
            "success": passed,
            "verifier_score": 1.0 if passed else 0.0,
            "feedback": "Real Click repo fixture is present, source-backed synthesis is saved, and provider search retrieves it."
            if passed
            else "Expected Click fixture, saved synthesis note, and provider search hit were not all present.",
            "observations": {
                "click_repo": str(click_repo),
                "saved_note": str(saved_note),
                "search_results": search_results,
            },
        }

    if task_id == "packet_local_fixture_retrieval":
        evidence = run_packet_evidence(repo_root, "Click deprecation warnings commands options arguments parser compatibility")
        passed = "fixtures/click/src/click/core.py" in evidence or "fixtures\\\\click\\\\src\\\\click\\\\core.py" in evidence
        return {
            "verifier_passed": passed,
            "success": passed,
            "verifier_score": 1.0 if passed else 0.0,
            "feedback": "Packet local evidence found the cloned fixture repo."
            if passed
            else "Packet local evidence did not surface fixtures/click, even though direct rg found source evidence. This is a retrieval coverage issue for playground fixtures.",
            "observations": {
                "expected_source": "fixtures/click/src/click/core.py",
                "evidence_excerpt": evidence[:3000],
            },
        }

    return {
        "verifier_passed": False,
        "success": False,
        "verifier_score": 0.0,
        "feedback": f"Unknown task id: {task_id}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    result = evaluate(repo_root, args.task_id)
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
