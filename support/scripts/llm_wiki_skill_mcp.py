#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SERVER_NAME = "llm-wiki-skills"
SERVER_VERSION = "0.3.0"
DEFAULT_KINDS = {"ui", "http", "workflow", "prompt"}
CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}
ROUTE_DECISIONS = {
    "complete",
    "retry_same_worker",
    "reroute_to_sibling",
    "escalate_to_parent",
    "stop_insufficient_evidence",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or f"skill-{uuid.uuid4().hex[:8]}"


def ensure_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                decoded = json.loads(stripped)
                if isinstance(decoded, list):
                    return [str(item).strip() for item in decoded if str(item).strip()]
            except json.JSONDecodeError:
                pass
        if "\n" in stripped:
            return [line.strip() for line in stripped.splitlines() if line.strip()]
        return [stripped]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def ensure_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def unique_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        stripped = item.strip()
        if not stripped:
            continue
        key = stripped.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(stripped)
    return result


def tokenize(*parts: str) -> set[str]:
    text = " ".join(part for part in parts if part)
    return {token.lower() for token in re.findall(r"[A-Za-z0-9]{3,}", text)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def safe_stem(value: str) -> str:
    base = slugify(value) or uuid.uuid4().hex[:8]
    return base[:80]


def file_stamp(timestamp: str) -> str:
    return timestamp.replace(":", "").replace("-", "").replace("T", "-").replace("Z", "")


def yaml_quote(value: str) -> str:
    return json.dumps(ensure_text(value))


def merge_text(existing: str, incoming: str) -> str:
    existing_text = ensure_text(existing)
    incoming_text = ensure_text(incoming)
    if not existing_text:
        return incoming_text
    if not incoming_text:
        return existing_text
    if incoming_text.lower() in existing_text.lower():
        return existing_text

    merged = [line.rstrip() for line in existing_text.splitlines() if line.strip()]
    if not merged:
        merged = [existing_text]
    seen = {line.strip().lower() for line in merged if line.strip()}
    for line in [line.rstrip() for line in incoming_text.splitlines() if line.strip()]:
        key = line.strip().lower()
        if key not in seen:
            merged.append(line)
            seen.add(key)
    return "\n".join(merged)


def detect_pii(*parts: str) -> list[str]:
    text = "\n".join(part for part in parts if part)
    checks = {
        "email": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "api_key": r"\b(?:sk|rk|pk)_[A-Za-z0-9_-]{12,}\b",
        "bearer_token": r"Bearer\s+[A-Za-z0-9._-]{12,}",
        "cookie_like": r"\b(?:session|token|cookie|secret|password)[=:][^\s]{6,}",
        "long_hex": r"\b[a-f0-9]{32,}\b",
        "phone_like": r"\+?\d[\d\s().-]{8,}\d",
    }
    hits: list[str] = []
    for label, pattern in checks.items():
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(label)
    return hits


class SkillStore:
    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        config = self._load_config()
        skill_cfg = config.get("skills", {})
        pipeline_cfg = skill_cfg.get("pipeline", {})

        self.registry_path = self.workspace / skill_cfg.get("registry_path", ".llm-wiki/skills-registry.json")
        self.index_path = self.workspace / skill_cfg.get("index_path", "wiki/skills/index.md")
        self.log_path = self.workspace / skill_cfg.get("log_path", "wiki/log.md")
        self.active_dir = self.workspace / skill_cfg.get("active_dir", "wiki/skills/active")
        self.feedback_dir = self.workspace / skill_cfg.get("feedback_dir", "wiki/skills/feedback")
        self.retired_dir = self.workspace / skill_cfg.get("retired_dir", "wiki/skills/retired")
        self.retire_below_score = int(skill_cfg.get("retire_below_score", -3))

        self.pipeline_dir = self.workspace / pipeline_cfg.get("pipeline_dir", ".llm-wiki/skill-pipeline")
        self.brief_dir = self.workspace / pipeline_cfg.get("brief_dir", ".llm-wiki/skill-pipeline/briefs")
        self.delta_dir = self.workspace / pipeline_cfg.get("delta_dir", ".llm-wiki/skill-pipeline/deltas")
        self.validation_dir = self.workspace / pipeline_cfg.get("validation_dir", ".llm-wiki/skill-pipeline/validations")
        self.packet_dir = self.workspace / pipeline_cfg.get("packet_dir", ".llm-wiki/skill-pipeline/packets")
        self.min_validation_score = int(pipeline_cfg.get("min_validation_score", 7))
        self.dedupe_similarity_threshold = float(pipeline_cfg.get("dedupe_similarity_threshold", 0.72))
        self.auto_merge_duplicates = bool(pipeline_cfg.get("auto_merge_duplicates", True))
        self.long_task_brief_min_chars = int(pipeline_cfg.get("long_task_brief_min_chars", 280))
        self.max_hops_default = int(pipeline_cfg.get("max_hops_default", 2))
        self.max_retries_default = int(pipeline_cfg.get("max_retries_default", 1))
        self.enforce_summary_only = bool(pipeline_cfg.get("enforce_summary_only", True))

        for path in [
            self.registry_path.parent,
            self.index_path.parent,
            self.log_path.parent,
            self.active_dir,
            self.feedback_dir,
            self.retired_dir,
            self.pipeline_dir,
            self.brief_dir,
            self.delta_dir,
            self.validation_dir,
            self.packet_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

        self.data = self._load_registry()

    def _load_config(self) -> dict[str, Any]:
        config_path = self.workspace / ".llm-wiki" / "config.json"
        if config_path.exists():
            return json.loads(config_path.read_text(encoding="utf-8"))
        return {}

    def _load_registry(self) -> dict[str, Any]:
        if self.registry_path.exists():
            loaded = json.loads(self.registry_path.read_text(encoding="utf-8"))
        else:
            loaded = {}
        loaded.setdefault("skills", {})
        loaded.setdefault("feedback", [])
        loaded.setdefault("briefs", [])
        loaded.setdefault("deltas", [])
        loaded.setdefault("validations", [])
        loaded.setdefault("packets", [])
        loaded.setdefault("events", [])
        return loaded

    def _save(self) -> None:
        self.registry_path.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.workspace).as_posix()

    def _append_log(self, entry_type: str, subject: str, lines: list[str]) -> None:
        if not self.log_path.exists():
            self.log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
        entry_lines = [f"## {utc_now()} - {entry_type}: {subject}", ""]
        entry_lines.extend(f"- {line}" for line in lines if line)
        entry_lines.append("")
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(entry_lines))

    def _record_registry_event(self, kind: str, payload: dict[str, Any]) -> None:
        self.data["events"].append({"id": f"event-{uuid.uuid4().hex[:10]}", "kind": kind, "created_at": utc_now(), "payload": payload})

    def get_skill(self, skill_id: str) -> dict[str, Any] | None:
        return self.data["skills"].get(skill_id)

    def list_feedback(self, skill_id: str) -> list[dict[str, Any]]:
        return [row for row in self.data["feedback"] if row["skill_id"] == skill_id]

    def list_briefs(self, skill_id: str) -> list[dict[str, Any]]:
        return [row for row in self.data["briefs"] if row.get("skill_id") == skill_id or skill_id in row.get("related_skill_ids", [])]

    def list_packets(self, skill_id: str) -> list[dict[str, Any]]:
        return [row for row in self.data["packets"] if row.get("skill_id") == skill_id or skill_id in row.get("related_skill_ids", [])]

    def _build_similarity_matches(self, candidate: dict[str, Any], exclude_id: str | None = None) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        cand_meta = tokenize(candidate.get("title", ""), candidate.get("problem", ""), candidate.get("trigger", ""))
        cand_fast = tokenize(candidate.get("fast_path", ""), candidate.get("failure_modes", ""), candidate.get("evidence", ""))
        cand_apply = {item.lower() for item in candidate.get("applies_to", [])}

        for skill in self.data["skills"].values():
            if skill.get("status") != "active":
                continue
            if exclude_id and skill.get("id") == exclude_id:
                continue

            skill_meta = tokenize(skill.get("title", ""), skill.get("problem", ""), skill.get("trigger", ""))
            skill_fast = tokenize(skill.get("fast_path", ""), skill.get("failure_modes", ""), skill.get("evidence", ""))
            skill_apply = {item.lower() for item in skill.get("applies_to", [])}

            apply_overlap = 0.0
            if cand_apply and skill_apply:
                if cand_apply & skill_apply:
                    apply_overlap = 1.0
                else:
                    for left in cand_apply:
                        for right in skill_apply:
                            if left.rstrip("*") and left.rstrip("*") in right:
                                apply_overlap = max(apply_overlap, 0.75)
                            if right.rstrip("*") and right.rstrip("*") in left:
                                apply_overlap = max(apply_overlap, 0.75)

            kind_match = 1.0 if candidate.get("kind", "").lower() == skill.get("kind", "").lower() else 0.0
            similarity = (
                0.35 * jaccard(cand_meta, skill_meta)
                + 0.25 * jaccard(cand_fast, skill_fast)
                + 0.25 * apply_overlap
                + 0.15 * kind_match
            )
            if similarity >= 0.45:
                matches.append(
                    {
                        "skill_id": skill["id"],
                        "title": skill["title"],
                        "similarity": round(similarity, 3),
                        "kind": skill["kind"],
                        "applies_to": skill["applies_to"],
                        "score": skill["score"],
                    }
                )

        matches.sort(key=lambda item: (item["similarity"], item["score"]), reverse=True)
        return matches

    def lookup(
        self,
        url_pattern: str = "",
        task_type: str = "",
        goal: str = "",
        context: str = "",
        limit: int = 5,
    ) -> dict[str, Any]:
        terms = [term.lower() for term in re.findall(r"[A-Za-z0-9]{3,}", f"{goal} {context}")]
        matches: list[tuple[int, dict[str, Any]]] = []
        for skill in self.data["skills"].values():
            if skill["status"] != "active":
                continue
            score = max(int(skill.get("score", 0)), 0)
            if task_type and task_type.lower() == skill["kind"].lower():
                score += 4
            haystack = " ".join(
                [
                    skill["title"],
                    skill["problem"],
                    skill["trigger"],
                    skill["preconditions"],
                    skill["fast_path"],
                    skill["failure_modes"],
                    ensure_text(skill.get("validation_status")),
                ]
            ).lower()
            for term in terms:
                if term in haystack:
                    score += 1
            if url_pattern:
                for pattern in skill["applies_to"]:
                    if fnmatch.fnmatch(url_pattern, pattern):
                        score += 10
                    elif pattern.rstrip("*") and pattern.rstrip("*") in url_pattern:
                        score += 6
            if score > 0:
                item = dict(skill)
                item["match_score"] = score
                matches.append((score, item))
        matches.sort(key=lambda item: (item[0], item[1]["updated_at"]), reverse=True)
        return {"matches": [item for _, item in matches[:limit]], "count": min(limit, len(matches))}

    def _normalize_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = ensure_text(payload.get("title")) or ensure_text(payload.get("goal")) or ensure_text(payload.get("problem"))
        kind = ensure_text(payload.get("kind") or payload.get("task_type") or "workflow").lower()
        applies_to = ensure_list(payload.get("applies_to"))
        if not applies_to and ensure_text(payload.get("url_pattern")):
            applies_to = [ensure_text(payload.get("url_pattern"))]

        observations = unique_list(
            ensure_list(payload.get("observations"))
            + ensure_list(payload.get("trajectory"))
            + ensure_list(payload.get("lessons"))
        )
        risks = unique_list(ensure_list(payload.get("risks")))
        next_actions = unique_list(ensure_list(payload.get("next_actions")))
        files = unique_list(ensure_list(payload.get("files")))
        references = unique_list(ensure_list(payload.get("references")))
        important_context = ensure_text(payload.get("important_context") or payload.get("context"))
        outcome = ensure_text(payload.get("outcome"))
        evidence_text = ensure_text(payload.get("evidence"))
        if outcome:
            evidence_text = merge_text(evidence_text, f"Outcome: {outcome}")
        if files:
            evidence_text = merge_text(evidence_text, "Files involved:\n" + "\n".join(f"- {item}" for item in files))
        if references:
            evidence_text = merge_text(evidence_text, "References:\n" + "\n".join(f"- {item}" for item in references))

        fast_path = ensure_text(payload.get("fast_path"))
        if not fast_path and observations:
            fast_path = "\n".join(f"{idx}. {item}" for idx, item in enumerate(observations[:5], start=1))
        if not fast_path and next_actions:
            fast_path = "\n".join(f"{idx}. {item}" for idx, item in enumerate(next_actions[:5], start=1))

        failure_modes = ensure_text(payload.get("failure_modes"))
        if not failure_modes and risks:
            failure_modes = "\n".join(f"- {item}" for item in risks)

        skip_steps_estimate = payload.get("skip_steps_estimate")
        if skip_steps_estimate in (None, "") or ensure_int(skip_steps_estimate) <= 0:
            derived = 0
            if observations:
                derived = max(2, min(12, len(observations) * 2))
            elif important_context:
                derived = 3
            skip_steps_estimate = derived

        long_task = bool(payload.get("long_task"))
        if not long_task:
            long_task = len(important_context) >= self.long_task_brief_min_chars or len(observations) >= 4

        route_decision = ensure_text(payload.get("route_decision")).lower()
        if not route_decision and not long_task:
            route_decision = "complete"

        return {
            "skill_id": ensure_text(payload.get("skill_id")),
            "title": title,
            "kind": kind,
            "applies_to": applies_to,
            "problem": ensure_text(payload.get("problem") or payload.get("goal") or title),
            "trigger": ensure_text(payload.get("trigger") or payload.get("goal") or title),
            "preconditions": ensure_text(payload.get("preconditions") or important_context),
            "fast_path": fast_path,
            "failure_modes": failure_modes,
            "evidence": evidence_text,
            "http_candidate": bool(payload.get("http_candidate", False)),
            "source_type": ensure_text(payload.get("source_type") or ("trajectory" if observations else "summary")),
            "skip_steps_estimate": int(skip_steps_estimate or 0),
            "confidence": ensure_text(payload.get("confidence") or ("high" if len(observations) >= 4 else "medium")).lower(),
            "last_validated": ensure_text(payload.get("last_validated")),
            "important_context": important_context,
            "observations": observations,
            "risks": risks,
            "next_actions": next_actions,
            "files": files,
            "references": references,
            "outcome": outcome,
            "brief_refs": unique_list(ensure_list(payload.get("brief_refs"))),
            "route_decision": route_decision,
            "route_reason": ensure_text(payload.get("route_reason")),
            "unresolved_questions": unique_list(ensure_list(payload.get("unresolved_questions"))),
            "artifact_refs": unique_list(ensure_list(payload.get("artifact_refs")) + ensure_list(payload.get("brief_refs"))),
            "assigned_target": ensure_text(payload.get("assigned_target")),
            "parent_packet_id": ensure_text(payload.get("parent_packet_id")),
            "hop_count": max(0, ensure_int(payload.get("hop_count"), 0)),
            "retry_count": max(0, ensure_int(payload.get("retry_count"), 0)),
            "long_task": long_task,
        }

    def _build_executive_summary(self, candidate: dict[str, Any], goal: str) -> str:
        return (
            f"{candidate['title']}: {goal or candidate['problem']}. "
            f"Outcome: {candidate['outcome'] or 'pending'}. "
            f"Future agent shortcut: solve in {max(candidate['skip_steps_estimate'], 1)} fewer steps by reusing the fast path."
        ).strip()

    def _build_packet(self, candidate: dict[str, Any], payload: dict[str, Any], created_at: str) -> dict[str, Any]:
        goal = ensure_text(payload.get("goal") or candidate.get("problem"))
        route_decision = ensure_text(candidate.get("route_decision")).lower()
        if not route_decision and not candidate.get("long_task"):
            route_decision = "complete"

        return {
            "id": ensure_text(payload.get("packet_id")) or f"packet-{slugify(candidate['title'])}-{uuid.uuid4().hex[:8]}",
            "skill_id": ensure_text(candidate.get("skill_id")),
            "title": candidate["title"],
            "task_type": candidate["kind"],
            "goal": goal,
            "executive_summary": self._build_executive_summary(candidate, goal),
            "important_context": candidate["important_context"],
            "outcome": candidate["outcome"],
            "observations": candidate["observations"],
            "risks": candidate["risks"],
            "next_actions": candidate["next_actions"],
            "confidence": candidate["confidence"],
            "route_decision": route_decision,
            "route_reason": ensure_text(candidate.get("route_reason")),
            "unresolved_questions": unique_list(ensure_list(candidate.get("unresolved_questions"))),
            "artifact_refs": unique_list(ensure_list(candidate.get("artifact_refs"))),
            "assigned_target": ensure_text(candidate.get("assigned_target")),
            "parent_packet_id": ensure_text(candidate.get("parent_packet_id")),
            "hop_count": max(0, ensure_int(candidate.get("hop_count"), 0)),
            "retry_count": max(0, ensure_int(candidate.get("retry_count"), 0)),
            "long_task": bool(candidate.get("long_task")),
            "related_skill_ids": [candidate["skill_id"]] if candidate.get("skill_id") else [],
            "created_at": created_at,
            "updated_at": created_at,
        }

    def _write_packet(self, packet: dict[str, Any]) -> str:
        path = self.packet_dir / f"{file_stamp(packet['created_at'])}--{safe_stem(packet['title'])}.json"
        rel = self._relative(path)
        packet["path"] = rel
        path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
        existing_idx = next((idx for idx, row in enumerate(self.data["packets"]) if row.get("id") == packet["id"]), None)
        if existing_idx is None:
            self.data["packets"].append(dict(packet))
            action = "created"
        else:
            self.data["packets"][existing_idx] = dict(packet)
            action = "updated"
        self._record_registry_event("skill_packet", {"packet_id": packet["id"], "path": rel, "action": action, "route_decision": packet.get("route_decision", "")})
        self._save()
        return rel

    def _refresh_packet(
        self,
        packet: dict[str, Any],
        *,
        artifact_refs: list[str] | None = None,
        related_skill_id: str = "",
        validation_status: str = "",
        pipeline_status: str = "",
    ) -> tuple[dict[str, Any], str]:
        updated = dict(packet)
        if artifact_refs:
            updated["artifact_refs"] = unique_list(ensure_list(updated.get("artifact_refs")) + artifact_refs)
        if related_skill_id:
            updated["skill_id"] = related_skill_id
            updated["related_skill_ids"] = unique_list(ensure_list(updated.get("related_skill_ids")) + [related_skill_id])
        if validation_status:
            updated["validation_status"] = validation_status
        if pipeline_status:
            updated["pipeline_status"] = pipeline_status
        updated["updated_at"] = utc_now()
        path = self._write_packet(updated)
        return updated, path

    def _write_brief(self, brief: dict[str, Any]) -> str:
        path = self.brief_dir / f"{file_stamp(brief['created_at'])}--{safe_stem(brief['title'])}.md"
        observations = "\n".join(f"- {item}" for item in brief["observations"]) or "- No detailed observations captured yet."
        risks = "\n".join(f"- {item}" for item in brief["risks"]) or "- No explicit risks captured."
        next_actions = "\n".join(f"- {item}" for item in brief["next_actions"]) or "- No next actions recorded."
        files = "\n".join(f"- {item}" for item in brief["files"]) or "- No files recorded."
        references = "\n".join(f"- {item}" for item in brief["references"]) or "- No references recorded."
        body = f"""---
id: {brief["id"]}
title: {yaml_quote(brief["title"])}
task_type: {brief["task_type"]}
created_at: {brief["created_at"]}
long_task: {"true" if brief["long_task"] else "false"}
related_skill_ids: {json.dumps(brief["related_skill_ids"])}
---

## Goal

{brief["goal"] or "Goal not captured."}

## Outcome

{brief["outcome"] or "Outcome not captured yet."}

## Important Context

{brief["important_context"] or "No important context supplied."}

## Executive Summary

{brief["executive_summary"]}

## Key Observations

{observations}

## Risks

{risks}

## Next Actions

{next_actions}

## Files

{files}

## References

{references}
"""
        path.write_text(body, encoding="utf-8")
        rel = self._relative(path)
        brief["path"] = rel
        self.data["briefs"].append(brief)
        self._record_registry_event("skill_brief", {"brief_id": brief["id"], "path": rel})
        self._save()
        return rel

    def reflect(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidate = self._normalize_candidate(payload)
        if not candidate["title"]:
            return {"status": "blocked", "reason": "missing_title"}
        brief_pii_hits = detect_pii(
            ensure_text(payload.get("goal")),
            candidate["important_context"],
            ensure_text(payload.get("outcome")),
            ensure_text(payload.get("evidence")),
            "\n".join(candidate["observations"]),
        )
        if brief_pii_hits:
            return {"status": "blocked", "reason": "pii_detected", "matches": brief_pii_hits}
        now = utc_now()
        goal = ensure_text(payload.get("goal") or candidate["problem"])
        brief = {
            "id": f"brief-{slugify(candidate['title'])}-{uuid.uuid4().hex[:8]}",
            "title": candidate["title"],
            "created_at": now,
            "task_type": candidate["kind"],
            "goal": goal,
            "outcome": candidate["outcome"],
            "important_context": candidate["important_context"],
            "executive_summary": self._build_executive_summary(candidate, goal),
            "observations": candidate["observations"],
            "risks": candidate["risks"],
            "next_actions": candidate["next_actions"],
            "files": candidate["files"],
            "references": candidate["references"],
            "long_task": candidate["long_task"],
            "related_skill_ids": [candidate["skill_id"]] if candidate["skill_id"] else [],
        }
        persist_brief = payload.get("persist_brief", True)
        if persist_brief:
            brief_path = self._write_brief(brief)
            candidate["brief_refs"] = unique_list(candidate["brief_refs"] + [brief_path])
            candidate["artifact_refs"] = unique_list(candidate["artifact_refs"] + [brief_path])
        else:
            brief_path = ""
        packet = self._build_packet(candidate, payload, now)
        persist_packet = payload.get("persist_packet", True)
        if persist_packet:
            packet_path = self._write_packet(packet)
        else:
            packet_path = ""
        return {
            "status": "ok",
            "brief": brief,
            "brief_path": brief_path,
            "candidate": candidate,
            "packet": packet,
            "packet_path": packet_path,
        }

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing: dict[str, Any] | None = None
        skill_id = ensure_text(payload.get("skill_id"))
        if skill_id:
            existing = self.get_skill(skill_id)
            if not existing:
                return {"status": "missing", "skill_id": skill_id}
            merged_payload = dict(existing)
            merged_payload.update({key: value for key, value in payload.items() if value not in (None, "", [], {})})
            candidate = self._normalize_candidate(merged_payload)
            candidate["skill_id"] = skill_id
        else:
            candidate = self._normalize_candidate(payload)
        packet = payload.get("packet") if isinstance(payload.get("packet"), dict) else self._build_packet(candidate, payload, utc_now())

        blockers: list[str] = []
        warnings: list[str] = []
        checks: list[dict[str, str]] = []
        score = 0

        def add_check(name: str, passed: bool, detail: str, *, weight: int = 1, blocker: bool = False, warning: bool = False) -> None:
            nonlocal score
            status = "pass" if passed else "fail" if blocker else "warn" if warning else "fail"
            checks.append({"name": name, "status": status, "detail": detail})
            if passed:
                score += weight
            elif blocker:
                blockers.append(detail)
            elif warning:
                warnings.append(detail)

        pii_hits = detect_pii(
            candidate["title"],
            candidate["problem"],
            candidate["trigger"],
            candidate["preconditions"],
            candidate["fast_path"],
            candidate["failure_modes"],
            candidate["evidence"],
            candidate["important_context"],
        )
        add_check("privacy", not pii_hits, "No obvious PII detected." if not pii_hits else f"Potential PII detected: {', '.join(pii_hits)}", weight=2, blocker=bool(pii_hits))
        add_check("title", len(candidate["title"].split()) >= 2, "Skill title is specific enough." if len(candidate["title"].split()) >= 2 else "Skill title is too terse.", warning=True)
        add_check("kind", candidate["kind"] in DEFAULT_KINDS, f"Kind `{candidate['kind']}` matches the recommended taxonomy." if candidate["kind"] in DEFAULT_KINDS else f"Kind `{candidate['kind']}` is allowed but outside the recommended set {sorted(DEFAULT_KINDS)}.", warning=True)
        add_check("applies_to", bool(candidate["applies_to"]), "Applies-to patterns supplied." if candidate["applies_to"] else "At least one applies-to pattern is required.", weight=1, blocker=not candidate["applies_to"])
        add_check("trigger", len(candidate["trigger"]) >= 18, "Trigger is concrete." if len(candidate["trigger"]) >= 18 else "Trigger needs to be more explicit.", weight=1, blocker=len(candidate["trigger"]) < 18)
        add_check("problem", len(candidate["problem"]) >= 24, "Problem statement is grounded." if len(candidate["problem"]) >= 24 else "Problem statement is too thin.", weight=1, warning=True)
        add_check("preconditions", len(candidate["preconditions"]) >= 16, "Preconditions captured." if len(candidate["preconditions"]) >= 16 else "Preconditions are missing or too short.", weight=1, warning=True)
        add_check("fast_path", len(candidate["fast_path"]) >= 24, "Fast path is present." if len(candidate["fast_path"]) >= 24 else "Fast path is required and should be reusable.", weight=2, blocker=len(candidate["fast_path"]) < 24)
        add_check("failure_modes", len(candidate["failure_modes"]) >= 16, "Failure modes captured." if len(candidate["failure_modes"]) >= 16 else "Failure modes need more detail.", weight=1, warning=True)
        add_check("evidence", len(candidate["evidence"]) >= 40, "Evidence is substantive." if len(candidate["evidence"]) >= 40 else "Evidence is too short to validate the skill.", weight=2, blocker=len(candidate["evidence"]) < 40)
        add_check("skip_steps", candidate["skip_steps_estimate"] > 0, "Exploration cost savings estimated." if candidate["skip_steps_estimate"] > 0 else "skip_steps_estimate should be positive.", weight=1, warning=True)
        add_check(
            "briefing",
            (not candidate["long_task"]) or bool(candidate["brief_refs"]) or len(candidate["important_context"]) >= self.long_task_brief_min_chars,
            "Long-task context was captured with a reducer packet and supporting brief." if (not candidate["long_task"]) or bool(candidate["brief_refs"]) or len(candidate["important_context"]) >= self.long_task_brief_min_chars else "Long tasks should capture a stronger important-context reducer packet.",
            weight=1,
            warning=candidate["long_task"],
        )
        add_check(
            "route_decision_present",
            (not candidate["long_task"]) or bool(packet.get("route_decision")),
            "Long-task context includes an explicit route decision." if (not candidate["long_task"]) or bool(packet.get("route_decision")) else "Long tasks must set an explicit route_decision.",
            weight=1,
            blocker=bool(candidate["long_task"]) and not bool(packet.get("route_decision")),
        )
        add_check(
            "route_decision_valid",
            (not packet.get("route_decision")) or packet.get("route_decision") in ROUTE_DECISIONS,
            "Route decision omitted; non-long-task payloads default to `complete`." if not packet.get("route_decision") else f"Route decision `{packet.get('route_decision', '')}` is valid." if packet.get("route_decision") in ROUTE_DECISIONS else f"Route decision must be one of {sorted(ROUTE_DECISIONS)}.",
            weight=1,
            blocker=bool(packet.get("route_decision")) and packet.get("route_decision") not in ROUTE_DECISIONS,
        )
        add_check(
            "hop_budget",
            ensure_int(packet.get("hop_count"), 0) <= self.max_hops_default,
            f"hop_count is within the configured limit ({self.max_hops_default})." if ensure_int(packet.get("hop_count"), 0) <= self.max_hops_default else f"hop_count exceeds max_hops_default ({self.max_hops_default}).",
            weight=1,
            blocker=ensure_int(packet.get("hop_count"), 0) > self.max_hops_default,
        )
        add_check(
            "retry_budget",
            ensure_int(packet.get("retry_count"), 0) <= self.max_retries_default,
            f"retry_count is within the configured limit ({self.max_retries_default})." if ensure_int(packet.get("retry_count"), 0) <= self.max_retries_default else f"retry_count exceeds max_retries_default ({self.max_retries_default}).",
            weight=1,
            blocker=ensure_int(packet.get("retry_count"), 0) > self.max_retries_default,
        )
        packet_route = ensure_text(packet.get("route_decision")).lower()
        if packet_route == "complete":
            add_check(
                "route_complete",
                len(candidate["outcome"]) >= 16 or len(candidate["fast_path"]) >= 24,
                "Complete packets include a substantive outcome or reusable fast path." if len(candidate["outcome"]) >= 16 or len(candidate["fast_path"]) >= 24 else "Complete route requires a substantive outcome or reusable fast_path.",
                weight=1,
                blocker=True,
            )
        elif packet_route == "retry_same_worker":
            add_check(
                "route_retry",
                bool(packet.get("route_reason")) and bool(packet.get("unresolved_questions")),
                "Retry packet includes the reason and unresolved questions." if bool(packet.get("route_reason")) and bool(packet.get("unresolved_questions")) else "retry_same_worker requires route_reason and at least one unresolved question.",
                weight=1,
                blocker=True,
            )
        elif packet_route == "reroute_to_sibling":
            add_check(
                "route_reroute",
                bool(packet.get("route_reason")) and bool(packet.get("unresolved_questions")) and bool(packet.get("assigned_target")),
                "Sibling reroute packet includes the reason, target, and unresolved questions." if bool(packet.get("route_reason")) and bool(packet.get("unresolved_questions")) and bool(packet.get("assigned_target")) else "reroute_to_sibling requires assigned_target, route_reason, and at least one unresolved question.",
                weight=1,
                blocker=True,
            )
        elif packet_route == "escalate_to_parent":
            add_check(
                "route_escalate",
                bool(packet.get("route_reason")) and bool(packet.get("artifact_refs")),
                "Escalation packet includes the reason and artifact refs." if bool(packet.get("route_reason")) and bool(packet.get("artifact_refs")) else "escalate_to_parent requires route_reason and at least one artifact_ref.",
                weight=1,
                blocker=True,
            )
        elif packet_route == "stop_insufficient_evidence":
            add_check(
                "route_stop",
                bool(packet.get("route_reason")),
                "Stop packet includes the stopping reason." if bool(packet.get("route_reason")) else "stop_insufficient_evidence requires route_reason.",
                weight=1,
                blocker=True,
            )
        add_check(
            "summary_only",
            (not self.enforce_summary_only) or ("evidence" not in packet and "fast_path" not in packet and "failure_modes" not in packet),
            "Packet stays summary-only and references artifacts for raw detail." if (not self.enforce_summary_only) or ("evidence" not in packet and "fast_path" not in packet and "failure_modes" not in packet) else "Packets must remain summary-only when enforce_summary_only is enabled.",
            weight=1,
            blocker=self.enforce_summary_only and ("evidence" in packet or "fast_path" in packet or "failure_modes" in packet),
        )

        duplicate_matches = self._build_similarity_matches(candidate, exclude_id=skill_id or None)
        merge_target = ""
        if duplicate_matches and duplicate_matches[0]["similarity"] >= self.dedupe_similarity_threshold:
            merge_target = duplicate_matches[0]["skill_id"]
            add_check(
                "dedupe",
                False,
                f"Candidate overlaps with `{merge_target}` at similarity {duplicate_matches[0]['similarity']:.3f}; merge is recommended.",
                warning=True,
            )
        else:
            add_check("dedupe", True, "No strong duplicate detected.", weight=1)

        status = "validated"
        if blockers:
            status = "blocked"
        elif merge_target:
            status = "merge_recommended"
        elif score < self.min_validation_score:
            status = "needs_revision"

        report = {
            "status": status,
            "score": score,
            "min_validation_score": self.min_validation_score,
            "blockers": blockers,
            "warnings": warnings,
            "checks": checks,
            "candidate": candidate,
            "packet": packet,
            "packet_path": ensure_text(payload.get("packet_path") or packet.get("path")),
            "duplicate_matches": duplicate_matches[:5],
            "merge_target": merge_target,
            "validated_at": utc_now(),
        }
        if payload.get("persist_report", True):
            report["validation_path"] = self._write_validation_report(report)
        return report

    def _write_validation_report(self, report: dict[str, Any]) -> str:
        title = report["candidate"]["title"] or report["candidate"].get("skill_id") or "skill"
        path = self.validation_dir / f"{file_stamp(report['validated_at'])}--{safe_stem(title)}.json"
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        rel = self._relative(path)
        self.data["validations"].append({"id": f"validation-{uuid.uuid4().hex[:10]}", "created_at": report["validated_at"], "status": report["status"], "skill_id": report["candidate"].get("skill_id", ""), "path": rel})
        self._record_registry_event("skill_validation", {"path": rel, "status": report["status"], "title": title})
        self._save()
        return rel

    def _write_delta(self, payload: dict[str, Any]) -> str:
        created_at = payload.get("created_at") or utc_now()
        title = payload.get("candidate", {}).get("title") or payload.get("title") or "skill"
        path = self.delta_dir / f"{file_stamp(created_at)}--{safe_stem(title)}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        rel = self._relative(path)
        self.data["deltas"].append({"id": f"delta-{uuid.uuid4().hex[:10]}", "created_at": created_at, "path": rel, "title": title})
        self._record_registry_event("skill_delta", {"path": rel, "title": title})
        self._save()
        return rel

    def _max_confidence(self, left: str, right: str) -> str:
        left_rank = CONFIDENCE_ORDER.get(left.lower(), 0)
        right_rank = CONFIDENCE_ORDER.get(right.lower(), 0)
        return left if left_rank >= right_rank else right

    def _merge_skill(self, target_skill_id: str, candidate: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        skill = dict(self.get_skill(target_skill_id) or {})
        if not skill:
            return {"status": "missing", "skill_id": target_skill_id}

        merged = dict(skill)
        merged["applies_to"] = unique_list(skill.get("applies_to", []) + candidate.get("applies_to", []))
        merged["problem"] = merge_text(skill.get("problem", ""), candidate.get("problem", ""))
        merged["trigger"] = merge_text(skill.get("trigger", ""), candidate.get("trigger", ""))
        merged["preconditions"] = merge_text(skill.get("preconditions", ""), candidate.get("preconditions", ""))
        merged["fast_path"] = merge_text(skill.get("fast_path", ""), candidate.get("fast_path", ""))
        merged["failure_modes"] = merge_text(skill.get("failure_modes", ""), candidate.get("failure_modes", ""))
        merged["evidence"] = merge_text(skill.get("evidence", ""), candidate.get("evidence", ""))
        merged["skip_steps_estimate"] = max(int(skill.get("skip_steps_estimate", 0)), int(candidate.get("skip_steps_estimate", 0)))
        merged["confidence"] = self._max_confidence(skill.get("confidence", "medium"), candidate.get("confidence", "medium"))
        merged["http_candidate"] = bool(skill.get("http_candidate", False) or candidate.get("http_candidate", False))
        merged["source_type"] = skill.get("source_type", candidate.get("source_type", "trajectory"))
        merged["last_validated"] = utc_day()
        merged["updated_at"] = utc_now()
        merged["validation_status"] = "validated"
        merged["validation_score"] = max(int(skill.get("validation_score", 0)), int(validation.get("score", 0)))
        merged["validation_notes"] = unique_list(ensure_list(skill.get("validation_notes")) + validation.get("warnings", []))
        merged["brief_refs"] = unique_list(ensure_list(skill.get("brief_refs")) + candidate.get("brief_refs", []))
        merge_history = ensure_list(skill.get("merge_history"))
        merge_history.append(f"{utc_now()}: merged pipeline delta from {candidate['title']}")
        merged["merge_history"] = unique_list(merge_history)

        self.data["skills"][target_skill_id] = merged
        self._save()
        self._write_skill(merged)
        self._sync_index()
        self._append_log(
            "skill",
            f"merged `{candidate['title']}` into `{target_skill_id}`",
            [
                f"validation: {validation['status']} ({validation['score']})",
                f"brief refs: {', '.join(candidate.get('brief_refs', [])) or 'none'}",
            ],
        )
        return {"status": "merged", "skill": merged, "target_skill_id": target_skill_id}

    def propose(self, payload: dict[str, Any]) -> dict[str, Any]:
        validation = self.validate({**payload, "persist_report": payload.get("persist_report", True)})
        if validation["status"] == "blocked":
            return {"status": "blocked", "validation": validation}
        if validation["status"] == "merge_recommended" and not payload.get("allow_duplicate"):
            return {"status": "needs_review", "reason": "duplicate_skill_detected", "validation": validation}

        candidate = validation["candidate"]
        now = utc_now()
        skill_id = candidate["skill_id"] or slugify(f"skill-{candidate['title']}")
        existing = self.get_skill(skill_id) or {}
        skill = {
            "id": skill_id,
            "title": candidate["title"],
            "status": "active",
            "kind": candidate["kind"],
            "applies_to": candidate["applies_to"],
            "score": int(existing.get("score", 0)),
            "helpful_count": int(existing.get("helpful_count", 0)),
            "harmful_count": int(existing.get("harmful_count", 0)),
            "skip_steps_estimate": int(candidate.get("skip_steps_estimate", existing.get("skip_steps_estimate", 0))),
            "confidence": candidate.get("confidence", existing.get("confidence", "medium")),
            "pii_review": "passed",
            "validation_status": "validated" if validation["status"] == "validated" else validation["status"],
            "validation_score": int(validation["score"]),
            "validation_notes": validation["warnings"],
            "http_candidate": bool(candidate.get("http_candidate", existing.get("http_candidate", False))),
            "source_type": candidate.get("source_type", existing.get("source_type", "trajectory")),
            "last_validated": candidate.get("last_validated") or utc_day(),
            "problem": candidate.get("problem", ""),
            "trigger": candidate.get("trigger", ""),
            "preconditions": candidate.get("preconditions", ""),
            "fast_path": candidate.get("fast_path", ""),
            "failure_modes": candidate.get("failure_modes", ""),
            "evidence": candidate.get("evidence", ""),
            "brief_refs": unique_list(ensure_list(existing.get("brief_refs")) + candidate.get("brief_refs", [])),
            "merge_history": ensure_list(existing.get("merge_history")),
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }
        self.data["skills"][skill_id] = skill
        self._save()
        self._write_skill(skill)
        self._sync_index()
        self._append_log(
            "skill",
            f"saved `{skill_id}`",
            [
                f"validation: {skill['validation_status']} ({skill['validation_score']})",
                f"kind: {skill['kind']}",
                f"brief refs: {', '.join(skill['brief_refs']) or 'none'}",
            ],
        )
        return {"status": "saved", "skill": skill, "validation": validation}

    def pipeline_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        reflection = self.reflect(payload)
        if reflection["status"] != "ok":
            return reflection
        persist_packet = payload.get("persist_packet", True)

        validation_payload = dict(payload)
        validation_payload.update(reflection["candidate"])
        validation_payload["packet"] = reflection["packet"]
        validation_payload["packet_path"] = reflection.get("packet_path", "")
        validation_payload["persist_report"] = payload.get("persist_report", True)
        validation = self.validate(validation_payload)

        delta = {
            "created_at": utc_now(),
            "brief": reflection["brief"],
            "brief_path": reflection.get("brief_path", ""),
            "packet": validation["packet"],
            "packet_path": reflection.get("packet_path", ""),
            "candidate": validation["candidate"],
            "validation": {
                "status": validation["status"],
                "score": validation["score"],
                "blockers": validation["blockers"],
                "warnings": validation["warnings"],
                "merge_target": validation["merge_target"],
                "validation_path": validation.get("validation_path", ""),
            },
        }
        delta_path = self._write_delta(delta)
        packet = dict(validation["packet"])
        packet_path = reflection.get("packet_path", "")
        if persist_packet:
            packet, packet_path = self._refresh_packet(
                validation["packet"],
                artifact_refs=[
                    reflection.get("brief_path", ""),
                    validation.get("validation_path", ""),
                    delta_path,
                ],
                validation_status=validation["status"],
                pipeline_status=validation["status"],
            )
        else:
            packet["artifact_refs"] = unique_list(
                ensure_list(packet.get("artifact_refs"))
                + [item for item in [reflection.get("brief_path", ""), validation.get("validation_path", ""), delta_path] if item]
            )
            packet["validation_status"] = validation["status"]
            packet["pipeline_status"] = validation["status"]
        reflection["packet"] = packet
        reflection["packet_path"] = packet_path
        validation["packet"] = packet
        validation["packet_path"] = packet_path

        if validation["status"] == "blocked":
            self._append_log(
                "skill",
                f"blocked `{validation['candidate']['title']}`",
                [f"blockers: {', '.join(validation['blockers'])}", f"delta: {delta_path}"],
            )
            return {"status": "blocked", "reflection": reflection, "validation": validation, "packet": packet, "packet_path": packet_path, "delta_path": delta_path}

        persist = payload.get("persist", True)
        if not persist:
            return {"status": validation["status"], "reflection": reflection, "validation": validation, "packet": packet, "packet_path": packet_path, "delta_path": delta_path}

        if packet.get("route_decision") and packet["route_decision"] != "complete":
            routed_status = packet["route_decision"]
            if persist_packet:
                packet, packet_path = self._refresh_packet(packet, pipeline_status=routed_status)
            else:
                packet["pipeline_status"] = routed_status
            reflection["packet"] = packet
            reflection["packet_path"] = packet_path
            validation["packet"] = packet
            validation["packet_path"] = packet_path
            self._append_log(
                "skill",
                f"routed `{validation['candidate']['title']}`",
                [
                    f"route decision: {routed_status}",
                    f"route reason: {packet.get('route_reason') or 'none'}",
                    f"delta: {delta_path}",
                ],
            )
            return {
                "status": routed_status,
                "reflection": reflection,
                "validation": validation,
                "packet": packet,
                "packet_path": packet_path,
                "delta_path": delta_path,
            }

        auto_merge = payload.get("auto_merge")
        if auto_merge is None:
            auto_merge = self.auto_merge_duplicates

        if validation["merge_target"] and auto_merge:
            merged = self._merge_skill(validation["merge_target"], validation["candidate"], validation)
            if persist_packet:
                packet, packet_path = self._refresh_packet(packet, related_skill_id=validation["merge_target"], pipeline_status=merged["status"])
            else:
                packet["skill_id"] = validation["merge_target"]
                packet["related_skill_ids"] = unique_list(ensure_list(packet.get("related_skill_ids")) + [validation["merge_target"]])
                packet["pipeline_status"] = merged["status"]
            reflection["packet"] = packet
            reflection["packet_path"] = packet_path
            validation["packet"] = packet
            validation["packet_path"] = packet_path
            return {
                "status": merged["status"],
                "reflection": reflection,
                "validation": validation,
                "packet": packet,
                "packet_path": packet_path,
                "skill": merged.get("skill"),
                "delta_path": delta_path,
                "target_skill_id": validation["merge_target"],
            }

        saved = self.propose({**validation["candidate"], "allow_duplicate": payload.get("allow_duplicate", False), "persist_report": False})
        related_skill_id = ensure_text((saved.get("skill") or {}).get("id"))
        if persist_packet:
            packet, packet_path = self._refresh_packet(packet, related_skill_id=related_skill_id, pipeline_status=saved["status"])
        else:
            if related_skill_id:
                packet["skill_id"] = related_skill_id
                packet["related_skill_ids"] = unique_list(ensure_list(packet.get("related_skill_ids")) + [related_skill_id])
            packet["pipeline_status"] = saved["status"]
        reflection["packet"] = packet
        reflection["packet_path"] = packet_path
        validation["packet"] = packet
        validation["packet_path"] = packet_path
        return {
            "status": saved["status"],
            "reflection": reflection,
            "validation": validation,
            "packet": packet,
            "packet_path": packet_path,
            "skill": saved.get("skill"),
            "delta_path": delta_path,
        }

    def feedback(
        self,
        skill_id: str,
        verdict: str,
        reason: str,
        evidence: str = "",
        score_delta: int | None = None,
    ) -> dict[str, Any]:
        skill = self.get_skill(skill_id)
        if not skill:
            return {"status": "missing", "skill_id": skill_id}
        pii = detect_pii(reason, evidence)
        if pii:
            return {"status": "blocked", "reason": "pii_detected", "matches": pii}
        if score_delta is None:
            score_delta = 1 if verdict == "upvote" else -1 if verdict == "downvote" else 0
        row = {
            "id": f"feedback-{uuid.uuid4().hex[:12]}",
            "skill_id": skill_id,
            "verdict": verdict,
            "score_delta": int(score_delta),
            "reason": ensure_text(reason),
            "evidence": ensure_text(evidence),
            "created_at": utc_now(),
        }
        self.data["feedback"].append(row)

        skill["score"] = int(skill.get("score", 0)) + int(score_delta)
        if verdict == "upvote":
            skill["helpful_count"] = int(skill.get("helpful_count", 0)) + abs(int(score_delta))
            skill["last_validated"] = utc_day()
            if evidence:
                skill["evidence"] = merge_text(skill.get("evidence", ""), evidence)
        elif verdict == "downvote":
            skill["harmful_count"] = int(skill.get("harmful_count", 0)) + abs(int(score_delta))
            amendment = f"- Feedback downgrade: {reason}"
            if evidence:
                amendment = f"{amendment}\n- Evidence: {evidence}"
            skill["failure_modes"] = merge_text(skill.get("failure_modes", ""), amendment)
            skill["validation_status"] = "needs_revision"
        elif verdict == "amend":
            skill["last_validated"] = utc_day()
            amendment = f"- Feedback amendment: {reason}"
            if evidence:
                amendment = f"{amendment}\n- Evidence: {evidence}"
            skill["failure_modes"] = merge_text(skill.get("failure_modes", ""), amendment)

        skill["updated_at"] = row["created_at"]
        self._write_feedback(row)

        retired = False
        if skill["score"] < self.retire_below_score:
            retired = True
            self.retire(skill_id, f"Auto-retired after score fell below {self.retire_below_score}")
        else:
            self._save()
            self._write_skill(skill)
            self._sync_index()
            self._append_log(
                "skill",
                f"feedback for `{skill_id}`",
                [f"verdict: {verdict}", f"score delta: {score_delta:+d}", f"reason: {reason}"],
            )
        return {"status": "saved", "feedback": row, "retired": retired, "skill": self.get_skill(skill_id)}

    def retire(self, skill_id: str, reason: str) -> dict[str, Any]:
        skill = self.get_skill(skill_id)
        if not skill:
            return {"status": "missing", "skill_id": skill_id}
        pii = detect_pii(reason)
        if pii:
            return {"status": "blocked", "reason": "pii_detected", "matches": pii}
        skill["status"] = "retired"
        skill["validation_status"] = "retired"
        skill["updated_at"] = utc_now()
        self._save()
        active_path = self.active_dir / f"{skill_id}.md"
        if active_path.exists():
            active_path.unlink()
        self._write_skill(skill, retirement_reason=reason)
        self._sync_index()
        self._append_log("skill", f"retired `{skill_id}`", [f"reason: {reason}"])
        return {"status": "retired", "skill": skill, "reason": reason}

    def _write_skill(self, skill: dict[str, Any], retirement_reason: str = "") -> None:
        target_dir = self.retired_dir if skill["status"] == "retired" else self.active_dir
        feedback_summary = "\n".join(
            f"- {row['created_at']}: {row['verdict']} ({row['score_delta']:+d}) - {row['reason']}"
            for row in self.list_feedback(skill["id"])[-5:]
        ) or "- No feedback yet"
        validation_summary = "\n".join(f"- {item}" for item in ensure_list(skill.get("validation_notes"))) or "- No validation warnings recorded."
        brief_summary = "\n".join(f"- {item}" for item in ensure_list(skill.get("brief_refs"))) or "- No brief references recorded."
        merge_summary = "\n".join(f"- {item}" for item in ensure_list(skill.get("merge_history"))) or "- No merge history."
        applies = "\n".join(f"  - {yaml_quote(item)}" for item in skill["applies_to"]) or "  - \"<fill in>\""
        body = f"""---
id: {skill["id"]}
title: {yaml_quote(skill["title"])}
status: {skill["status"]}
kind: {skill["kind"]}
applies_to:
{applies}
score: {skill["score"]}
helpful_count: {skill.get("helpful_count", 0)}
harmful_count: {skill.get("harmful_count", 0)}
skip_steps_estimate: {skill["skip_steps_estimate"]}
confidence: {skill["confidence"]}
pii_review: passed
validation_status: {skill.get("validation_status", "unknown")}
validation_score: {skill.get("validation_score", 0)}
http_candidate: {"true" if skill["http_candidate"] else "false"}
source_type: {skill["source_type"]}
last_validated: {skill["last_validated"]}
brief_refs: {json.dumps(ensure_list(skill.get("brief_refs")))}
created_at: {skill["created_at"]}
updated_at: {skill["updated_at"]}
---

## Problem

{skill["problem"] or "Describe the repeated problem."}

## Trigger

{skill["trigger"] or "Describe when to apply this skill."}

## Preconditions

{skill["preconditions"] or "List the preconditions."}

## Fast Path

{skill["fast_path"] or "Describe the short reusable recipe."}

## Failure Modes

{skill["failure_modes"] or "Record edge cases and failure modes."}

## Feedback Summary

{feedback_summary}

## Validation Summary

{validation_summary}

## Brief References

{brief_summary}

## Merge History

{merge_summary}

## HTTP Upgrade Candidate

{"Yes" if skill["http_candidate"] else "No"}

## Evidence

{skill["evidence"] or "Record the grounding evidence."}
"""
        if retirement_reason:
            body += f"\n## Retirement Reason\n\n{retirement_reason}\n"
        (target_dir / f"{skill['id']}.md").write_text(body, encoding="utf-8")

    def _write_feedback(self, row: dict[str, Any]) -> None:
        path = self.feedback_dir / f"{row['created_at'][:10]}--{row['skill_id']}--{row['id']}.md"
        path.write_text(
            f"""---
id: {row["id"]}
skill_id: {row["skill_id"]}
verdict: {row["verdict"]}
score_delta: {row["score_delta"]}
created_at: {row["created_at"]}
---

## Reason

{row["reason"]}

## Evidence

{row["evidence"] or "No additional evidence supplied."}
""",
            encoding="utf-8",
        )

    def _sync_index(self) -> None:
        active = [skill for skill in self.data["skills"].values() if skill["status"] == "active"]
        retired = [skill for skill in self.data["skills"].values() if skill["status"] == "retired"]
        active.sort(key=lambda skill: (skill["score"], skill["updated_at"]), reverse=True)
        retired.sort(key=lambda skill: skill["updated_at"], reverse=True)

        def lines_for(skills: list[dict[str, Any]]) -> list[str]:
            if not skills:
                return ["| _none_ | _none_ | _none_ | 0 | _none_ | _none_ | _none_ |"]
            return [
                (
                    f"| `{skill['id']}` | {skill['title']} | `{skill['kind']}` | {skill['score']} "
                    f"| {skill.get('validation_status', 'unknown')} ({skill.get('validation_score', 0)}) "
                    f"| `{', '.join(skill['applies_to'])}` | {skill['updated_at']} |"
                )
                for skill in skills
            ]

        lines = [
            "# Skill Index",
            "",
            "## Active Skills",
            "",
            "| ID | Title | Kind | Score | Validation | Applies To | Updated |",
            "| --- | --- | --- | ---: | --- | --- | --- |",
            *lines_for(active),
            "",
            "## Retired Skills",
            "",
            "| ID | Title | Kind | Score | Validation | Applies To | Updated |",
            "| --- | --- | --- | ---: | --- | --- | --- |",
            *lines_for(retired),
            "",
        ]
        self.index_path.write_text("\n".join(lines), encoding="utf-8")

def mcp_tools() -> list[dict[str, Any]]:
    base_skill_fields = {
        "skill_id": {"type": "string"},
        "title": {"type": "string"},
        "kind": {"type": "string"},
        "applies_to": {"type": "array", "items": {"type": "string"}},
        "goal": {"type": "string"},
        "problem": {"type": "string"},
        "trigger": {"type": "string"},
        "preconditions": {"type": "string"},
        "fast_path": {"type": "string"},
        "failure_modes": {"type": "string"},
        "evidence": {"type": "string"},
        "important_context": {"type": "string"},
        "observations": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "next_actions": {"type": "array", "items": {"type": "string"}},
        "files": {"type": "array", "items": {"type": "string"}},
        "references": {"type": "array", "items": {"type": "string"}},
        "outcome": {"type": "string"},
        "route_decision": {"type": "string", "enum": sorted(ROUTE_DECISIONS)},
        "route_reason": {"type": "string"},
        "unresolved_questions": {"type": "array", "items": {"type": "string"}},
        "artifact_refs": {"type": "array", "items": {"type": "string"}},
        "assigned_target": {"type": "string"},
        "parent_packet_id": {"type": "string"},
        "hop_count": {"type": "integer"},
        "retry_count": {"type": "integer"},
        "http_candidate": {"type": "boolean"},
        "source_type": {"type": "string"},
        "skip_steps_estimate": {"type": "integer"},
        "confidence": {"type": "string"},
        "last_validated": {"type": "string"},
        "persist": {"type": "boolean"},
        "persist_brief": {"type": "boolean"},
        "persist_packet": {"type": "boolean"},
        "persist_report": {"type": "boolean"},
        "auto_merge": {"type": "boolean"},
        "allow_duplicate": {"type": "boolean"},
        "long_task": {"type": "boolean"},
    }
    return [
        {
            "name": "skill_lookup",
            "description": "Find active reusable skills relevant to a URL pattern, task type, or goal.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url_pattern": {"type": "string"},
                    "task_type": {"type": "string"},
                    "goal": {"type": "string"},
                    "context": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
        {
            "name": "skill_reflect",
            "description": "Create an executive brief, reducer packet, and normalized skill candidate from a completed task or long-running trajectory.",
            "inputSchema": {
                "type": "object",
                "required": ["title", "kind", "goal", "evidence"],
                "properties": base_skill_fields,
            },
        },
        {
            "name": "skill_validate",
            "description": "Validate a skill candidate or existing skill for privacy, structure, evidence quality, duplicate overlap, and reducer packet routing semantics.",
            "inputSchema": {
                "type": "object",
                "properties": base_skill_fields,
            },
        },
        {
            "name": "skill_pipeline_run",
            "description": "Run reflect -> validate -> curate. Persists briefs, reducer packets, validation reports, and only curates when the route decision is complete.",
            "inputSchema": {
                "type": "object",
                "required": ["title", "kind", "goal", "evidence"],
                "properties": base_skill_fields,
            },
        },
        {
            "name": "skill_propose",
            "description": "Create or update a reusable skill in the local skill library after validation.",
            "inputSchema": {
                "type": "object",
                "required": ["title", "kind", "applies_to", "trigger", "fast_path", "evidence"],
                "properties": base_skill_fields,
            },
        },
        {
            "name": "skill_feedback",
            "description": "Record feedback for an existing skill, update its score, and fold reasoned amendments back into the skill.",
            "inputSchema": {
                "type": "object",
                "required": ["skill_id", "verdict", "reason"],
                "properties": {
                    "skill_id": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["upvote", "downvote", "amend"]},
                    "reason": {"type": "string"},
                    "evidence": {"type": "string"},
                    "score_delta": {"type": "integer"},
                },
            },
        },
        {
            "name": "skill_get",
            "description": "Fetch a skill, related briefs, related packets, and its feedback by skill id.",
            "inputSchema": {
                "type": "object",
                "required": ["skill_id"],
                "properties": {"skill_id": {"type": "string"}},
            },
        },
        {
            "name": "skill_retire",
            "description": "Retire an active skill and move it out of the active registry.",
            "inputSchema": {
                "type": "object",
                "required": ["skill_id", "reason"],
                "properties": {
                    "skill_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
    ]


def tool_result(payload: dict[str, Any], is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}], "isError": is_error}


def read_message() -> dict[str, Any] | None:
    content_length = None
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        if line.lower().startswith(b"content-length:"):
            content_length = int(line.split(b":", 1)[1].strip())
    if content_length is None:
        return None
    return json.loads(sys.stdin.buffer.read(content_length).decode("utf-8"))


def write_message(payload: dict[str, Any]) -> None:
    raw = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def run_mcp(workspace: str) -> int:
    store = SkillStore(workspace)
    while True:
        message = read_message()
        if message is None:
            return 0
        method = message.get("method")
        msg_id = message.get("id")
        if method == "initialize":
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    },
                }
            )
        elif method == "notifications/initialized":
            continue
        elif method == "ping":
            write_message({"jsonrpc": "2.0", "id": msg_id, "result": {}})
        elif method == "tools/list":
            write_message({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": mcp_tools()}})
        elif method == "tools/call":
            params = message.get("params", {})
            name = str(params.get("name", ""))
            arguments = params.get("arguments", {}) or {}
            if name == "skill_lookup":
                result = store.lookup(
                    str(arguments.get("url_pattern", "")),
                    str(arguments.get("task_type", "")),
                    str(arguments.get("goal", "")),
                    str(arguments.get("context", "")),
                    int(arguments.get("limit", 5)),
                )
                write_message({"jsonrpc": "2.0", "id": msg_id, "result": tool_result(result)})
            elif name == "skill_reflect":
                result = store.reflect(arguments)
                write_message({"jsonrpc": "2.0", "id": msg_id, "result": tool_result(result, result.get("status") in {"blocked", "missing"})})
            elif name == "skill_validate":
                result = store.validate(arguments)
                write_message({"jsonrpc": "2.0", "id": msg_id, "result": tool_result(result, result.get("status") in {"blocked", "missing"})})
            elif name == "skill_pipeline_run":
                result = store.pipeline_run(arguments)
                write_message({"jsonrpc": "2.0", "id": msg_id, "result": tool_result(result, result.get("status") in {"blocked", "missing"})})
            elif name == "skill_propose":
                result = store.propose(arguments)
                write_message({"jsonrpc": "2.0", "id": msg_id, "result": tool_result(result, result.get("status") in {"blocked", "missing"})})
            elif name == "skill_feedback":
                result = store.feedback(
                    str(arguments["skill_id"]),
                    str(arguments["verdict"]),
                    str(arguments["reason"]),
                    str(arguments.get("evidence", "")),
                    arguments.get("score_delta"),
                )
                write_message({"jsonrpc": "2.0", "id": msg_id, "result": tool_result(result, result.get("status") in {"blocked", "missing"})})
            elif name == "skill_get":
                skill_id = str(arguments["skill_id"])
                skill = store.get_skill(skill_id)
                result = (
                    {
                        "status": "ok",
                        "skill": skill,
                        "feedback": store.list_feedback(skill_id),
                        "briefs": store.list_briefs(skill_id),
                        "packets": store.list_packets(skill_id),
                    }
                    if skill
                    else {"status": "missing", "skill_id": skill_id}
                )
                write_message({"jsonrpc": "2.0", "id": msg_id, "result": tool_result(result, result.get("status") == "missing")})
            elif name == "skill_retire":
                result = store.retire(str(arguments["skill_id"]), str(arguments["reason"]))
                write_message({"jsonrpc": "2.0", "id": msg_id, "result": tool_result(result, result.get("status") in {"blocked", "missing"})})
            else:
                write_message({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}})
        elif msg_id is not None:
            write_message({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    mcp_parser = sub.add_parser("mcp")
    mcp_parser.add_argument("--workspace", dest="subcommand_workspace", default=None)

    lookup = sub.add_parser("lookup")
    lookup.add_argument("--url-pattern", default="")
    lookup.add_argument("--task-type", default="")
    lookup.add_argument("--goal", default="")
    lookup.add_argument("--context", default="")
    lookup.add_argument("--limit", type=int, default=5)

    reflect = sub.add_parser("reflect")
    reflect.add_argument("--skill-id")
    reflect.add_argument("--title", required=True)
    reflect.add_argument("--kind", required=True)
    reflect.add_argument("--apply", dest="applies_to", action="append")
    reflect.add_argument("--goal", required=True)
    reflect.add_argument("--problem", default="")
    reflect.add_argument("--trigger", default="")
    reflect.add_argument("--preconditions", default="")
    reflect.add_argument("--fast-path", default="")
    reflect.add_argument("--failure-modes", default="")
    reflect.add_argument("--evidence", required=True)
    reflect.add_argument("--important-context", default="")
    reflect.add_argument("--observation", dest="observations", action="append")
    reflect.add_argument("--risk", dest="risks", action="append")
    reflect.add_argument("--next-action", dest="next_actions", action="append")
    reflect.add_argument("--file", dest="files", action="append")
    reflect.add_argument("--reference", dest="references", action="append")
    reflect.add_argument("--outcome", default="")
    reflect.add_argument("--route-decision", choices=sorted(ROUTE_DECISIONS))
    reflect.add_argument("--route-reason", default="")
    reflect.add_argument("--unresolved-question", dest="unresolved_questions", action="append")
    reflect.add_argument("--artifact-ref", dest="artifact_refs", action="append")
    reflect.add_argument("--assigned-target", default="")
    reflect.add_argument("--parent-packet-id", default="")
    reflect.add_argument("--hop-count", type=int, default=0)
    reflect.add_argument("--retry-count", type=int, default=0)
    reflect.add_argument("--http-candidate", action="store_true")
    reflect.add_argument("--source-type", default="trajectory")
    reflect.add_argument("--skip-steps-estimate", type=int, default=0)
    reflect.add_argument("--confidence", default="medium")
    reflect.add_argument("--last-validated", default="")
    reflect.add_argument("--long-task", action="store_true")
    reflect.add_argument("--no-persist-packet", dest="persist_packet", action="store_false")
    reflect.add_argument("--persist-brief", action="store_true")
    reflect.set_defaults(persist_brief=True, persist_packet=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--skill-id")
    validate.add_argument("--title")
    validate.add_argument("--kind")
    validate.add_argument("--apply", dest="applies_to", action="append")
    validate.add_argument("--goal", default="")
    validate.add_argument("--problem", default="")
    validate.add_argument("--trigger", default="")
    validate.add_argument("--preconditions", default="")
    validate.add_argument("--fast-path", default="")
    validate.add_argument("--failure-modes", default="")
    validate.add_argument("--evidence", default="")
    validate.add_argument("--important-context", default="")
    validate.add_argument("--observation", dest="observations", action="append")
    validate.add_argument("--risk", dest="risks", action="append")
    validate.add_argument("--next-action", dest="next_actions", action="append")
    validate.add_argument("--file", dest="files", action="append")
    validate.add_argument("--reference", dest="references", action="append")
    validate.add_argument("--outcome", default="")
    validate.add_argument("--route-decision", choices=sorted(ROUTE_DECISIONS))
    validate.add_argument("--route-reason", default="")
    validate.add_argument("--unresolved-question", dest="unresolved_questions", action="append")
    validate.add_argument("--artifact-ref", dest="artifact_refs", action="append")
    validate.add_argument("--assigned-target", default="")
    validate.add_argument("--parent-packet-id", default="")
    validate.add_argument("--hop-count", type=int, default=0)
    validate.add_argument("--retry-count", type=int, default=0)
    validate.add_argument("--http-candidate", action="store_true")
    validate.add_argument("--source-type", default="trajectory")
    validate.add_argument("--skip-steps-estimate", type=int, default=0)
    validate.add_argument("--confidence", default="medium")
    validate.add_argument("--last-validated", default="")
    validate.add_argument("--long-task", action="store_true")
    validate.add_argument("--no-persist-report", dest="persist_report", action="store_false")
    validate.set_defaults(persist_report=True)

    propose = sub.add_parser("propose")
    propose.add_argument("--skill-id")
    propose.add_argument("--title", required=True)
    propose.add_argument("--kind", required=True)
    propose.add_argument("--apply", dest="applies_to", action="append", required=True)
    propose.add_argument("--goal", default="")
    propose.add_argument("--problem", default="")
    propose.add_argument("--trigger", required=True)
    propose.add_argument("--preconditions", default="")
    propose.add_argument("--fast-path", required=True)
    propose.add_argument("--failure-modes", default="")
    propose.add_argument("--evidence", required=True)
    propose.add_argument("--important-context", default="")
    propose.add_argument("--observation", dest="observations", action="append")
    propose.add_argument("--risk", dest="risks", action="append")
    propose.add_argument("--next-action", dest="next_actions", action="append")
    propose.add_argument("--file", dest="files", action="append")
    propose.add_argument("--reference", dest="references", action="append")
    propose.add_argument("--outcome", default="")
    propose.add_argument("--route-decision", choices=sorted(ROUTE_DECISIONS))
    propose.add_argument("--route-reason", default="")
    propose.add_argument("--unresolved-question", dest="unresolved_questions", action="append")
    propose.add_argument("--artifact-ref", dest="artifact_refs", action="append")
    propose.add_argument("--assigned-target", default="")
    propose.add_argument("--parent-packet-id", default="")
    propose.add_argument("--hop-count", type=int, default=0)
    propose.add_argument("--retry-count", type=int, default=0)
    propose.add_argument("--http-candidate", action="store_true")
    propose.add_argument("--source-type", default="trajectory")
    propose.add_argument("--skip-steps-estimate", type=int, default=0)
    propose.add_argument("--confidence", default="medium")
    propose.add_argument("--last-validated", default="")
    propose.add_argument("--long-task", action="store_true")
    propose.add_argument("--allow-duplicate", action="store_true")
    propose.add_argument("--no-persist-report", dest="persist_report", action="store_false")
    propose.set_defaults(persist_report=True)

    pipeline = sub.add_parser("pipeline-run")
    pipeline.add_argument("--skill-id")
    pipeline.add_argument("--title", required=True)
    pipeline.add_argument("--kind", required=True)
    pipeline.add_argument("--apply", dest="applies_to", action="append")
    pipeline.add_argument("--goal", required=True)
    pipeline.add_argument("--problem", default="")
    pipeline.add_argument("--trigger", default="")
    pipeline.add_argument("--preconditions", default="")
    pipeline.add_argument("--fast-path", default="")
    pipeline.add_argument("--failure-modes", default="")
    pipeline.add_argument("--evidence", required=True)
    pipeline.add_argument("--important-context", default="")
    pipeline.add_argument("--observation", dest="observations", action="append")
    pipeline.add_argument("--risk", dest="risks", action="append")
    pipeline.add_argument("--next-action", dest="next_actions", action="append")
    pipeline.add_argument("--file", dest="files", action="append")
    pipeline.add_argument("--reference", dest="references", action="append")
    pipeline.add_argument("--outcome", default="")
    pipeline.add_argument("--route-decision", choices=sorted(ROUTE_DECISIONS))
    pipeline.add_argument("--route-reason", default="")
    pipeline.add_argument("--unresolved-question", dest="unresolved_questions", action="append")
    pipeline.add_argument("--artifact-ref", dest="artifact_refs", action="append")
    pipeline.add_argument("--assigned-target", default="")
    pipeline.add_argument("--parent-packet-id", default="")
    pipeline.add_argument("--hop-count", type=int, default=0)
    pipeline.add_argument("--retry-count", type=int, default=0)
    pipeline.add_argument("--http-candidate", action="store_true")
    pipeline.add_argument("--source-type", default="trajectory")
    pipeline.add_argument("--skip-steps-estimate", type=int, default=0)
    pipeline.add_argument("--confidence", default="medium")
    pipeline.add_argument("--last-validated", default="")
    pipeline.add_argument("--long-task", action="store_true")
    pipeline.add_argument("--no-persist", dest="persist", action="store_false")
    pipeline.add_argument("--no-persist-brief", dest="persist_brief", action="store_false")
    pipeline.add_argument("--no-persist-packet", dest="persist_packet", action="store_false")
    pipeline.add_argument("--no-persist-report", dest="persist_report", action="store_false")
    pipeline.add_argument("--no-auto-merge", dest="auto_merge", action="store_false")
    pipeline.add_argument("--allow-duplicate", action="store_true")
    pipeline.set_defaults(persist=True, persist_brief=True, persist_packet=True, persist_report=True, auto_merge=True)

    feedback = sub.add_parser("feedback")
    feedback.add_argument("--skill-id", required=True)
    feedback.add_argument("--verdict", choices=["upvote", "downvote", "amend"], required=True)
    feedback.add_argument("--reason", required=True)
    feedback.add_argument("--evidence", default="")
    feedback.add_argument("--score-delta", type=int)

    retire = sub.add_parser("retire")
    retire.add_argument("--skill-id", required=True)
    retire.add_argument("--reason", required=True)

    get_cmd = sub.add_parser("get")
    get_cmd.add_argument("--skill-id", required=True)

    sub.add_parser("sync-index")

    args = parser.parse_args(argv)

    if args.command == "mcp":
        return run_mcp(args.subcommand_workspace or args.workspace)

    store = SkillStore(args.workspace)
    payload = vars(args)
    command = payload.pop("command")
    payload.pop("workspace", None)

    if command == "lookup":
        result = store.lookup(payload["url_pattern"], payload["task_type"], payload["goal"], payload["context"], payload["limit"])
    elif command == "reflect":
        result = store.reflect(payload)
    elif command == "validate":
        result = store.validate(payload)
    elif command == "propose":
        result = store.propose(payload)
    elif command == "pipeline-run":
        result = store.pipeline_run(payload)
    elif command == "feedback":
        result = store.feedback(payload["skill_id"], payload["verdict"], payload["reason"], payload["evidence"], payload["score_delta"])
    elif command == "retire":
        result = store.retire(payload["skill_id"], payload["reason"])
    elif command == "get":
        skill = store.get_skill(payload["skill_id"])
        result = {
            "status": "ok",
            "skill": skill,
            "feedback": store.list_feedback(payload["skill_id"]),
            "briefs": store.list_briefs(payload["skill_id"]),
            "packets": store.list_packets(payload["skill_id"]),
        } if skill else {"status": "missing", "skill_id": payload["skill_id"]}
    else:
        store._sync_index()
        result = {"status": "ok", "index_path": str(store.index_path)}

    print(json.dumps(result, indent=2))
    return 0 if result.get("status") not in {"blocked", "missing"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
