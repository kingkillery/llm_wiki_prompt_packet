from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


FAILURE_PROPOSAL_MAP = {
    "perception-observation-failure": "prompt-skill-instruction-patch",
    "tool-action-selection-failure": "routing-tool-rule-adjustment",
    "decomposition-planning-failure": "prompt-skill-instruction-patch",
    "missing-environment-knowledge": "memory-playbook-addition",
    "memory-recall-failure": "memory-playbook-addition",
    "verifier-mismatch-or-task-ambiguity": "benchmark-issue-flag",
}


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_repo_root(config_path: Path) -> Path:
    return config_path.resolve().parent


def create_run_dir(output_root: Path) -> Path:
    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = ensure_dir(output_root / "runs" / run_id)
    (output_root / "latest_run.txt").write_text(run_id, encoding="utf-8")
    return run_dir


def latest_run_dir(output_root: Path) -> Path:
    latest_file = output_root / "latest_run.txt"
    if not latest_file.exists():
        raise FileNotFoundError(f"No latest run found under {output_root}")
    return output_root / "runs" / latest_file.read_text(encoding="utf-8").strip()


def try_load_registry(repo_root: Path):
    sys.path.insert(0, str(repo_root))
    try:
        from benchmarks.cua_world.registry import (  # type: ignore
            get_tasks_for_environment,
            load_environment_task_splits,
            resolve_environment_dir,
            resolve_environment_key,
        )
        return {
            "get_tasks_for_environment": get_tasks_for_environment,
            "load_environment_task_splits": load_environment_task_splits,
            "resolve_environment_dir": resolve_environment_dir,
            "resolve_environment_key": resolve_environment_key,
        }
    except Exception:
        return None


def resolve_tasks(repo_root: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    task_source = config["task_source"]
    explicit_tasks = task_source.get("explicit_tasks") or []
    if explicit_tasks:
        return [
            {
                "env": entry["env"],
                "env_dir": entry.get("env_dir") or f"benchmarks/cua_world/environments/{entry['env']}_env",
                "task": entry["task"],
            }
            for entry in explicit_tasks
        ]

    selection = task_source.get("selection", {})
    envs = selection.get("envs") or []
    split = selection.get("split", "test")
    surface = selection.get("surface", "raw")
    max_tasks = int(selection.get("max_tasks", 0) or 0)
    registry = try_load_registry(repo_root)
    tasks: list[dict[str, str]] = []

    if registry:
        if envs:
            for env in envs:
                env_key = registry["resolve_environment_key"](env)
                env_dir = str(registry["resolve_environment_dir"](env))
                task_ids = registry["get_tasks_for_environment"](env_key, split=split, surface=surface)
                tasks.extend({"env": env, "env_dir": env_dir, "task": task_id} for task_id in task_ids)
        else:
            split_map = registry["load_environment_task_splits"](surface=surface)
            for env_key, env_splits in split_map.items():
                for task_id in env_splits.get(split, []):
                    env_dir = str(registry["resolve_environment_dir"](env_key))
                    tasks.append({"env": env_key, "env_dir": env_dir, "task": task_id})
    else:
        for env in envs:
            env_dir = repo_root / "benchmarks" / "cua_world" / "environments" / f"{env}_env"
            tasks_dir = env_dir / "tasks"
            if not tasks_dir.is_dir():
                continue
            for task_dir in sorted(tasks_dir.iterdir()):
                if (task_dir / "task.json").exists():
                    tasks.append({"env": env, "env_dir": str(env_dir), "task": task_dir.name})

    random.Random(int(selection.get("seed", 0) or 0)).shuffle(tasks)
    if max_tasks > 0:
        tasks = tasks[:max_tasks]
    return tasks


def partition_tasks(tasks: list[dict[str, str]], partition: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    if not tasks:
        return {"train": [], "validation": [], "holdout": []}
    ordered = list(tasks)
    random.Random(int(partition.get("seed", 0) or 0)).shuffle(ordered)
    total = len(ordered)
    train_count = int(total * float(partition.get("train", 0.6)))
    validation_count = int(total * float(partition.get("validation", 0.2)))
    if train_count <= 0 and total >= 1:
        train_count = 1
    if validation_count <= 0 and total >= 3:
        validation_count = 1
    if train_count + validation_count >= total and total > 1:
        validation_count = max(0, total - train_count - 1)
    return {
        "train": ordered[:train_count],
        "validation": ordered[train_count:train_count + validation_count],
        "holdout": ordered[train_count + validation_count:],
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def compute_success_rate(results: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0
    return round(sum(1 for item in results if item.get("success")) / len(results), 4)


def _placeholders(repo_root: Path, run_dir: Path, agent: dict[str, Any], task_record: dict[str, str], phase: str, output_json: Path) -> dict[str, str]:
    return {
        "repo_root": str(repo_root),
        "run_dir": str(run_dir),
        "agent_name": agent["name"],
        "identifier": agent.get("identifier", ""),
        "env_dir": task_record["env_dir"],
        "task_id": task_record["task"],
        "phase": phase,
        "output_json": str(output_json),
    }


def run_native_agent(repo_root: Path, run_dir: Path, config: dict[str, Any], agent: dict[str, Any], task_record: dict[str, str], phase: str) -> dict[str, Any]:
    task_dir = ensure_dir(run_dir / "task_runs" / phase / f"{agent['name']}__{task_record['env']}__{task_record['task']}")
    output_json = task_dir / "result.json"
    stdout_path = task_dir / "stdout.txt"
    stderr_path = task_dir / "stderr.txt"
    command = [
        sys.executable,
        str(repo_root / ".agent-improvement" / "scripts" / "native_eval_adapter.py"),
        "--repo-root", str(repo_root),
        "--env-dir", task_record["env_dir"],
        "--task", task_record["task"],
        "--agent", agent["identifier"],
        "--agent-args", json.dumps(agent.get("parameters", {})),
        "--seed", str(config["experiment_policy"].get("seed", 42)),
        "--steps", str(config["experiment_policy"].get("max_steps", 30)),
        "--output-json", str(output_json),
    ]
    started = time.time()
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True)
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    result = json.loads(output_json.read_text(encoding="utf-8")) if output_json.exists() else {}
    result.update(
        {
            "phase": phase,
            "agent_name": agent["name"],
            "adapter_type": "native-gym-agent",
            "env": task_record["env"],
            "env_dir": task_record["env_dir"],
            "task_id": task_record["task"],
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "exit_code": completed.returncode,
            "duration_sec": round(time.time() - started, 3),
        }
    )
    if completed.returncode != 0 and not result.get("error"):
        result["error"] = f"native adapter exited with code {completed.returncode}"
    result["success"] = bool(result.get("verifier_passed"))
    result["stderr_excerpt"] = (completed.stderr or "")[:500]
    return result


def run_external_wrapper(repo_root: Path, run_dir: Path, agent: dict[str, Any], task_record: dict[str, str], phase: str) -> dict[str, Any]:
    task_dir = ensure_dir(run_dir / "task_runs" / phase / f"{agent['name']}__{task_record['env']}__{task_record['task']}")
    output_json = task_dir / "result.json"
    stdout_path = task_dir / "stdout.txt"
    stderr_path = task_dir / "stderr.txt"
    command_template = agent.get("parameters", {}).get("command")
    if not command_template:
        return {
            "phase": phase,
            "agent_name": agent["name"],
            "adapter_type": agent["adapter_type"],
            "env": task_record["env"],
            "env_dir": task_record["env_dir"],
            "task_id": task_record["task"],
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "exit_code": 1,
            "success": False,
            "verifier_passed": False,
            "verifier_score": None,
            "feedback": None,
            "summary_path": None,
            "episode_dir": None,
            "error": f"Missing command template for adapter type {agent['adapter_type']}",
            "stderr_excerpt": "",
        }

    placeholders = _placeholders(repo_root, run_dir, agent, task_record, phase, output_json)
    command = [part.format(**placeholders) for part in command_template]
    started = time.time()
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True)
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    result = json.loads(output_json.read_text(encoding="utf-8")) if output_json.exists() else {}
    result.update(
        {
            "phase": phase,
            "agent_name": agent["name"],
            "adapter_type": agent["adapter_type"],
            "env": task_record["env"],
            "env_dir": task_record["env_dir"],
            "task_id": task_record["task"],
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "exit_code": completed.returncode,
            "duration_sec": round(time.time() - started, 3),
            "stderr_excerpt": (completed.stderr or "")[:500],
        }
    )
    if completed.returncode != 0 and not result.get("error"):
        result["error"] = f"wrapper exited with code {completed.returncode}"
    result["success"] = bool(result.get("verifier_passed") or result.get("success"))
    return result


def classify_failure(result: dict[str, Any]) -> str:
    if result.get("success"):
        return "success"
    haystack = " ".join(
        str(value)
        for value in [result.get("feedback"), result.get("error"), result.get("stderr_excerpt")]
        if value
    ).lower()
    if not result.get("summary_path") and not result.get("verifier"):
        return "verifier-mismatch-or-task-ambiguity"
    if any(token in haystack for token in ["screen", "screenshot", "ocr", "image", "pixel", "visual"]):
        return "perception-observation-failure"
    if any(token in haystack for token in ["tool", "mouse", "keyboard", "click", "type", "action", "navigate"]):
        return "tool-action-selection-failure"
    if any(token in haystack for token in ["remember", "recall", "forgot", "history", "prior"]):
        return "memory-recall-failure"
    if any(token in haystack for token in ["workflow", "credential", "menu", "setting", "course", "environment"]):
        return "missing-environment-knowledge"
    if any(token in haystack for token in ["verifier", "checker", "artifact", "expected", "mismatch"]):
        return "verifier-mismatch-or-task-ambiguity"
    return "decomposition-planning-failure"


def build_proposal(result: dict[str, Any]) -> dict[str, Any]:
    failure_class = result["failure_class"]
    return {
        "agent_name": result["agent_name"],
        "env": result["env"],
        "task_id": result["task_id"],
        "failure_class": failure_class,
        "proposal_type": FAILURE_PROPOSAL_MAP.get(failure_class, "candidate-regression-test-suggestion"),
        "confidence": 0.7 if failure_class != "verifier-mismatch-or-task-ambiguity" else 0.55,
        "rationale": result.get("feedback") or result.get("error") or "Generated from normalized failure evidence.",
        "suggested_follow_up": f"Review the proposed {FAILURE_PROPOSAL_MAP.get(failure_class, 'candidate-regression-test-suggestion')} for {result['agent_name']} on {result['env']}/{result['task_id']}.",
    }


def evaluate(config_path: Path, *, phases: list[str] | None = None, reuse_run_dir: Path | None = None) -> Path:
    repo_root = resolve_repo_root(config_path)
    config = load_config(config_path)
    output_root = ensure_dir(repo_root / config["artifact_paths"]["output_root"])
    ensure_dir(repo_root / config["artifact_paths"]["logs"])
    ensure_dir(repo_root / config["artifact_paths"]["cache"])
    run_dir = reuse_run_dir or create_run_dir(output_root)
    tasks = resolve_tasks(repo_root, config)
    partitions = partition_tasks(tasks, config["experiment_policy"].get("partition", {}))
    selected_phases = phases or ["train"]
    write_json(run_dir / "selection.json", {"tasks": tasks, "partitions": partitions, "selected_phases": selected_phases})

    results: list[dict[str, Any]] = []
    for phase in selected_phases:
        for agent in config["agents_under_test"]:
            for task_record in partitions.get(phase, []):
                if agent["adapter_type"] == "native-gym-agent":
                    result = run_native_agent(repo_root, run_dir, config, agent, task_record, phase)
                else:
                    result = run_external_wrapper(repo_root, run_dir, agent, task_record, phase)
                results.append(result)

    write_json(run_dir / "results.json", results)
    summary = {
        "run_id": run_dir.name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selected_phases": selected_phases,
        "task_count": len(tasks),
        "partition_counts": {name: len(items) for name, items in partitions.items()},
        "agent_names": [agent["name"] for agent in config["agents_under_test"]],
        "success_rate": compute_success_rate(results),
        "success_count": sum(1 for item in results if item.get("success")),
        "failure_count": sum(1 for item in results if not item.get("success")),
    }
    write_json(run_dir / "summary.json", summary)
    return run_dir


def analyze(config_path: Path, *, run_dir: Path | None = None) -> Path:
    repo_root = resolve_repo_root(config_path)
    output_root = repo_root / load_config(config_path)["artifact_paths"]["output_root"]
    run_dir = run_dir or latest_run_dir(output_root)
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    failures = []
    for result in results:
        if result.get("success"):
            continue
        enriched = dict(result)
        enriched["failure_class"] = classify_failure(result)
        failures.append(enriched)
    payload = {
        "run_id": run_dir.name,
        "failure_count": len(failures),
        "failure_class_counts": dict(Counter(item["failure_class"] for item in failures)),
        "failures": failures,
    }
    write_json(run_dir / "failures.json", payload)
    return run_dir


def propose(config_path: Path, *, run_dir: Path | None = None) -> Path:
    repo_root = resolve_repo_root(config_path)
    config = load_config(config_path)
    output_root = repo_root / config["artifact_paths"]["output_root"]
    run_dir = run_dir or latest_run_dir(output_root)
    failures = json.loads((run_dir / "failures.json").read_text(encoding="utf-8"))
    proposals = [build_proposal(item) for item in failures.get("failures", [])]
    write_json(run_dir / "proposals.json", proposals)
    lines = [
        f"# Improvement Proposals for {run_dir.name}",
        "",
        f"Approval mode: {config['improvement_policy'].get('approval_mode', 'human-gated')}",
        "",
    ]
    if not proposals:
        lines.append("No proposals generated.")
    for proposal in proposals:
        lines.extend(
            [
                f"## {proposal['agent_name']} :: {proposal['env']} / {proposal['task_id']}",
                f"- Failure class: `{proposal['failure_class']}`",
                f"- Proposal type: `{proposal['proposal_type']}`",
                f"- Confidence: `{proposal['confidence']}`",
                f"- Rationale: {proposal['rationale']}",
                f"- Suggested follow-up: {proposal['suggested_follow_up']}",
                "",
            ]
        )
    (run_dir / "proposals.md").write_text("\n".join(lines), encoding="utf-8")
    return run_dir


def validate(config_path: Path, *, run_dir: Path | None = None) -> Path:
    repo_root = resolve_repo_root(config_path)
    config = load_config(config_path)
    output_root = repo_root / config["artifact_paths"]["output_root"]
    run_dir = run_dir or latest_run_dir(output_root)
    evaluate(config_path, phases=["validation", "holdout"], reuse_run_dir=run_dir)
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    validation_results = [item for item in results if item.get("phase") == "validation"]
    holdout_results = [item for item in results if item.get("phase") == "holdout"]
    validation_rate = compute_success_rate(validation_results)
    holdout_rate = compute_success_rate(holdout_results)
    requirements = config["improvement_policy"]["regression_requirements"]
    holdout_blocked = bool(requirements.get("block_on_holdout_regression", True)) and any(not item.get("success") for item in holdout_results)
    recommended = validation_rate >= float(requirements.get("minimum_validation_success_rate", 0.0)) and not holdout_blocked
    payload = {
        "run_id": run_dir.name,
        "validation_success_rate": validation_rate,
        "holdout_success_rate": holdout_rate,
        "holdout_blocked": holdout_blocked,
        "recommended": recommended,
        "validation_results": validation_results,
        "holdout_results": holdout_results,
    }
    write_json(run_dir / "regression.json", payload)
    return run_dir


def report(config_path: Path, *, run_dir: Path | None = None) -> Path:
    repo_root = resolve_repo_root(config_path)
    output_root = repo_root / load_config(config_path)["artifact_paths"]["output_root"]
    run_dir = run_dir or latest_run_dir(output_root)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    failures = json.loads((run_dir / "failures.json").read_text(encoding="utf-8")) if (run_dir / "failures.json").exists() else {"failure_count": 0, "failure_class_counts": {}}
    proposals = json.loads((run_dir / "proposals.json").read_text(encoding="utf-8")) if (run_dir / "proposals.json").exists() else []
    regression = json.loads((run_dir / "regression.json").read_text(encoding="utf-8")) if (run_dir / "regression.json").exists() else {"recommended": False, "validation_success_rate": 0.0, "holdout_success_rate": 0.0, "holdout_blocked": False}

    lines = [
        f"# Agent Improvement Review Packet: {run_dir.name}",
        "",
        "## What Was Tested",
        f"- Agents: {', '.join(summary.get('agent_names', []))}",
        f"- Selected phases: {', '.join(summary.get('selected_phases', []))}",
        f"- Task count: {summary.get('task_count', 0)}",
        "",
        "## Baseline Metrics",
        f"- Success rate: {summary.get('success_rate', 0.0)}",
        f"- Success count: {summary.get('success_count', 0)}",
        f"- Failure count: {summary.get('failure_count', 0)}",
        "",
        "## Failure Clusters",
    ]
    if failures.get("failure_class_counts"):
        for failure_class, count in sorted(failures["failure_class_counts"].items()):
            lines.append(f"- {failure_class}: {count}")
    else:
        lines.append("- No failures detected.")
    lines.extend(["", "## Proposed Changes"])
    if proposals:
        for proposal in proposals:
            lines.append(f"- {proposal['proposal_type']} for {proposal['agent_name']} on {proposal['env']}/{proposal['task_id']} ({proposal['failure_class']})")
    else:
        lines.append("- No proposals generated.")
    lines.extend(
        [
            "",
            "## Regression Verdict",
            f"- Validation success rate: {regression.get('validation_success_rate', 0.0)}",
            f"- Holdout success rate: {regression.get('holdout_success_rate', 0.0)}",
            f"- Holdout blocked: {regression.get('holdout_blocked', False)}",
            f"- Recommended: {regression.get('recommended', False)}",
            "",
            "## Unresolved Risks",
        ]
    )
    if failures.get("failure_count", 0) == 0:
        lines.append("- None identified from this run.")
    else:
        lines.append("- Failures remain proposal-only until a human accepts a change path.")
        if regression.get("holdout_blocked"):
            lines.append("- Holdout regressions currently block recommendation status.")
        lines.append("- Benchmark-side mismatches should be reviewed before patching the agent.")
    (run_dir / "review_packet.md").write_text("\n".join(lines), encoding="utf-8")
    return run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repo-local agent self-improvement harness.")
    parser.add_argument("verb", choices=["evaluate", "analyze", "propose", "validate", "report", "all"])
    parser.add_argument("--config", default="agent-improvement.config.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        return 1
    if args.verb == "evaluate":
        run_dir = evaluate(config_path)
    elif args.verb == "analyze":
        run_dir = analyze(config_path)
    elif args.verb == "propose":
        run_dir = propose(config_path)
    elif args.verb == "validate":
        run_dir = validate(config_path)
    elif args.verb == "report":
        run_dir = report(config_path)
    else:
        run_dir = evaluate(config_path)
        analyze(config_path, run_dir=run_dir)
        propose(config_path, run_dir=run_dir)
        validate(config_path, run_dir=run_dir)
        report(config_path, run_dir=run_dir)
    print(f"Harness phase '{args.verb}' completed in {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
