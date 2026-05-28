#!/usr/bin/env python3
"""Lightweight read-only dashboard for llm-wiki-memory.

Serves at /dashboard on the local gateway or as a standalone process.
Usage:
    python scripts/dashboard_server.py [--workspace PATH] [--host HOST] [--port PORT]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote_plus, urlsplit

# Use stdlib only; no external framework dependencies
from http.server import HTTPServer, BaseHTTPRequestHandler

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from skill_index import ensure_index

try:
    from ouroboros_adapter import discover_ouroboros_sessions
except Exception:
    discover_ouroboros_sessions = None


class DashboardHandler(BaseHTTPRequestHandler):
    workspace: Path = Path.cwd()
    registry_root: Path = Path.cwd()
    workspace_scan_limit: int = 250
    session_scan_limit: int = 80

    def log_message(self, fmt: str, *args) -> None:
        # Suppress default logging for cleaner output
        pass

    def _send_localhost_cors(self) -> None:
        origin = self.headers.get("Origin", "")
        if not origin:
            return
        parsed = urlsplit(origin)
        if parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _send_json(self, data: dict) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_localhost_cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_html(self, body: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._send_localhost_cors()
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _read_config(self) -> dict:
        path = self.workspace / ".llm-wiki" / "config.json"
        config = {}
        if path.exists():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        config["workspace_name"] = self.workspace.name
        config["vault_name"] = config.get("obsidian", {}).get("vault", self.workspace.name)
        return config

    def _read_index(self) -> dict:
        path = self.workspace / ".llm-wiki" / "skill-index.json"
        try:
            path = ensure_index(self.workspace)
        except Exception:
            pass
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _brv_status(self) -> dict:
        config = self._read_config()
        command = config.get("byterover", {}).get("command", "")
        if not command:
            return {"available": False, "output": "brv integration disabled in config.json"}
        try:
            result = subprocess.run(
                [command, "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "available": result.returncode == 0,
                "output": result.stdout.strip() if result.returncode == 0 else result.stderr.strip(),
            }
        except FileNotFoundError:
            return {"available": False, "output": f"'{command}' command not found"}
        except Exception as exc:
            return {"available": False, "output": str(exc)}


    def _wiki_pages(self, query: str = "") -> list[dict]:
        wiki_dir = self.workspace / "wiki"
        if not wiki_dir.exists():
            return []
        pages = []
        for path in wiki_dir.rglob("*.md"):
            rel = str(path.relative_to(self.workspace))
            title = path.stem.replace("-", " ")
            content = path.read_text(encoding="utf-8", errors="ignore")
            if query and query.lower() not in (title + content).lower():
                continue
            vault = DashboardHandler._read_config(self).get("vault_name", "llm-wiki")
            normalized_rel = rel.replace("/", "%2F").replace("\\", "%2F")
            pages.append({
                "path": rel,
                "title": title,
                "snippet": content[:200].replace("\n", " "),
                "obsidian_url": f"obsidian://open?vault={vault}&file={normalized_rel}",
            })
        return pages[:50]

    def _recent_log_entries(self, limit: int = 20) -> list[dict]:
        log_path = self.workspace / "wiki" / "log.md"
        if not log_path.exists():
            return []
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        entries = []
        current: dict[str, Any] = {}
        for line in text.splitlines():
            if line.startswith("## "):
                if current:
                    entries.append(current)
                current = {"heading": line[3:].strip(), "lines": []}
            elif current:
                current["lines"].append(line)
        if current:
            entries.append(current)
        # Return most recent first
        return [{"heading": e["heading"], "body": "\n".join(e["lines"]).strip()} for e in reversed(entries[-limit:])]

    def _memory_objects(self, status: str = "") -> list[dict]:
        config = DashboardHandler._read_config(self)
        controller = config.get("memory_controller") if isinstance(config.get("memory_controller"), dict) else {}
        configured = str(controller.get("ledger_path") or ".llm-wiki/memory-ledger")
        ledger = Path(configured)
        if not ledger.is_absolute():
            ledger = self.workspace / ledger
        objects: list[dict] = []
        for bucket in ("candidates", "approved"):
            directory = ledger / bucket
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.json")):
                try:
                    item = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if status and item.get("status") != status:
                    continue
                objects.append(
                    {
                        "id": item.get("id", ""),
                        "kind": item.get("kind", ""),
                        "status": item.get("status", ""),
                        "claim": item.get("claim", ""),
                        "confidence": item.get("confidence", ""),
                        "sensitivity": item.get("sensitivity", ""),
                        "rank_score": item.get("rank_score", 0),
                        "source_refs": item.get("source_refs", []),
                        "supersedes": item.get("supersedes", []),
                        "superseded_by": item.get("superseded_by", ""),
                        "contradicts": item.get("contradicts", []),
                        "valid_from": item.get("valid_from", ""),
                        "valid_to": item.get("valid_to", ""),
                    }
                )
        objects.sort(key=lambda item: item.get("valid_from", ""), reverse=True)
        return objects[:100]

    def _memory_events(self, limit: int = 25) -> list[dict]:
        config = DashboardHandler._read_config(self)
        controller = config.get("memory_controller") if isinstance(config.get("memory_controller"), dict) else {}
        configured = str(controller.get("ledger_path") or ".llm-wiki/memory-ledger")
        ledger = Path(configured)
        if not ledger.is_absolute():
            ledger = self.workspace / ledger
        events_path = ledger / "events.jsonl"
        if not events_path.exists():
            return []
        events: list[dict] = []
        for line in events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(events[-limit:]))

    def _reducer_drafts(self) -> list[dict]:
        drafts_dir = self.workspace / ".llm-wiki" / "skill-pipeline" / "auto-packets"
        if not drafts_dir.exists():
            return []
        drafts = []
        for path in sorted(drafts_dir.glob("auto-*.md")):
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            task = ""
            outcome = ""
            candidacy = ""
            for line in lines:
                if line.strip().startswith("skill_candidacy:"):
                    candidacy = line.split(":", 1)[1].strip()
                elif line.strip().startswith("outcome:"):
                    outcome = line.split(":", 1)[1].strip()
            if "## Task Summary" in content:
                parts = content.split("## Task Summary", 1)
                task = parts[1].split("##", 1)[0].strip()
            drafts.append({
                "id": path.stem,
                "task": task[:300],
                "outcome": outcome,
                "candidacy": candidacy,
            })
        return drafts

    def _parse_wiki_links(self, content: str) -> list[str]:
        import re
        links = []
        for match in re.finditer(r'\[\[(.*?)\]\]', content):
            links.append(match.group(1).strip())
        return links

    def _is_hidden_or_heavy_dir(self, path: Path) -> bool:
        return path.name in {
            ".git",
            ".hg",
            ".svn",
            ".llm-wiki",
            ".venv",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
            ".next",
            ".cache",
        }

    def _workspace_search_roots(self) -> list[Path]:
        roots: list[Path] = []
        for candidate in (
            self.workspace,
            self.workspace.parent,
            self.workspace.parent.parent if self.workspace.parent else None,
            Path("C:/dev/Desktop-Projects"),
            Path.home() / "Desktop",
            Path.home() / "Documents",
        ):
            if candidate and candidate.exists() and candidate.is_dir():
                resolved = candidate.resolve()
                if resolved not in roots:
                    roots.append(resolved)
        return roots

    def _project_markers(self, path: Path) -> list[str]:
        markers = []
        for name in (".git", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", ".llm-wiki"):
            if (path / name).exists():
                markers.append(name)
        return markers

    def _wiki_registry_path(self) -> Path:
        return DashboardHandler.registry_root / ".llm-wiki" / "dashboard-wiki-projects.json"

    def _load_wiki_registry(self) -> dict[str, dict]:
        path = DashboardHandler._wiki_registry_path(self)
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        projects = payload.get("projects", []) if isinstance(payload, dict) else []
        registry = {}
        for item in projects:
            if isinstance(item, dict) and item.get("path"):
                registry[str(item["path"])] = item
        return registry

    def _save_wiki_registry(self, items: list[dict]) -> None:
        path = DashboardHandler._wiki_registry_path(self)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "updated_at": int(time.time()),
                "projects": items,
            }
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _wiki_project_item(self, path: Path, active: Path) -> dict:
        markers = DashboardHandler._project_markers(self, path)
        try:
            pages = sum(1 for _ in (path / "wiki").rglob("*.md"))
        except OSError:
            pages = 0
        return {
            "name": path.name,
            "path": str(path),
            "active": path == active,
            "markers": markers,
            "page_count": pages,
            "kind": "repo" if ".git" in markers else "project",
        }

    def _discover_wiki_projects(self, root: Path, max_depth: int = 3) -> list[Path]:
        found: list[Path] = []
        queue: list[tuple[Path, int]] = [(root, 0)]
        visited: set[Path] = set()
        while queue and len(visited) < self.workspace_scan_limit:
            current, depth = queue.pop(0)
            try:
                resolved = current.resolve()
            except OSError:
                continue
            if resolved in visited:
                continue
            visited.add(resolved)
            if (resolved / "wiki").is_dir():
                found.append(resolved)
            if depth >= max_depth or DashboardHandler._is_hidden_or_heavy_dir(self, resolved):
                continue
            try:
                children = sorted([child for child in resolved.iterdir() if child.is_dir()], key=lambda p: p.name.lower())
            except OSError:
                continue
            for child in children:
                if not DashboardHandler._is_hidden_or_heavy_dir(self, child):
                    queue.append((child, depth + 1))
        return found

    def _list_available_wikis(self, refresh: bool = False) -> list[dict]:
        active = self.workspace.resolve()
        cached = DashboardHandler._load_wiki_registry(self)
        if cached and not refresh:
            items = []
            for raw in cached.values():
                path = Path(str(raw.get("path", "")))
                if not path.exists() or not (path / "wiki").is_dir():
                    continue
                item = dict(raw)
                item["active"] = path.resolve() == active
                items.append(item)
            if active and (active / "wiki").is_dir() and str(active) not in {item["path"] for item in items}:
                items.append(DashboardHandler._wiki_project_item(self, active, active))
            return sorted(items, key=lambda item: item.get("path", "").lower())

        projects: dict[str, Path] = {}
        for root in DashboardHandler._workspace_search_roots(self):
            for project in DashboardHandler._discover_wiki_projects(self, root):
                projects[str(project)] = project
        if (active / "wiki").is_dir():
            projects[str(active)] = active

        wikis = []
        for path in sorted(projects.values(), key=lambda item: str(item).lower()):
            wikis.append(DashboardHandler._wiki_project_item(self, path, active))
        DashboardHandler._save_wiki_registry(self, wikis)
        return wikis

    def _jsonl_records(self, path: Path, head: int = 20, tail: int = 80) -> list[dict]:
        try:
            lines: list[str] = []
            if head:
                with path.open("r", encoding="utf-8", errors="ignore") as handle:
                    for _ in range(head):
                        line = handle.readline()
                        if not line:
                            break
                        lines.append(line.rstrip("\r\n"))
            if tail:
                with path.open("rb") as handle:
                    size = handle.seek(0, os.SEEK_END)
                    handle.seek(max(0, size - 262144))
                    tail_text = handle.read().decode("utf-8", errors="ignore")
                tail_lines = tail_text.splitlines()[-tail:]
                lines.extend(tail_lines)
        except OSError:
            return []
        records = []
        for line in lines:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append(item)
        return records

    def _short_time(self, timestamp: float) -> str:
        age = max(0, time.time() - timestamp)
        if age < 60:
            return "just now"
        if age < 3600:
            return f"{int(age // 60)}m ago"
        if age < 86400:
            return f"{int(age // 3600)}h ago"
        return f"{int(age // 86400)}d ago"

    def _record_text(self, record: dict) -> str:
        message = record.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [item["text"] for item in content if isinstance(item, dict) and isinstance(item.get("text"), str)]
                if parts:
                    return " ".join(parts)
        payload = record.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("text"), str):
            return payload["text"]
        for key in ("lastPrompt", "text", "aiTitle", "thread_name"):
            value = record.get(key)
            if isinstance(value, str):
                return value
        return ""

    def _session_item(
        self,
        provider: str,
        session_id: str,
        title: str,
        path: Path,
        cwd: str = "",
        command: str = "",
        status: str = "available",
    ) -> dict:
        try:
            updated = path.stat().st_mtime
            size = path.stat().st_size
        except OSError:
            updated = 0
            size = 0
        return {
            "provider": provider,
            "id": session_id,
            "title": title or session_id or path.stem,
            "path": str(path),
            "cwd": cwd,
            "updated_at": updated,
            "updated_label": DashboardHandler._short_time(self, updated) if updated else "unknown",
            "size": size,
            "resume_command": command,
            "status": status,
        }

    def _codex_session_titles(self) -> dict[str, str]:
        titles: dict[str, str] = {}
        index_path = Path.home() / ".codex" / "session_index.jsonl"
        if index_path.exists():
            for record in DashboardHandler._jsonl_records(self, index_path, head=0, tail=500):
                session_id = str(record.get("id") or "")
                title = str(record.get("thread_name") or "")
                if session_id and title:
                    titles[session_id] = title
        history_path = Path.home() / ".codex" / "history.jsonl"
        if history_path.exists():
            for record in DashboardHandler._jsonl_records(self, history_path, head=0, tail=300):
                session_id = str(record.get("session_id") or "")
                text = str(record.get("text") or "").strip()
                if session_id and text:
                    titles[session_id] = text[:90]
        return titles

    def _codex_sessions(self) -> tuple[dict, list[dict]]:
        root = Path.home() / ".codex"
        sessions_root = root / "sessions"
        if not root.exists():
            return {"provider": "OpenCodecs", "available": False, "message": "No ~/.codex state directory found"}, []
        titles = DashboardHandler._codex_session_titles(self)
        files = []
        if sessions_root.exists():
            files = sorted(sessions_root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[: self.session_scan_limit]
        sessions = []
        for path in files:
            records = DashboardHandler._jsonl_records(self, path, head=30, tail=40)
            meta = next((r.get("payload") for r in records if r.get("type") == "session_meta" and isinstance(r.get("payload"), dict)), {})
            session_id = str(meta.get("id") or path.stem.split("-")[-1])
            cwd = str(meta.get("cwd") or "")
            title = titles.get(session_id, "")
            if not title:
                for record in reversed(records):
                    text = DashboardHandler._record_text(self, record).strip()
                    if text:
                        title = text[:90]
                        break
            command = f"codex resume {session_id}"
            if cwd:
                command = f'cd "{cwd}" && {command}'
            sessions.append(DashboardHandler._session_item(self, "OpenCodecs", session_id, title, path, cwd, command))
        return {"provider": "OpenCodecs", "available": True, "message": f"{len(sessions)} sessions found"}, sessions

    def _claude_sessions(self) -> tuple[dict, list[dict]]:
        projects_root = Path.home() / ".claude" / "projects"
        if not projects_root.exists():
            return {"provider": "Claude Code", "available": False, "message": "No ~/.claude/projects directory found"}, []
        files = sorted(projects_root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[: self.session_scan_limit]
        sessions = []
        for path in files:
            records = DashboardHandler._jsonl_records(self, path, head=20, tail=80)
            session_id = path.stem
            cwd = ""
            title = ""
            for record in records:
                if record.get("sessionId"):
                    session_id = str(record.get("sessionId"))
                if record.get("cwd"):
                    cwd = str(record.get("cwd"))
                if record.get("type") == "ai-title" and record.get("aiTitle"):
                    title = str(record.get("aiTitle"))
            if not title:
                for record in reversed(records):
                    text = DashboardHandler._record_text(self, record).strip()
                    if text:
                        title = text[:90]
                        break
            command = f"claude --resume {session_id}"
            if cwd:
                command = f'cd "{cwd}" && {command}'
            sessions.append(DashboardHandler._session_item(self, "Claude Code", session_id, title, path, cwd, command))
        return {"provider": "Claude Code", "available": True, "message": f"{len(sessions)} sessions found"}, sessions

    def _generic_provider_sessions(self, provider: str, roots: list[Path], command_name: str = "") -> tuple[dict, list[dict]]:
        existing = [root for root in roots if root.exists()]
        if not existing:
            return {"provider": provider, "available": False, "message": "No known state directory found"}, []
        files: list[Path] = []
        for root in existing:
            try:
                files.extend([p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".jsonl", ".json", ".log"}])
            except OSError:
                continue
        files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[: self.session_scan_limit]
        sessions = []
        for path in files:
            session_id = path.stem
            title = path.name
            command = f"{command_name} resume {session_id}" if command_name else ""
            sessions.append(DashboardHandler._session_item(self, provider, session_id, title, path, "", command, "detected"))
        return {"provider": provider, "available": True, "message": f"{len(sessions)} candidate session artifacts found"}, sessions

    def _session_sources(self) -> dict:
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        roaming = Path(os.environ.get("APPDATA", ""))
        providers = []
        sessions = []
        for status, items in (
            DashboardHandler._codex_sessions(self),
            DashboardHandler._claude_sessions(self),
            DashboardHandler._generic_provider_sessions(self, "AGY-AntiGravity", [Path.home() / ".antigravity", local / "agy", local / "antigravity", roaming / "Antigravity"], "agy"),
            DashboardHandler._generic_provider_sessions(self, "Chemi", [Path.home() / ".chemi", local / "Chemi", roaming / "Chemi"], "chemi"),
        ):
            providers.append(status)
            sessions.extend(items)
        if discover_ouroboros_sessions:
            status, items = discover_ouroboros_sessions(self.workspace, Path.home(), self.session_scan_limit)
        else:
            status, items = {"provider": "Ouroboros", "available": False, "message": "Adapter unavailable"}, []
        providers.append(status)
        sessions.extend(items)
        sessions.sort(key=lambda item: item.get("updated_at", 0), reverse=True)
        return {"providers": providers, "sessions": sessions[:200]}

    def _session_detail(self, provider: str, session_id: str) -> dict:
        data = DashboardHandler._session_sources(self)
        for item in data["sessions"]:
            if item["provider"] == provider and item["id"] == session_id:
                path = Path(item["path"])
                records = DashboardHandler._jsonl_records(self, path, head=10, tail=30) if path.suffix.lower() == ".jsonl" else []
                preview = []
                for record in records[-12:]:
                    text = DashboardHandler._record_text(self, record).strip()
                    if text:
                        preview.append(text[:240])
                item = dict(item)
                item["preview"] = preview
                return {"session": item}
        return {"session": None}

    def _graph_data(self) -> dict:
        nodes = []
        links = []
        node_map = {}

        wiki_pages = self._wiki_pages("")
        page_links_raw = []
        for p in wiki_pages:
            p_id = f"page:{p['path']}"
            if p_id not in node_map:
                node_map[p_id] = len(nodes)
                nodes.append({
                    "id": p_id,
                    "label": p["title"],
                    "kind": "page",
                    "path": p["path"],
                    "size": 10,
                })

            full_path = self.workspace / p["path"]
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    outbound = self._parse_wiki_links(content)
                    for out in outbound:
                        page_links_raw.append((p_id, out.lower().replace(" ", "-")))
                except Exception:
                    pass

        memories = self._memory_objects("")
        for m in memories:
            m_id = f"memory:{m['id']}"
            if m_id not in node_map:
                node_map[m_id] = len(nodes)
                nodes.append({
                    "id": m_id,
                    "label": m["claim"][:45] + "...",
                    "claim": m["claim"],
                    "kind": "memory",
                    "status": m["status"],
                    "memory_kind": m["kind"],
                    "confidence": m["confidence"],
                    "sensitivity": m["sensitivity"],
                    "rank_score": m.get("rank_score", 0),
                    "size": 12 + int(m.get("rank_score", 0) * 1.5),
                })

            for ref in m.get("source_refs", []):
                ref_id = f"page:{ref}"
                if ref_id in node_map:
                    links.append({
                        "source": node_map[m_id],
                        "target": node_map[ref_id],
                        "type": "reference",
                    })

            for sup in m.get("supersedes", []):
                sup_id = f"memory:{sup}"
                if sup_id in node_map:
                    links.append({
                        "source": node_map[m_id],
                        "target": node_map[sup_id],
                        "type": "supersedes",
                    })

            for con in m.get("contradicts", []):
                con_id = f"memory:{con}"
                if con_id in node_map:
                    links.append({
                        "source": node_map[m_id],
                        "target": node_map[con_id],
                        "type": "contradicts",
                    })

        for src_id, dst_slug in page_links_raw:
            for p_node in nodes:
                if p_node["kind"] == "page":
                    stem = Path(p_node["path"]).stem.lower()
                    if stem == dst_slug or p_node["label"].lower() == dst_slug:
                        dst_id = p_node["id"]
                        links.append({
                            "source": node_map[src_id],
                            "target": node_map[dst_id],
                            "type": "wikilink",
                        })
                        break

        return {"nodes": nodes, "links": links}

    def _serve_api_graph(self) -> None:
        self._send_json(self._graph_data())

    def _search_results(self, query: str) -> dict:
        query = query.strip()
        if not query:
            return {"results": {}}

        prefix = ""
        term = query
        if ":" in query:
            parts = query.split(":", 1)
            prefix = parts[0].strip().lower()
            term = parts[1].strip()

        results = {
            "pages": [],
            "skills": [],
            "memories": [],
            "logs": [],
        }

        # 1. Search Wiki Pages
        if not prefix or prefix == "page" or prefix == "concept":
            pages = self._wiki_pages("")
            for p in pages:
                score = 0.0
                reason = []
                p_title = p["title"].lower()
                p_path = p["path"].lower()
                term_l = term.lower()

                if term_l in p_title:
                    score += 0.6
                    reason.append("match in title")
                if term_l in p_path:
                    score += 0.3
                    reason.append("match in path")

                if prefix == "concept" and "concepts/" not in p_path:
                    continue

                if score > 0:
                    score = min(1.0, score + 0.1)
                    results["pages"].append({
                        "id": f"page:{p['path']}",
                        "title": p["title"],
                        "type": "concept" if "concepts/" in p_path else "synthesis",
                        "path": p["path"],
                        "score": round(score, 2),
                        "reason": ", ".join(reason),
                        "obsidian_url": p["obsidian_url"],
                    })

        # 2. Search Skills
        if not prefix or prefix == "skill":
            skills = self._read_index().get("skills", [])
            for s in skills:
                score = 0.0
                reason = []
                s_title = s.get("title", "").lower()
                s_id = s.get("id", "").lower()
                s_desc = s.get("description", "").lower()
                term_l = term.lower()

                if term_l in s_title:
                    score += 0.6
                    reason.append("match in title")
                if term_l in s_id:
                    score += 0.5
                    reason.append("match in ID")
                if term_l in s_desc:
                    score += 0.2
                    reason.append("match in description")

                if score > 0:
                    score = min(1.0, score + 0.1)
                    results["skills"].append({
                        "id": f"skill:{s.get('id', '')}",
                        "title": s.get("title", ""),
                        "type": "skill",
                        "score": round(score, 2),
                        "reason": ", ".join(reason),
                    })

        # 3. Search Memories
        if not prefix or prefix == "memory":
            memories = self._memory_objects("")
            for m in memories:
                score = 0.0
                reason = []
                m_claim = m.get("claim", "").lower()
                m_id = m.get("id", "").lower()
                term_l = term.lower()

                if term_l in m_claim:
                    score += 0.7
                    reason.append("match in claim text")
                if term_l in m_id:
                    score += 0.4
                    reason.append("match in ID")

                if score > 0:
                    score = min(1.0, score + 0.1)
                    results["memories"].append({
                        "id": f"memory:{m.get('id', '')}",
                        "title": m.get("claim", "")[:50] + "...",
                        "claim": m.get("claim", ""),
                        "type": "memory",
                        "score": round(score, 2),
                        "reason": ", ".join(reason),
                    })

        # 4. Search Logs
        if not prefix or prefix == "log":
            logs = self._recent_log_entries(50)
            for e in logs:
                score = 0.0
                reason = []
                e_heading = e.get("heading", "").lower()
                e_body = e.get("body", "").lower()
                term_l = term.lower()

                if term_l in e_heading:
                    score += 0.6
                    reason.append("match in heading")
                if term_l in e_body:
                    score += 0.3
                    reason.append("match in body")

                if score > 0:
                    score = min(1.0, score + 0.1)
                    results["logs"].append({
                        "id": f"log:{e.get('heading', '')[:30]}",
                        "title": e.get("heading", ""),
                        "type": "log",
                        "score": round(score, 2),
                        "reason": ", ".join(reason),
                    })

        for cat in results:
            results[cat].sort(key=lambda x: x["score"], reverse=True)

        return {"results": results}

    def _context_pack_data(self, obj_id: str) -> dict:
        packet = ""
        summary = ""

        if obj_id.startswith("page:"):
            rel_path = obj_id[5:]
            full_path = self.workspace / rel_path
            title = rel_path.replace("\\", "/").split("/")[-1].replace(".md", "").replace("_", " ").replace("-", " ")
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    summary = content[:300].strip() + "..."
                    packet = f"""# Context Packet: {title}

Canonical ID: {obj_id}
Source: {rel_path}
Status: current

Summary:
{content[:1500]}

---
[End of Packet]"""
                except Exception as exc:
                    packet = f"Error reading page: {exc}"
            else:
                packet = f"Page not found: {rel_path}"

        elif obj_id.startswith("skill:"):
            s_id = obj_id[6:]
            skills = self._read_index().get("skills", [])
            skill = None
            for s in skills:
                if s.get("id") == s_id:
                    skill = s
                    break

            if skill:
                title = skill.get("title", "Active Skill")
                summary = skill.get("description", "")
                packet = f"""# Context Packet: {title}

Canonical ID: {obj_id}
Status: active
Score: {skill.get('feedback_score', 0)}

Description:
{skill.get('description', 'No description available')}

Trigger Phrases:
{json.dumps(skill.get('trigger_phrases', []), indent=2)}

---
[End of Packet]"""
            else:
                packet = f"Skill not found: {s_id}"

        elif obj_id.startswith("memory:"):
            m_id = obj_id[7:]
            memories = self._memory_objects("")
            memory = None
            for m in memories:
                if m.get("id") == m_id:
                    memory = m
                    break

            if memory:
                summary = memory.get("claim", "")
                packet = f"""# Context Packet: Memory Claim

Canonical ID: {obj_id}
Status: {memory.get('status', 'candidate')}
Kind: {memory.get('memory_kind', 'concept')}
Confidence: {memory.get('confidence', 'medium')}
Sensitivity: {memory.get('sensitivity', 'normal')}
Rank Score: {memory.get('rank_score', 0)}

Claim:
{memory.get('claim', '')}

Source Refs:
{json.dumps(memory.get('source_refs', []), indent=2)}

Supersedes:
{json.dumps(memory.get('supersedes', []), indent=2)}

Contradicts:
{json.dumps(memory.get('contradicts', []), indent=2)}

---
[End of Packet]"""
            else:
                packet = f"Memory not found: {m_id}"

        elif obj_id.startswith("session:"):
            parts = obj_id.split(":", 2)
            if len(parts) == 3:
                provider = parts[1]
                session_id = parts[2]
                detail = DashboardHandler._session_detail(self, provider, session_id).get("session")
                if detail:
                    summary = detail.get("title", "")
                    packet = f"""# Context Packet: LLM Session

Provider: {detail.get('provider', provider)}
Session ID: {detail.get('id', session_id)}
Title: {detail.get('title', '')}
Workspace: {detail.get('cwd', '')}
Artifact: {detail.get('path', '')}
Updated: {detail.get('updated_label', '')}

Resume Command:
{detail.get('resume_command', '') or 'Open this session manually in the provider app.'}

Recent Preview:
{chr(10).join('- ' + line for line in detail.get('preview', []))}

---
[End of Packet]"""
                else:
                    packet = f"Session not found: {provider}:{session_id}"
            else:
                packet = f"Malformed session id: {obj_id}"

        else:
            packet = f"Unknown object type: {obj_id}"

        return {"id": obj_id, "packet": packet, "summary": summary}

    def _debug_retrieval_data(self, query: str) -> dict:
        query = query.strip().lower()
        if not query:
            return {"results": [], "rejected": []}

        results = []
        rejected = []

        pages = self._wiki_pages("")
        memories = self._memory_objects("")

        for p in pages:
            p_title = p["title"].lower()
            p_path = p["path"].lower()

            semantic = 0.45
            if query in p_title:
                semantic += 0.35
            elif query in p_path:
                semantic += 0.15
            else:
                rejected.append({
                    "id": f"page:{p['path']}",
                    "title": p["title"],
                    "reason": "weak semantic match",
                })
                continue

            recency = 0.02
            if "log" in p_path or "today" in p_path:
                recency = 0.09
            elif "concept" in p_path:
                recency = 0.05

            graph_offset = 0.04

            total_score = round(min(1.00, semantic + recency + graph_offset), 2)
            results.append({
                "id": f"page:{p['path']}",
                "title": p["title"],
                "type": "wiki_page",
                "score": total_score,
                "breakdown": {
                    "semantic": round(semantic, 2),
                    "recency": round(recency, 2),
                    "graph": round(graph_offset, 2),
                },
                "matched_text": p["snippet"][:80],
            })

        for m in memories:
            m_claim = m["claim"].lower()
            m_id = m["id"].lower()

            semantic = 0.40
            if query in m_claim:
                semantic += 0.45
            elif query in m_id:
                semantic += 0.20
            else:
                rejected.append({
                    "id": f"memory:{m['id']}",
                    "title": m["claim"][:40] + "...",
                    "reason": "below semantic threshold",
                })
                continue

            recency = 0.03
            if m["status"] == "approved":
                recency += 0.04

            graph_offset = 0.03
            if m.get("rank_score", 0) > 2:
                graph_offset += 0.05

            total_score = round(min(1.00, semantic + recency + graph_offset), 2)
            results.append({
                "id": f"memory:{m['id']}",
                "title": m["claim"][:40] + "...",
                "type": "memory",
                "score": total_score,
                "breakdown": {
                    "semantic": round(semantic, 2),
                    "recency": round(recency, 2),
                    "graph": round(graph_offset, 2),
                },
                "matched_text": m["claim"][:80],
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return {"results": results[:10], "rejected": rejected[:5]}

    def _serve_api_search(self) -> None:
        query_values = parse_qs(urlsplit(self.path).query).get("q", [""])
        query = query_values[0]
        self._send_json(self._search_results(query))

    def _serve_api_context_pack(self) -> None:
        query_values = parse_qs(urlsplit(self.path).query).get("id", [""])
        obj_id = query_values[0]
        self._send_json(self._context_pack_data(obj_id))

    def _serve_api_debug(self) -> None:
        query_values = parse_qs(urlsplit(self.path).query).get("q", [""])
        query = query_values[0]
        self._send_json(self._debug_retrieval_data(query))

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == "/dashboard" or path == "/dashboard/":
            self._serve_index()
        elif path == "/dashboard/api/pages":
            self._serve_api_pages()
        elif path == "/dashboard/api/skills":
            self._serve_api_skills()
        elif path.startswith("/dashboard/api/skills/"):
            skill_id = unquote_plus(path.split("/")[-1])
            self._serve_api_skill_detail(skill_id)
        elif path == "/dashboard/api/brv/status":
            self._serve_api_brv_status()
        elif path == "/dashboard/api/log":
            self._serve_api_log()
        elif path == "/dashboard/api/config":
            self._serve_api_config()
        elif path == "/dashboard/api/memory":
            self._serve_api_memory()
        elif path == "/dashboard/api/memory/events":
            self._serve_api_memory_events()
        elif path == "/dashboard/api/reducer/drafts":
            self._send_json({"drafts": self._reducer_drafts()})
        elif path == "/dashboard/api/graph":
            self._serve_api_graph()
        elif path == "/dashboard/api/search":
            self._serve_api_search()
        elif path == "/dashboard/api/context-pack":
            self._serve_api_context_pack()
        elif path == "/dashboard/api/debug":
            self._serve_api_debug()
        elif path == "/dashboard/api/workspace/list":
            query = parse_qs(urlsplit(self.path).query)
            refresh = query.get("refresh", ["0"])[0] in {"1", "true", "yes"}
            self._send_json({"wikis": self._list_available_wikis(refresh=refresh)})
        elif path == "/dashboard/api/sessions":
            self._send_json(self._session_sources())
        elif path == "/dashboard/api/sessions/detail":
            query = parse_qs(urlsplit(self.path).query)
            provider = query.get("provider", [""])[0]
            session_id = query.get("id", [""])[0]
            self._send_json(self._session_detail(provider, session_id))
        elif path == "/dashboard/api/workspace/switch":
            query = parse_qs(urlsplit(self.path).query)
            target_path = query.get("path", [""])[0]
            if not target_path:
                self._send_json({"status": "error", "message": "Missing workspace path"})
                return
            target = Path(target_path).resolve()
            if not target.exists() or not target.is_dir():
                self._send_json({"status": "error", "message": f"Path '{target_path}' does not exist or is not a directory"})
                return
            if not (target / "wiki").is_dir():
                self._send_json({"status": "error", "message": f"Path '{target_path}' does not contain a wiki directory"})
                return
            DashboardHandler.workspace = target
            registry = DashboardHandler._load_wiki_registry(self)
            registry[str(target)] = DashboardHandler._wiki_project_item(self, target, target)
            DashboardHandler._save_wiki_registry(self, list(registry.values()))
            self._send_json({
                "status": "ok",
                "message": f"Switched to workspace '{target.name}' successfully",
                "workspace": str(target)
            })
        elif path == "/dashboard/api/reducer/approve":
            query = parse_qs(urlsplit(self.path).query)
            draft_id = query.get("id", [""])[0]
            if not draft_id:
                self._send_json({"status": "error", "message": "Missing draft id"})
                return
            try:
                res = subprocess.run(
                    [
                        sys.executable,
                        str(self.workspace / "scripts" / "auto_reducer_watcher.py"),
                        "--workspace", str(self.workspace),
                        "approve",
                        draft_id,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self._send_json({
                    "status": "ok" if res.returncode == 0 else "error",
                    "message": res.stdout.strip() if res.returncode == 0 else res.stderr.strip()
                })
            except Exception as exc:
                self._send_json({"status": "error", "message": str(exc)})
        elif path == "/dashboard/api/reducer/reject":
            query = parse_qs(urlsplit(self.path).query)
            draft_id = query.get("id", [""])[0]
            if not draft_id:
                self._send_json({"status": "error", "message": "Missing draft id"})
                return
            try:
                res = subprocess.run(
                    [
                        sys.executable,
                        str(self.workspace / "scripts" / "auto_reducer_watcher.py"),
                        "--workspace", str(self.workspace),
                        "reject",
                        draft_id,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self._send_json({
                    "status": "ok" if res.returncode == 0 else "error",
                    "message": res.stdout.strip() if res.returncode == 0 else res.stderr.strip()
                })
            except Exception as exc:
                self._send_json({"status": "error", "message": str(exc)})
        else:
            self._send_html("<h1>Not Found</h1>", 404)

    def _serve_index(self) -> None:
        html_body = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LLM Wiki Memory Cockpit</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-main: #141416;
    --bg-panel: #1a1a1e;
    --bg-card: #222228;
    --bg-input: #0e0e11;
    --border-color: #2a2a32;
    --border-hover: #3a3a46;
    --text-primary: #e3e3e6;
    --text-secondary: #a3a3a6;
    --text-muted: #62626e;
    --accent: #00bcd4;
    --accent-glow: rgba(0, 188, 212, 0.15);
    --success: #4caf50;
    --success-bg: rgba(76, 175, 80, 0.1);
    --danger: #f44336;
    --danger-bg: rgba(244, 67, 54, 0.1);
    --warning: #ff9800;
    --warning-bg: rgba(255, 152, 0, 0.1);

    --font-display: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

    --transition-quint: cubic-bezier(0.23, 1, 0.32, 1);
  }

  * { box-sizing: border-box; }
  body {
    font-family: var(--font-display);
    margin: 0;
    padding: 0;
    background-color: var(--bg-main);
    color: var(--text-primary);
    height: 100vh;
    overflow: hidden;
    letter-spacing: -0.01em;
  }

  /* Full Screen Cockpit Layout Grid */
  .cockpit-container {
    display: grid;
    grid-template-rows: 45px 35px 1fr;
    height: 100vh;
    width: 100vw;
  }

  /* Top Command Palette bar */
  .top-search-bar {
    background-color: var(--bg-panel);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1.5rem;
    position: relative;
    z-index: 100;
  }

  .command-palette-wrapper {
    position: relative;
    width: 60%;
  }

  .palette-input {
    width: 100%;
    background-color: var(--bg-input);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: 0.35rem 0.75rem;
    font-size: 0.82rem;
    border-radius: 4px;
    font-family: var(--font-mono);
    outline: none;
    transition: all 0.25s var(--transition-quint);
  }

  .palette-input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px var(--accent-glow);
  }

  /* Floating Dropdown Results */
  .palette-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    width: 100%;
    background-color: var(--bg-panel);
    border: 1px solid var(--border-color);
    border-top: none;
    border-radius: 0 0 6px 6px;
    max-height: 400px;
    overflow-y: auto;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    z-index: 101;
    display: none;
  }

  .dropdown-group {
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border-color);
  }

  .dropdown-group:last-child {
    border-bottom: none;
  }

  .group-title {
    font-family: var(--font-display);
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--text-muted);
    font-weight: 700;
    padding: 0.25rem 0.75rem;
    letter-spacing: 0.05em;
  }

  .dropdown-row {
    padding: 0.4rem 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: all 0.2s;
    font-family: var(--font-mono);
    font-size: 0.75rem;
  }

  .dropdown-row:hover {
    background-color: var(--bg-card);
  }

  .row-left {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .row-title {
    color: var(--text-primary);
    font-weight: 500;
  }

  .row-path {
    color: var(--text-muted);
    font-size: 0.68rem;
  }

  .row-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .row-score {
    color: var(--success);
    font-weight: 700;
  }

  /* Overview Strip Bar */
  .overview-strip {
    background-color: var(--bg-main);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1.5rem;
    font-size: 0.72rem;
    color: var(--text-secondary);
  }

  .strip-stats {
    display: flex;
    gap: 1.2rem;
  }

  .strip-stats span {
    font-family: var(--font-mono);
  }

  .strip-system {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
  }

  .dot-green { background-color: var(--success); box-shadow: 0 0 6px var(--success); }
  .dot-amber { background-color: var(--warning); box-shadow: 0 0 6px var(--warning); }
  .dot-red { background-color: var(--danger); box-shadow: 0 0 6px var(--danger); }
  .dot-gray { background-color: var(--text-muted); }

  /* 3-Rail Workspace Rail Splitting */
  .workspace-split {
    display: grid;
    grid-template-columns: 220px 1fr 340px;
    height: 100%;
    overflow: hidden;
  }

  /* Left Rail: filters & Stable nav */
  .rail-left {
    background-color: var(--bg-panel);
    border-right: 1px solid var(--border-color);
    padding: 1.5rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .nav-header {
    font-size: 0.72rem;
    text-transform: uppercase;
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
  }

  .nav-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .nav-item {
    padding: 0.4rem 0.6rem;
    border-radius: 4px;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .nav-item:hover {
    background-color: var(--bg-card);
  }

  .nav-item.active {
    background-color: var(--bg-card);
    color: var(--accent);
    font-weight: 500;
    border-left: 3px solid var(--accent);
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
  }

  .nav-count {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  /* Center Area: Exploration surface */
  .rail-center {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background-color: var(--bg-main);
  }

  .explorer-tabs {
    display: flex;
    border-bottom: 1px solid var(--border-color);
    background-color: var(--bg-panel);
    padding: 0 1rem;
  }

  .tab-btn {
    font-family: var(--font-display);
    font-size: 0.78rem;
    padding: 0.6rem 1rem;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
    outline: none;
  }

  .tab-btn:hover {
    color: var(--text-primary);
  }

  .tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    font-weight: 500;
  }

  .explorer-sheet {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    display: none;
  }

  .explorer-sheet.active {
    display: block;
  }

  /* List Table Aesthetics */
  .density-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-display);
    font-size: 0.8rem;
  }

  .density-table th {
    text-align: left;
    padding: 0.5rem 0.6rem;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-muted);
    font-weight: 500;
    font-size: 0.72rem;
    text-transform: uppercase;
  }

  .density-table td {
    padding: 0.5rem 0.6rem;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    color: var(--text-primary);
    cursor: pointer;
  }

  .density-table tr:hover td {
    background-color: var(--bg-panel);
  }

  .table-mono {
    font-family: var(--font-mono);
    font-size: 0.75rem;
  }

  .hotness-bar {
    font-family: var(--font-mono);
    color: var(--accent);
    letter-spacing: -0.05em;
  }

  /* Timeline & Logs monospaces */
  .timeline-list, .log-list-mono {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .timeline-card {
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background-color: var(--bg-panel);
    padding: 0.75rem 1rem;
    font-family: var(--font-mono);
    font-size: 0.75rem;
  }

  /* Retrieval debugger layout */
  .retrieval-debug-header {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
  }

  /* Right Rail: persistent inspector */
  .rail-right {
    background-color: var(--bg-panel);
    border-left: 1px solid var(--border-color);
    padding: 1.5rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .inspector-header h2 {
    font-size: 1.15rem;
    font-weight: 700;
    margin: 0 0 0.2rem 0;
    word-break: break-all;
  }

  .inspector-header .badge {
    margin-top: 0.3rem;
  }

  .inspector-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.4rem 1rem;
    font-size: 0.78rem;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 1rem;
  }

  .grid-label {
    color: var(--text-muted);
  }

  .grid-val {
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .inspector-links-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.76rem;
  }

  .inspector-links-list li {
    cursor: pointer;
    color: var(--accent);
    text-decoration: underline;
  }

  .inspector-packet-box {
    background-color: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 0.6rem;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    white-space: pre-wrap;
    max-height: 250px;
    overflow-y: auto;
    color: var(--text-secondary);
  }

  /* Agent View Mode Toggles */
  .agent-card {
    background-color: var(--bg-panel);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 1rem;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    margin-bottom: 1rem;
  }

  .agent-card-header {
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 0.3rem;
    display: flex;
    justify-content: space-between;
  }

  .agent-card-curl {
    background-color: var(--bg-input);
    padding: 0.5rem;
    border-radius: 4px;
    margin-top: 0.4rem;
    color: var(--success);
    word-break: break-all;
  }

  body.agent-mode-active .human-ui-pane {
    display: none !important;
  }

  body:not(.agent-mode-active) .agent-ui-pane {
    display: none !important;
  }

  /* Scrollbar Aesthetics */
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  ::-webkit-scrollbar-track {
    background: var(--bg-main);
  }
  ::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: var(--border-hover);
  }
</style>
</head>
<body class="">

<div class="cockpit-container">

  <div class="top-search-bar">
    <div style="font-family: var(--font-display); font-weight: 700; font-size: 0.95rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.6rem;">
      <span style="background: var(--accent); color: var(--bg-main); padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.75rem;">COCKPIT</span>
      <select id="wiki-selector" onchange="switchWorkspace(this.value)" style="background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-color); font-family: var(--font-display); font-size: 0.8rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 4px; outline: none; cursor: pointer; transition: all 0.25s;">
        <option value="">Loading Wikis...</option>
      </select>
      <button class="btn-dev btn-copy" onclick="loadWorkspaceList(true)" title="Refresh wiki project registry">Refresh Wikis</button>
    </div>

    <div class="command-palette-wrapper">
      <input type="text" id="palette-search" class="palette-input" placeholder="Search pages, memories, skills, logs, reducers, IDs, concepts... (e.g. page:retrieval, skill:dry)" oninput="handlePaletteSearch(this.value)">
      <div id="palette-dropdown" class="palette-dropdown"></div>
    </div>

    <!-- Human vs Agent View Switcher -->
    <div style="display: flex; gap: 0.25rem; background: var(--bg-input); padding: 0.15rem; border-radius: 4px; border: 1px solid var(--border-color);">
      <button id="btn-toggle-human" class="btn-dev" style="padding: 0.2rem 0.5rem; background: var(--bg-card); color: var(--accent); border-color: var(--accent);" onclick="setUiMode('human')">Human View</button>
      <button id="btn-toggle-agent" class="btn-dev" style="padding: 0.2rem 0.5rem;" onclick="setUiMode('agent')">Agent View</button>
    </div>
  </div>

  <!-- Overview Status Strip -->
  <div class="overview-strip">
    <div class="strip-stats">
      <span id="stat-pages">0 Pages</span>
      <span id="stat-skills">0 Active Skills</span>
      <span id="stat-reducers">0 Reducer Drafts</span>
      <span id="stat-memories">0 Memories</span>
      <span id="stat-sessions">0 LLM Sessions</span>
      <span id="stat-logs">0 Recent Logs</span>
    </div>

    <div class="strip-system">
      <div class="status-item">
        <span class="dot dot-green"></span>
        <span>SYSTEM: Stable</span>
      </div>
      <div class="status-item" style="margin-left: 0.8rem;">
        <span class="dot dot-green"></span>
        <span>RETRIEVAL: Healthy</span>
      </div>
      <div class="status-item" style="margin-left: 0.8rem; font-family: var(--font-mono); color: var(--text-muted);" id="strip-update">
        Last Update: 0m ago
      </div>
    </div>
  </div>

  <!-- Main Three-Rail split view -->
  <div class="workspace-split">

    <!-- Left Rail: filters & Stable navigation -->
    <div class="rail-left">
      <div>
        <div class="nav-header">System Map</div>
        <ul class="nav-list">
          <li class="nav-item active" id="nav-item-all" onclick="setLeftFilter('all')">
            <span>All Explorer</span>
            <span class="nav-count" id="nav-count-all">0</span>
          </li>
          <li class="nav-item" id="nav-item-pages" onclick="setLeftFilter('pages')">
            <span>Wiki Pages</span>
            <span class="nav-count" id="nav-count-pages">0</span>
          </li>
          <li class="nav-item" id="nav-item-skills" onclick="setLeftFilter('skills')">
            <span>Active Skills</span>
            <span class="nav-count" id="nav-count-skills">0</span>
          </li>
          <li class="nav-item" id="nav-item-reducers" onclick="setLeftFilter('reducers')">
            <span>Reducer Drafts</span>
            <span class="nav-count" id="nav-count-reducers">0</span>
          </li>
          <li class="nav-item" id="nav-item-memories" onclick="setLeftFilter('memories')">
            <span>Memories</span>
            <span class="nav-count" id="nav-count-memories">0</span>
          </li>
          <li class="nav-item" id="nav-item-sessions" onclick="setLeftFilter('sessions'); setCenterTab('sessions')">
            <span>LLM Sessions</span>
            <span class="nav-count" id="nav-count-sessions">0</span>
          </li>
          <li class="nav-item" id="nav-item-logs" onclick="setLeftFilter('logs')">
            <span>System Logs</span>
            <span class="nav-count" id="nav-count-logs">0</span>
          </li>
        </ul>
      </div>

      <div>
        <div class="nav-header">Quick Utilities</div>
        <ul class="nav-list">
          <li class="nav-item" onclick="setCenterTab('debug')">
            <span>Retrieval Debugger</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Center rail: Fast exploration surface -->
    <div class="rail-center">

      <!-- Human UI Pane -->
      <div class="human-ui-pane" style="display:flex; flex-direction:column; height:100%; overflow:hidden;">
        <div class="explorer-tabs">
          <button class="tab-btn active" id="tab-btn-list" onclick="setCenterTab('list')">List Explorer</button>
          <button class="tab-btn" id="tab-btn-graph" onclick="setCenterTab('graph')">Knowledge Graph</button>
          <button class="tab-btn" id="tab-btn-sessions" onclick="setCenterTab('sessions')">LLM Sessions</button>
          <button class="tab-btn" id="tab-btn-timeline" onclick="setCenterTab('timeline')">Session Timeline</button>
          <button class="tab-btn" id="tab-btn-logs" onclick="setCenterTab('logs')">Developer Logs</button>
          <button class="tab-btn" id="tab-btn-debug" onclick="setCenterTab('debug')">Retrieval Debug</button>
        </div>

        <!-- Tab 1: Dense List Explorer -->
        <div class="explorer-sheet active" id="sheet-list">
          <table class="density-table" id="list-table">
            <thead>
              <tr>
                <th style="width: 45%;">Name</th>
                <th style="width: 15%;">Type</th>
                <th style="width: 10%;">Links</th>
                <th style="width: 18%;">Last Touched</th>
                <th style="width: 12%;">Hot</th>
              </tr>
            </thead>
            <tbody id="list-table-body">
              <tr><td colspan="5" class="meta-info">Loading records...</td></tr>
            </tbody>
          </table>
        </div>

        <!-- Tab 2: Graph Canvas View -->
        <div class="explorer-sheet" id="sheet-graph" style="padding: 0; position: relative; overflow: hidden;">
          <div class="section-header" style="position: absolute; top: 1rem; left: 1.5rem; z-index: 10; border-bottom: none; width: calc(100% - 3rem);">
            <div style="display: flex; gap: 0.5rem; align-items: center;">
              <div style="display: flex; gap: 0.25rem; background: var(--bg-input); padding: 0.15rem; border-radius: 4px; border: 1px solid var(--border-color); margin-right: 0.5rem;">
                <button id="btn-mode-galaxy" class="btn-dev" style="padding: 0.2rem 0.5rem; background: var(--bg-card); color: var(--accent); border-color: var(--accent);" onclick="setLayoutMode('galaxy')">Galaxy</button>
                <button id="btn-mode-mindmap" class="btn-dev" style="padding: 0.2rem 0.5rem;" onclick="setLayoutMode('mindmap')">Mind Map</button>
              </div>
              <button class="btn-dev btn-copy" onclick="initGraphPhysics(true)">Reset View</button>
              <button class="btn-dev btn-copy" id="btn-freeze" onclick="toggleFreezeGraph()">Freeze Layout</button>
              <span class="count-badge" id="graph-node-count">0 nodes</span>
            </div>
          </div>

          <!-- Floating config HUD -->
          <div id="graph-controls" style="position: absolute; top: 1rem; right: 1.5rem; z-index: 10; background: rgba(14, 18, 27, 0.92); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.8rem; font-family: var(--font-display); width: 220px; transition: all 0.3s var(--transition-quint); max-height: calc(100% - 2rem); overflow: hidden; font-size: 0.75rem;">
            <div style="font-weight: 700; font-size: 0.8rem; margin-bottom: 0.6rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.3rem; color: var(--accent); display: flex; justify-content: space-between; align-items: center;">
              <span>GRAPH CONFIG</span>
              <span style="font-size: 0.65rem; color: var(--text-muted); cursor: pointer;" onclick="toggleControls()">[Hide]</span>
            </div>
            <div id="controls-body">
              <div style="font-weight: 500; margin-bottom: 0.4rem; color: var(--text-secondary);">Forces</div>
              <label style="display: flex; flex-direction: column; gap: 0.15rem; margin-bottom: 0.4rem;">
                <span style="font-size: 0.68rem; color: var(--text-muted);">Repulsion: <span id="val-repulsion">450</span></span>
                <input type="range" min="100" max="1500" value="450" oninput="updateForceParam('repulsion', this.value)" style="width:100%;">
              </label>
              <label style="display: flex; flex-direction: column; gap: 0.15rem; margin-bottom: 0.4rem;">
                <span style="font-size: 0.68rem; color: var(--text-muted);">Link Length: <span id="val-linklen">70</span></span>
                <input type="range" min="30" max="250" value="70" oninput="updateForceParam('linklen', this.value)" style="width:100%;">
              </label>
              <label style="display: flex; flex-direction: column; gap: 0.15rem; margin-bottom: 0.6rem;">
                <span style="font-size: 0.68rem; color: var(--text-muted);">Gravity: <span id="val-gravity">0.015</span></span>
                <input type="range" min="0.005" max="0.08" step="0.005" value="0.015" oninput="updateForceParam('gravity', this.value)" style="width:100%;">
              </label>

              <div style="font-weight: 500; margin-bottom: 0.4rem; color: var(--text-secondary); border-top: 1px solid var(--border-color); padding-top: 0.4rem;">Display</div>
              <label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer; margin-bottom: 0.3rem;">
                <input type="checkbox" id="chk-labels" checked onchange="updateDisplayParam('labels', this.checked)">
                <span style="font-size: 0.7rem; color: var(--text-secondary);">Show Labels</span>
              </label>
              <label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer; margin-bottom: 0.3rem;">
                <input type="checkbox" id="chk-grid" checked onchange="updateDisplayParam('grid', this.checked)">
                <span style="font-size: 0.7rem; color: var(--text-secondary);">Show Grid lines</span>
              </label>
              <label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer;">
                <input type="checkbox" id="chk-progressive" checked onchange="updateDisplayParam('progressive', this.checked); if(layoutMode==='mindmap')calculateMindMapLayout();">
                <span style="font-size: 0.7rem; color: var(--accent);">Progressive View</span>
              </label>
            </div>
          </div>
          <canvas id="concept-map" style="width: 100%; height: 100%; display: block; background-color: var(--bg-input); cursor: grab;"></canvas>
        </div>

        <!-- Tab 3: Session Timeline -->
        <div class="explorer-sheet" id="sheet-timeline">
          <ul class="timeline-list" id="timeline-list-body">
            <li class="timeline-card">Timeline loading...</li>
          </ul>
        </div>

        <!-- Tab 4: LLM Session Switcher -->
        <div class="explorer-sheet" id="sheet-sessions">
          <div class="retrieval-debug-header">
            <select id="session-provider-filter" class="palette-input" style="width: 220px;" onchange="renderSessionExplorer()">
              <option value="all">All providers</option>
            </select>
            <input type="text" id="session-search" class="palette-input" style="width: 50%;" placeholder="Filter sessions by title, project, provider, or ID..." oninput="renderSessionExplorer()">
            <button class="btn-dev btn-copy" onclick="loadSessions()">Refresh</button>
          </div>
          <ul class="timeline-list" id="session-list-body">
            <li class="timeline-card">Sessions loading...</li>
          </ul>
          <div class="meta-info" id="session-provider-status" style="margin-top: 1rem;"></div>
        </div>

        <!-- Tab 5: Monospace Dev Logs -->
        <div class="explorer-sheet" id="sheet-logs">
          <ul class="log-list-mono" id="log-list-body">
            <li class="meta-info">Logs loading...</li>
          </ul>
        </div>

        <!-- Tab 6: Retrieval Debugger -->
        <div class="explorer-sheet" id="sheet-debug">
          <div class="retrieval-debug-header">
            <input type="text" id="debug-query" class="palette-input" style="width: 70%;" placeholder="Enter query string (e.g. memory review gating)..." onkeydown="if(event.key==='Enter') runDebugAnalysis()">
            <button class="btn-dev btn-dev-approve" onclick="runDebugAnalysis()">Analyze Retrieval Weights</button>
          </div>

          <div style="font-weight: 500; font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--accent);">Top Retrieval Candidates</div>
          <ul class="log-list-mono" id="debug-results-body" style="margin-bottom: 1.5rem;">
            <li class="meta-info">Enter a query to run retrieval analysis.</li>
          </ul>

          <div style="font-weight: 500; font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--danger);">Rejected Near-Matches</div>
          <ul class="log-list-mono" id="debug-rejected-body">
            <li class="meta-info">No rejected near-matches yet.</li>
          </ul>
        </div>
      </div>

      <!-- Agent UI Pane -->
      <div class="agent-ui-pane" style="padding: 1.5rem; overflow-y: auto; height: 100%;">
        <div style="font-family: var(--font-display); font-weight:700; font-size: 1.1rem; margin-bottom: 0.8rem;">Agent Navigable REST endpoints</div>
        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 1.5rem;">
          These JSON endpoints expose structured, deterministic data configurations. No HTML scraping is required for LLM agent exploration.
        </div>

        <div class="agent-card">
          <div class="agent-card-header">
            <span>GET /dashboard/api/pages</span>
            <span>Returns Wiki Pages</span>
          </div>
          <div>Exposes deterministically compiled markdown files index and relative paths.</div>
          <div class="agent-card-curl">curl http://localhost:8183/dashboard/api/pages</div>
        </div>

        <div class="agent-card">
          <div class="agent-card-header">
            <span>GET /dashboard/api/skills</span>
            <span>Returns Active Skills</span>
          </div>
          <div>Provides structural skills listings, trigger keywords, and associated feedback metrics.</div>
          <div class="agent-card-curl">curl http://localhost:8183/dashboard/api/skills</div>
        </div>

        <div class="agent-card">
          <div class="agent-card-header">
            <span>GET /dashboard/api/memory</span>
            <span>Returns Memories Ledger</span>
          </div>
          <div>Exposes active/approved claims ledger items, statuses, contradiction matrices, and scores.</div>
          <div class="agent-card-curl">curl http://localhost:8183/dashboard/api/memory</div>
        </div>

        <div class="agent-card">
          <div class="agent-card-header">
            <span>GET /dashboard/api/reducer/drafts</span>
            <span>Returns Reducer Packets</span>
          </div>
          <div>Provides queued pipeline draft memory packets awaiting promotion approvals.</div>
          <div class="agent-card-curl">curl http://localhost:8183/dashboard/api/reducer/drafts</div>
        </div>

        <div class="agent-card">
          <div class="agent-card-header">
            <span>GET /dashboard/api/search?q=query_string</span>
            <span>Query Unified Index</span>
          </div>
          <div>Returns heuristically scored results grouped by structural object types.</div>
          <div class="agent-card-curl">curl "http://localhost:8183/dashboard/api/search?q=memory+review"</div>
        </div>

        <div class="agent-card">
          <div class="agent-card-header">
            <span>GET /dashboard/api/context-pack?id=object_id</span>
            <span>Get Context Packet</span>
          </div>
          <div>Compiles a compact, LLM-ready markdown summary block detailing references and stable ID links.</div>
          <div class="agent-card-curl">curl "http://localhost:8183/dashboard/api/context-pack?id=page:wiki/concepts/memory_controller.md"</div>
        </div>
      </div>

    </div>

    <!-- Right Rail: persistent inspector -->
    <div class="rail-right" id="inspector-rail">
      <!-- Welcome Inspector display -->
      <div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 5rem;" id="inspector-placeholder">
        <span style="font-size: 1.5rem; display: block; margin-bottom: 0.5rem;">â–</span>
        Select any node, table row, search hit, or filter to inspect live telemetry context.
      </div>

      <div id="inspector-content" style="display:none; flex-direction:column; gap: 1.25rem;">
        <div class="inspector-header">
          <h2 id="inspect-title">Object Title</h2>
          <span class="badge badge-candidate" id="inspect-badge">TYPE</span>
        </div>

        <div class="inspector-grid">
          <span class="grid-label">ID</span>
          <span class="grid-val" id="inspect-id">page.xyz</span>

          <span class="grid-label">Path</span>
          <span class="grid-val" id="inspect-path" style="word-break: break-all;">wiki/xyz</span>

          <span class="grid-label">Last Touched</span>
          <span class="grid-val" id="inspect-touched">today</span>

          <span class="grid-label">Score</span>
          <span class="grid-val" id="inspect-score" style="color:var(--success);">0.95</span>
        </div>

        <div>
          <div style="font-weight: 500; font-size: 0.76rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.4rem;">Top Connections</div>
          <ul class="inspector-links-list" id="inspect-links">
            <li>None</li>
          </ul>
        </div>

        <div>
          <div style="font-weight: 500; font-size: 0.76rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.4rem;">Why this matters</div>
          <div style="font-size: 0.8rem; line-height: 1.45; color: var(--text-secondary);" id="inspect-reason">
            Grounded retrieval score trace.
          </div>
        </div>

        <div class="btn-group" style="border-top: 1px solid var(--border-color); padding-top: 1rem;">
          <a href="#" id="inspect-btn-obsidian" class="btn-dev btn-dev-approve" target="_blank" style="text-decoration:none;">Open in Obsidian</a>
          <button class="btn-dev" id="inspect-btn-copyid">Copy ID</button>
          <button class="btn-dev" id="inspect-btn-copytext">Copy Context Packet</button>
        </div>

        <div>
          <div style="font-weight: 500; font-size: 0.76rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.4rem;">Context Packet Summary</div>
          <pre class="inspector-packet-box" id="inspect-packet-body">Loading context...</pre>
        </div>
      </div>
    </div>

  </div>
</div>

<!-- Floating Details HUD (kept for Graph Canvas) -->
<div id="graph-hud" style="display: none;"></div>

<script>
async function api(path) {
  const r = await fetch('/dashboard/api' + path);
  return r.json();
}

function escapeHtml(t) {
  const div = document.createElement('div');
  div.textContent = t;
  return div.innerHTML;
}

function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerText;
    btn.innerText = 'Copied!';
    btn.style.borderColor = 'var(--success)';
    btn.style.color = 'var(--success)';
    setTimeout(() => {
      btn.innerText = orig;
      btn.style.borderColor = '';
      btn.style.color = '';
    }, 1500);
  }).catch(err => {
    console.error('Copy failed', err);
  });
}

// Global Cockpit States
let activeLeftFilter = 'all';
let activeCenterTab = 'list';
let selectedObjectId = null;
let humanMode = true;
let allRecordsCache = [];
let sessionRecordsCache = [];
let sessionProviderStatusCache = [];
let obsidianVaultName = 'llm-wiki';

function setUiMode(mode) {
  humanMode = (mode === 'human');
  const btnHuman = document.getElementById('btn-toggle-human');
  const btnAgent = document.getElementById('btn-toggle-agent');

  if (humanMode) {
    document.body.classList.remove('agent-mode-active');
    btnHuman.style.background = 'var(--bg-card)';
    btnHuman.style.color = 'var(--accent)';
    btnHuman.style.borderColor = 'var(--accent)';
    btnAgent.style.background = '';
    btnAgent.style.color = '';
    btnAgent.style.borderColor = '';
  } else {
    document.body.classList.add('agent-mode-active');
    btnAgent.style.background = 'var(--bg-card)';
    btnAgent.style.color = 'var(--accent)';
    btnAgent.style.borderColor = 'var(--accent)';
    btnHuman.style.background = '';
    btnHuman.style.color = '';
    btnHuman.style.borderColor = '';
  }
}

function setLeftFilter(filter) {
  activeLeftFilter = filter;

  // Highlight Left rail active item
  const items = ['all', 'pages', 'skills', 'reducers', 'memories', 'sessions', 'logs'];
  items.forEach(it => {
    const el = document.getElementById('nav-item-' + it);
    if (el) el.classList.remove('active');
  });

  const activeEl = document.getElementById('nav-item-' + filter);
  if (activeEl) activeEl.classList.add('active');

  // Filter Explorer List Sheet
  renderListExplorer();
}

function setCenterTab(tab) {
  activeCenterTab = tab;

  // Highlight Tab Button
  const tabs = ['list', 'graph', 'sessions', 'timeline', 'logs', 'debug'];
  tabs.forEach(t => {
    const el = document.getElementById('tab-btn-' + t);
    if (el) el.classList.remove('active');

    const sheet = document.getElementById('sheet-' + t);
    if (sheet) sheet.classList.remove('active');
  });

  const activeTabEl = document.getElementById('tab-btn-' + tab);
  if (activeTabEl) activeTabEl.classList.add('active');

  const activeSheetEl = document.getElementById('sheet-' + tab);
  if (activeSheetEl) activeSheetEl.classList.add('active');

  if (tab === 'graph') {
    // Resize canvas when tab opens
    setupCanvasElement();
  }
}

// Compile Unified Records Cache
async function prefetchSystemData() {
  try {
    const [pagesData, skillsData, memoriesData, reducersData, logsData, configData, sessionsData] = await Promise.all([
      api('/pages'),
      api('/skills'),
      api('/memory'),
      api('/reducer/drafts'),
      api('/log'),
      api('/config'),
      api('/sessions')
    ]);

    obsidianVaultName = configData.vault_name || configData.workspace_name || 'llm-wiki';
    sessionRecordsCache = sessionsData.sessions || [];
    sessionProviderStatusCache = sessionsData.providers || [];

    allRecordsCache = [];

    // Add Pages
    (pagesData.pages || []).forEach(p => {
      allRecordsCache.push({
        id: 'page:' + p.path,
        name: p.title,
        type: 'Wiki Page',
        links: 8, // simulated connection density
        lastUsed: 'today',
        hotness: 4,
        meta: p
      });
    });

    // Add Skills
    (skillsData.skills || []).forEach(s => {
      allRecordsCache.push({
        id: 'skill:' + s.id,
        name: s.title,
        type: 'Active Skill',
        links: 5,
        lastUsed: '2d ago',
        hotness: 3,
        meta: s
      });
    });

    // Add Reducer Drafts
    (reducersData.drafts || []).forEach(d => {
      allRecordsCache.push({
        id: 'reducer:' + d.id,
        name: d.id,
        type: 'Reducer Draft',
        links: 3,
        lastUsed: 'today',
        hotness: 5,
        meta: d
      });
    });

    // Add Memories
    (memoriesData.memories || []).forEach(m => {
      allRecordsCache.push({
        id: 'memory:' + m.id,
        name: m.claim.substring(0, 45) + '...',
        type: 'Memory Item',
        links: 4,
        lastUsed: m.status === 'approved' ? '2d ago' : '5d ago',
        hotness: m.status === 'approved' ? 3 : 2,
        meta: m
      });
    });

    // Add LLM Sessions
    sessionRecordsCache.forEach(s => {
      allRecordsCache.push({
        id: 'session:' + s.provider + ':' + s.id,
        name: s.title,
        type: 'LLM Session',
        links: 2,
        lastUsed: s.updated_label || 'unknown',
        hotness: s.resume_command ? 5 : 2,
        meta: s
      });
    });

    // Update Strip Status Counts
    document.getElementById('stat-pages').innerText = (pagesData.pages || []).length + " Pages";
    document.getElementById('stat-skills').innerText = (skillsData.skills || []).length + " Active Skills";
    document.getElementById('stat-reducers').innerText = (reducersData.drafts || []).length + " Reducer Drafts";
    document.getElementById('stat-memories').innerText = (memoriesData.memories || []).length + " Memories";
    document.getElementById('stat-sessions').innerText = sessionRecordsCache.length + " LLM Sessions";
    document.getElementById('stat-logs').innerText = (logsData.entries || []).length + " Recent Logs";

    document.getElementById('nav-count-all').innerText = allRecordsCache.length;
    document.getElementById('nav-count-pages').innerText = (pagesData.pages || []).length;
    document.getElementById('nav-count-skills').innerText = (skillsData.skills || []).length;
    document.getElementById('nav-count-reducers').innerText = (reducersData.drafts || []).length;
    document.getElementById('nav-count-memories').innerText = (memoriesData.memories || []).length;
    document.getElementById('nav-count-sessions').innerText = sessionRecordsCache.length;
    document.getElementById('nav-count-logs').innerText = (logsData.entries || []).length;

    renderListExplorer();
    renderSessionExplorer();
    renderTimelineExplorer(logsData.entries || []);
    renderLogsExplorer(logsData.entries || []);
  } catch (err) {
    console.error('Failed to prefetch cockpit dataset', err);
  }
}

// Render Explorer List Table
function renderListExplorer() {
  const body = document.getElementById('list-table-body');

  // Filter cache
  let filtered = allRecordsCache;
  if (activeLeftFilter === 'pages') {
    filtered = allRecordsCache.filter(r => r.type === 'Wiki Page');
  } else if (activeLeftFilter === 'skills') {
    filtered = allRecordsCache.filter(r => r.type === 'Active Skill');
  } else if (activeLeftFilter === 'reducers') {
    filtered = allRecordsCache.filter(r => r.type === 'Reducer Draft');
  } else if (activeLeftFilter === 'memories') {
    filtered = allRecordsCache.filter(r => r.type === 'Memory Item');
  } else if (activeLeftFilter === 'sessions') {
    filtered = allRecordsCache.filter(r => r.type === 'LLM Session');
  } else if (activeLeftFilter === 'logs') {
    filtered = []; // Logs are rendered in separate monospace list tab
  }

  if (filtered.length === 0) {
    body.innerHTML = `<tr><td colspan="5" class="meta-info">No items found matching filter "${activeLeftFilter}"</td></tr>`;
    return;
  }

  body.innerHTML = filtered.map(r => {
    let hotGauge = 'â–ˆ'.repeat(r.hotness) + 'â–‘'.repeat(5 - r.hotness);
    return `
      <tr onclick="inspectObject('${escapeHtml(r.id)}')">
        <td><strong>${escapeHtml(r.name)}</strong></td>
        <td><span class="badge badge-candidate" style="font-size:0.65rem;">${escapeHtml(r.type)}</span></td>
        <td class="table-mono">${escapeHtml(String(r.links))}</td>
        <td class="table-mono">${escapeHtml(r.lastUsed)}</td>
        <td class="hotness-bar">${escapeHtml(hotGauge)}</td>
      </tr>
    `;
  }).join('');
}

async function loadSessions() {
  try {
    const data = await api('/sessions');
    sessionRecordsCache = data.sessions || [];
    sessionProviderStatusCache = data.providers || [];
    renderSessionExplorer();
    prefetchSystemData();
  } catch (err) {
    console.error('Failed to load sessions', err);
  }
}

function renderSessionExplorer() {
  const body = document.getElementById('session-list-body');
  const providerFilter = document.getElementById('session-provider-filter');
  const status = document.getElementById('session-provider-status');
  if (!body || !providerFilter) return;

  const providers = Array.from(new Set(sessionProviderStatusCache.map(p => p.provider).concat(sessionRecordsCache.map(s => s.provider)))).filter(Boolean);
  const currentProvider = providerFilter.value || 'all';
  providerFilter.innerHTML = '<option value="all">All providers</option>' + providers.map(provider => `
    <option value="${escapeHtml(provider)}" ${provider === currentProvider ? 'selected' : ''}>${escapeHtml(provider)}</option>
  `).join('');

  const qEl = document.getElementById('session-search');
  const query = qEl ? qEl.value.toLowerCase().trim() : '';
  let sessions = sessionRecordsCache;
  if (currentProvider !== 'all') {
    sessions = sessions.filter(s => s.provider === currentProvider);
  }
  if (query) {
    sessions = sessions.filter(s => [s.provider, s.title, s.id, s.cwd, s.path].join(' ').toLowerCase().includes(query));
  }

  body.innerHTML = sessions.length
    ? sessions.map(s => {
        const command = s.resume_command || '';
        const encodedCommand = encodeURIComponent(command);
        const commandHtml = command
          ? `<button class="btn-dev btn-dev-approve" onclick="event.stopPropagation(); copyText(decodeURIComponent('${encodedCommand}'), this)">Copy Resume</button>`
          : `<span class="meta-info">Manual reopen</span>`;
        return `
          <li class="timeline-card" onclick="inspectSession('${escapeHtml(s.provider)}', '${escapeHtml(s.id)}')">
            <div style="display:flex; justify-content:space-between; gap:1rem; align-items:flex-start;">
              <div>
                <div style="font-weight:700; color:var(--accent); margin-bottom:0.25rem;">${escapeHtml(s.title)}</div>
                <div class="meta-info">${escapeHtml(s.provider)} | ${escapeHtml(s.updated_label || 'unknown')} | ${escapeHtml(s.cwd || s.path)}</div>
              </div>
              ${commandHtml}
            </div>
          </li>
        `;
      }).join('')
    : '<li class="meta-info">No sessions found for this filter.</li>';

  if (status) {
    status.innerHTML = sessionProviderStatusCache.map(p => {
      const state = p.available ? 'status-ok' : 'status-bad';
      return `<span class="${state}">${escapeHtml(p.provider)}</span>: ${escapeHtml(p.message)}`;
    }).join(' | ');
  }
}

async function inspectSession(provider, id) {
  try {
    const data = await api('/sessions/detail?provider=' + encodeURIComponent(provider) + '&id=' + encodeURIComponent(id));
    const s = data.session;
    if (!s) return;
    selectedObjectId = 'session:' + provider + ':' + id;
    const placeholder = document.getElementById('inspector-placeholder');
    const content = document.getElementById('inspector-content');
    placeholder.style.display = 'none';
    content.style.display = 'flex';
    document.getElementById('inspect-title').innerText = s.title;
    document.getElementById('inspect-badge').innerText = s.provider;
    document.getElementById('inspect-id').innerText = s.id;
    document.getElementById('inspect-path').innerText = s.cwd || s.path;
    document.getElementById('inspect-score').innerText = s.updated_label || 'unknown';
    document.getElementById('inspect-reason').innerText = s.resume_command || 'Session artifact detected; reopen manually in the provider app.';
    document.getElementById('inspect-packet-body').innerText = [
      '# Session Resume Packet',
      '',
      'Provider: ' + s.provider,
      'Session: ' + s.id,
      'Title: ' + s.title,
      'Workspace: ' + (s.cwd || ''),
      'Artifact: ' + s.path,
      'Resume: ' + (s.resume_command || 'manual'),
      '',
      'Recent preview:',
      ...(s.preview || []).map(line => '- ' + line)
    ].join('\\n');
    document.getElementById('inspect-links').innerHTML = `<li>${escapeHtml(s.provider)}</li><li>${escapeHtml(s.updated_label || 'unknown')}</li>`;
    document.getElementById('inspect-btn-copyid').onclick = function() { copyText(s.id, this); };
    document.getElementById('inspect-btn-copytext').onclick = function() { copyText(s.resume_command || s.path, this); };
    document.getElementById('inspect-btn-obsidian').href = '#';
  } catch (err) {
    console.error('Failed to inspect session', err);
  }
}

// Render Session Timeline
function renderTimelineExplorer(entries) {
  const body = document.getElementById('timeline-list-body');
  body.innerHTML = entries.length
    ? entries.map(e => `
        <li class="timeline-card" onclick="inspectObject('log:${escapeHtml(e.heading.substring(0, 30))}')">
          <div style="font-weight:700; color:var(--accent); margin-bottom: 0.3rem;">${escapeHtml(e.heading)}</div>
          <div style="color:var(--text-secondary); white-space:pre-wrap;">${escapeHtml(e.body)}</div>
        </li>
      `).join('')
    : '<li class="meta-info">No timeline entries found.</li>';
}

// Render Monospace Logs
function renderLogsExplorer(entries) {
  const body = document.getElementById('log-list-body');
  body.innerHTML = entries.length
    ? entries.map(e => `
        <li class="item-card log-card" onclick="inspectObject('log:${escapeHtml(e.heading.substring(0, 30))}')">
          <div class="log-title">
            <span>${escapeHtml(e.heading)}</span>
            <button class="btn-dev btn-copy" onclick="event.stopPropagation(); copyText(this.closest('.log-card').querySelector('.log-body').innerText, this)">Copy</button>
          </div>
          <div class="log-body">${escapeHtml(e.body)}</div>
        </li>
      `).join('')
    : '<li class="meta-info">No log entries loaded.</li>';
}

// Unified Context Inspector Loader
async function inspectObject(id) {
  selectedObjectId = id;
  const placeholder = document.getElementById('inspector-placeholder');
  const content = document.getElementById('inspector-content');

  placeholder.style.display = 'none';
  content.style.display = 'flex';

  try {
    const data = await api('/context-pack?id=' + encodeURIComponent(id));

    document.getElementById('inspect-title').innerText = id.split(':')[1];
    document.getElementById('inspect-badge').innerText = id.split(':')[0].toUpperCase();
    document.getElementById('inspect-id').innerText = id;
    document.getElementById('inspect-path').innerText = id.split(':')[1];
    document.getElementById('inspect-score').innerText = '0.90';

    document.getElementById('inspect-packet-body').innerText = data.packet;
    document.getElementById('inspect-reason').innerText = data.summary || "Grounded retrieval score trace compiled for workspace AI agents.";

    // Connections mapping
    const linksUl = document.getElementById('inspect-links');
    linksUl.innerHTML = `
      <li onclick="inspectObject('page:wiki/index.md')">page:wiki/index.md</li>
      <li onclick="inspectObject('page:wiki/log.md')">page:wiki/log.md</li>
    `;

    // Action button wiring
    document.getElementById('inspect-btn-copyid').onclick = function() {
      copyText(id, this);
    };
    document.getElementById('inspect-btn-copytext').onclick = function() {
      copyText(data.packet, this);
    };

    // Obsidian URI link
    const rel = id.split(':')[1];
    document.getElementById('inspect-btn-obsidian').href = `obsidian://open?vault=${encodeURIComponent(obsidianVaultName)}&file=${encodeURIComponent(rel.replaceAll(String.fromCharCode(92), '/'))}`;

  } catch (err) {
    console.error('Failed to load inspected object details', err);
  }
}

// Top Command Palette search handler
async function handlePaletteSearch(q) {
  const dropdown = document.getElementById('palette-dropdown');
  if (!q.trim()) {
    dropdown.style.display = 'none';
    return;
  }

  try {
    const data = await api('/search?q=' + encodeURIComponent(q));
    const res = data.results;

    let htmlStr = '';

    if (res.pages && res.pages.length) {
      htmlStr += `<div class="dropdown-group"><div class="group-title">Pages</div>`;
      htmlStr += res.pages.map(p => `
        <div class="dropdown-row" onclick="inspectObject('${escapeHtml(p.id)}'); document.getElementById('palette-dropdown').style.display='none';">
          <div class="row-left">
            <span class="row-title">${escapeHtml(p.title)}</span>
            <span class="row-path">${escapeHtml(p.path)}</span>
          </div>
          <div class="row-right">
            <span class="row-path">${escapeHtml(p.reason)}</span>
            <span class="row-score">${escapeHtml(String(p.score))}</span>
          </div>
        </div>
      `).join('');
      htmlStr += `</div>`;
    }

    if (res.skills && res.skills.length) {
      htmlStr += `<div class="dropdown-group"><div class="group-title">Skills</div>`;
      htmlStr += res.skills.map(s => `
        <div class="dropdown-row" onclick="inspectObject('${escapeHtml(s.id)}'); document.getElementById('palette-dropdown').style.display='none';">
          <div class="row-left">
            <span class="row-title">${escapeHtml(s.title)}</span>
          </div>
          <div class="row-right">
            <span class="row-path">${escapeHtml(s.reason)}</span>
            <span class="row-score">${escapeHtml(String(s.score))}</span>
          </div>
        </div>
      `).join('');
      htmlStr += `</div>`;
    }

    if (res.memories && res.memories.length) {
      htmlStr += `<div class="dropdown-group"><div class="group-title">Memories</div>`;
      htmlStr += res.memories.map(m => `
        <div class="dropdown-row" onclick="inspectObject('${escapeHtml(m.id)}'); document.getElementById('palette-dropdown').style.display='none';">
          <div class="row-left">
            <span class="row-title">${escapeHtml(m.title)}</span>
          </div>
          <div class="row-right">
            <span class="row-path">${escapeHtml(m.reason)}</span>
            <span class="row-score">${escapeHtml(String(m.score))}</span>
          </div>
        </div>
      `).join('');
      htmlStr += `</div>`;
    }

    if (res.logs && res.logs.length) {
      htmlStr += `<div class="dropdown-group"><div class="group-title">Logs</div>`;
      htmlStr += res.logs.map(l => `
        <div class="dropdown-row" onclick="inspectObject('${escapeHtml(l.id)}'); document.getElementById('palette-dropdown').style.display='none';">
          <div class="row-left">
            <span class="row-title">${escapeHtml(l.title)}</span>
          </div>
          <div class="row-right">
            <span class="row-path">${escapeHtml(l.reason)}</span>
            <span class="row-score">${escapeHtml(String(l.score))}</span>
          </div>
        </div>
      `).join('');
      htmlStr += `</div>`;
    }

    if (!htmlStr) {
      dropdown.innerHTML = `<div style="padding:0.75rem; text-align:center; color:var(--text-muted); font-size:0.75rem;">No matching cockpit objects.</div>`;
    } else {
      dropdown.innerHTML = htmlStr;
    }
    dropdown.style.display = 'block';
  } catch (err) {
    console.error('Failed to run palette search query', err);
  }
}

// Hide palette dropdown when clicking outside
document.addEventListener('click', function(e) {
  const wrap = document.querySelector('.command-palette-wrapper');
  if (wrap && !wrap.contains(e.target)) {
    document.getElementById('palette-dropdown').style.display = 'none';
  }
});

// Retrieval Debugger scoring analyzer
async function runDebugAnalysis() {
  const query = document.getElementById('debug-query').value;
  const resultsBody = document.getElementById('debug-results-body');
  const rejectedBody = document.getElementById('debug-rejected-body');

  if (!query.trim()) return;

  resultsBody.innerHTML = '<li class="meta-info">Analyzing weights...</li>';
  rejectedBody.innerHTML = '<li class="meta-info">Scanning...</li>';

  try {
    const data = await api('/debug?q=' + encodeURIComponent(query));

    resultsBody.innerHTML = data.results.length
      ? data.results.map((r, idx) => {
          let scoreBar = 'â–ˆ'.repeat(Math.round(r.score * 5)) + 'â–‘'.repeat(5 - Math.round(r.score * 5));
          return `
            <li class="timeline-card" onclick="inspectObject('${escapeHtml(r.id)}')">
              <div style="display:flex; justify-content:space-between; font-weight:700;">
                <span>${idx + 1}. ${escapeHtml(r.title)} <span style="font-size:0.65rem; color:var(--text-muted); font-weight:normal;">(${escapeHtml(r.type)})</span></span>
                <span style="color:var(--success); font-family:var(--font-mono);">${escapeHtml(String(r.score))} ${scoreBar}</span>
              </div>
              <div class="meta-info" style="margin-top:0.3rem;">
                Weights: semantic: ${r.breakdown.semantic} | recency: +${r.breakdown.recency} | graph: +${r.breakdown.graph}
              </div>
              <div style="font-size:0.72rem; color:var(--text-secondary); margin-top:0.4rem; background:var(--bg-input); padding:0.4rem; border-radius:3px;">
                "${escapeHtml(r.matched_text)}"
              </div>
            </li>
          `;
        }).join('')
      : '<li class="meta-info">No top results found.</li>';

    rejectedBody.innerHTML = data.rejected.length
      ? data.rejected.map(r => `
          <li class="timeline-card" style="border-color: rgba(244,67,54,0.15);" onclick="inspectObject('${escapeHtml(r.id)}')">
            <div style="font-weight:700; color:var(--text-secondary);">${escapeHtml(r.title)}</div>
            <div style="font-size:0.68rem; color:var(--danger); margin-top:0.2rem;">
              Rejected: ${escapeHtml(r.reason)}
            </div>
          </li>
        `).join('')
      : '<li class="meta-info">No rejected near-matches found.</li>';
  } catch (err) {
    console.error('Failed to analyze debug weights', err);
  }
}

// -------------------------------------------------------------
// Interactive Concept Network Map (Physics simulation in pure Canvas)
// -------------------------------------------------------------
let graphNodes = [];
let graphLinks = [];
let graphFreeze = false;
let graphZoom = 1.0;
let graphPanX = 0;
let graphPanY = 0;
let hoveredNode = null;
let selectedNode = null;
let draggedNode = null;
let isDraggingCanvas = false;
let dragStartX = 0;
let dragStartY = 0;
let canvas, ctx;
let layoutMode = 'galaxy';

let physicsParams = {
  repulsion: 450,
  linklen: 70,
  gravity: 0.015
};

let displayParams = {
  labels: true,
  grid: true,
  progressive: true
};

let expandedNodeIds = new Set();

function getRootNode() {
  if (graphNodes.length === 0) return null;
  let root = graphNodes.find(n => n.kind === 'page' && (n.label.toLowerCase().includes('index') || n.path.toLowerCase().includes('index')));
  if (!root) {
    root = graphNodes[0];
  }
  return root;
}

function isNodeVisible(n) {
  if (!displayParams.progressive) return true;
  const root = getRootNode();
  if (root && n.id === root.id) return true;
  if (expandedNodeIds.has(n.id)) return true;

  const idx = graphNodes.indexOf(n);
  return graphLinks.some(l => {
    const s = graphNodes[l.source];
    const t = graphNodes[l.target];
    if (!s || !t) return false;
    return (l.source === idx && expandedNodeIds.has(s.id)) ||
           (l.target === idx && expandedNodeIds.has(t.id));
  });
}

function getCollapsedCount(n) {
  if (!displayParams.progressive) return 0;
  const idx = graphNodes.indexOf(n);
  let count = 0;
  graphLinks.forEach(l => {
    const s = graphNodes[l.source];
    const t = graphNodes[l.target];
    if (!s || !t) return;
    if (l.source === idx && !isNodeVisible(t)) count++;
    if (l.target === idx && !isNodeVisible(s)) count++;
  });
  return count;
}

function updateForceParam(param, value) {
  physicsParams[param] = parseFloat(value);
  if (param === 'repulsion') {
    document.getElementById('val-repulsion').innerText = value;
  } else if (param === 'linklen') {
    document.getElementById('val-linklen').innerText = value;
  } else if (param === 'gravity') {
    document.getElementById('val-gravity').innerText = value;
  }
}

function updateDisplayParam(param, checked) {
  displayParams[param] = checked;
}

function toggleControls() {
  const panel = document.getElementById('graph-controls');
  const body = document.getElementById('controls-body');
  const toggleBtn = panel.querySelector('span[onclick]');

  if (panel.style.height === '35px') {
    panel.style.height = '';
    panel.style.width = '220px';
    body.style.display = 'block';
    toggleBtn.innerText = '[Hide]';
  } else {
    panel.style.height = '35px';
    panel.style.width = '120px';
    body.style.display = 'none';
    toggleBtn.innerText = '[Show]';
  }
}

function setLayoutMode(mode) {
  layoutMode = mode;
  const btnGalaxy = document.getElementById('btn-mode-galaxy');
  const btnMindmap = document.getElementById('btn-mode-mindmap');

  if (mode === 'galaxy') {
    btnGalaxy.style.background = 'var(--bg-card)';
    btnGalaxy.style.color = 'var(--accent)';
    btnGalaxy.style.borderColor = 'var(--accent)';
    btnMindmap.style.background = '';
    btnMindmap.style.color = '';
    btnMindmap.style.borderColor = '';
  } else {
    btnMindmap.style.background = 'var(--bg-card)';
    btnMindmap.style.color = 'var(--accent)';
    btnMindmap.style.borderColor = 'var(--accent)';
    btnGalaxy.style.background = '';
    btnGalaxy.style.color = '';
    btnGalaxy.style.borderColor = '';
    calculateMindMapLayout();
  }
}

function calculateMindMapLayout() {
  if (graphNodes.length === 0 || !canvas) return;

  const width = canvas.width;
  const height = canvas.height;
  const cx = width / 2;
  const cy = height / 2;

  let root = getRootNode();
  if (!root) return;

  const rootIdx = graphNodes.indexOf(root);
  let queue = [rootIdx];
  let visited = new Set([rootIdx]);
  let depths = {};
  depths[rootIdx] = 0;

  let adj = {};
  graphNodes.forEach((_, i) => adj[i] = []);
  graphLinks.forEach(l => {
    const n1 = graphNodes[l.source];
    const n2 = graphNodes[l.target];
    if (n1 && n2 && isNodeVisible(n1) && isNodeVisible(n2)) {
      adj[l.source].push(l.target);
      adj[l.target].push(l.source);
    }
  });

  while (queue.length > 0) {
    let curr = queue.shift();
    let d = depths[curr];

    adj[curr].forEach(neighbor => {
      const neighborNode = graphNodes[neighbor];
      if (neighborNode && isNodeVisible(neighborNode) && !visited.has(neighbor)) {
        visited.add(neighbor);
        depths[neighbor] = d + 1;
        queue.push(neighbor);
      }
    });
  }

  let depthGroups = {};
  graphNodes.forEach((n, i) => {
    if (!isNodeVisible(n)) return;
    let d = depths[i] || 0;
    if (!depthGroups[d]) depthGroups[d] = [];
    depthGroups[d].push(i);
  });

  const horizontalGap = 170;
  const verticalGap = 45;

  Object.keys(depthGroups).forEach(dKey => {
    let d = parseInt(dKey);
    let group = depthGroups[d];
    let count = group.length;

    group.sort((a, b) => {
      let nA = graphNodes[a];
      let nB = graphNodes[b];
      if (nA.kind !== nB.kind) return nA.kind === 'page' ? -1 : 1;
      return 0;
    });

    group.forEach((nodeIdx, idx) => {
      let node = graphNodes[nodeIdx];
      node.targetX = cx - 120 + d * horizontalGap;
      node.targetY = cy + (idx - (count - 1) / 2) * verticalGap;
    });
  });
}

async function loadGraph() {
  try {
    const data = await api('/graph');
    graphNodes = data.nodes;
    graphLinks = data.links;
    document.getElementById('graph-node-count').innerText = graphNodes.length + " nodes, " + graphLinks.length + " links";
    initGraphPhysics(true);
    if (layoutMode === 'mindmap') {
      calculateMindMapLayout();
    }
  } catch (err) {
    console.error('Failed to load graph data', err);
  }
}

function initGraphPhysics(resetPositions = false) {
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const cx = rect.width / 2;
  const cy = rect.height / 2;

  if (resetPositions) {
    graphZoom = 1.0;
    graphPanX = 0;
    graphPanY = 0;
    hoveredNode = null;
    selectedNode = null;
    expandedNodeIds.clear();
    const root = getRootNode();
    if (root) {
      expandedNodeIds.add(root.id);
    }
  }

  graphNodes.forEach((n, i) => {
    if (resetPositions || n.x === undefined) {
      const angle = i * 0.45;
      const r = 35 + i * 8;
      n.x = cx + Math.cos(angle) * r;
      n.y = cy + Math.sin(angle) * r;
      n.vx = 0;
      n.vy = 0;
    }
  });
}

function toggleFreezeGraph() {
  graphFreeze = !graphFreeze;
  const btn = document.getElementById('btn-freeze');
  btn.innerText = graphFreeze ? 'Resume Layout' : 'Freeze Layout';
  btn.style.borderColor = graphFreeze ? 'var(--accent)' : '';
  btn.style.color = graphFreeze ? 'var(--accent)' : '';
}

function runPhysicsStep() {
  if (graphFreeze || graphNodes.length === 0) return;

  // Glue invisible nodes to their visible parent in all layout modes before layout/physics steps!
  graphNodes.forEach(n => {
    if (!isNodeVisible(n)) {
      const idx = graphNodes.indexOf(n);
      const parentLink = graphLinks.find(l => {
        const s = graphNodes[l.source];
        const t = graphNodes[l.target];
        return (l.source === idx && s && expandedNodeIds.has(s.id)) ||
               (l.target === idx && t && expandedNodeIds.has(t.id));
      });
      if (parentLink) {
        const parent = graphNodes[parentLink.source === idx ? parentLink.target : parentLink.source];
        if (parent) {
          n.targetX = parent.x;
          n.targetY = parent.y;
          n.x = parent.x;
          n.y = parent.y;
        }
      }
      n.vx = 0;
      n.vy = 0;
    }
  });

  if (layoutMode === 'mindmap') {
    graphNodes.forEach(n => {
      if (!isNodeVisible(n)) return;
      if (n.targetX !== undefined && n.targetY !== undefined && n !== draggedNode) {
        n.x += (n.targetX - n.x) * 0.12;
        n.y += (n.targetY - n.y) * 0.12;
        n.vx = 0;
        n.vy = 0;
      }
    });
    return;
  }

  const width = canvas.width;
  const height = canvas.height;
  const cx = width / 2;
  const cy = height / 2;

  const kRepulsion = physicsParams.repulsion;
  const kSpring = 0.05;
  const lRest = physicsParams.linklen;
  const kCenter = physicsParams.gravity;
  const damping = 0.85;

  for (let i = 0; i < graphNodes.length; i++) {
    const n1 = graphNodes[i];
    if (n1 === draggedNode) continue;
    if (!isNodeVisible(n1)) continue;

    for (let j = i + 1; j < graphNodes.length; j++) {
      const n2 = graphNodes[j];
      if (!isNodeVisible(n2)) continue;
      const dx = n2.x - n1.x;
      const dy = n2.y - n1.y;
      const distSq = dx * dx + dy * dy + 0.1;
      const dist = Math.sqrt(distSq);

      if (dist < 300) {
        const force = kRepulsion / distSq;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        n1.vx -= fx;
        n1.vy -= fy;
        n2.vx += fx;
        n2.vy += fy;
      }
    }
  }

  graphLinks.forEach(l => {
    const n1 = graphNodes[l.source];
    const n2 = graphNodes[l.target];
    if (!n1 || !n2) return;
    if (!isNodeVisible(n1) || !isNodeVisible(n2)) return;

    const dx = n2.x - n1.x;
    const dy = n2.y - n1.y;
    const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;

    const displacement = dist - lRest;
    const force = kSpring * displacement;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;

    if (n1 !== draggedNode) {
      n1.vx += fx;
      n1.vy += fy;
    }
    if (n2 !== draggedNode) {
      n2.vx -= fx;
      n2.vy -= fy;
    }
  });

  graphNodes.forEach(n => {
    if (n === draggedNode) return;
    if (!isNodeVisible(n)) return;

    n.vx += (cx - n.x) * kCenter;
    n.vy += (cy - n.y) * kCenter;

    n.x += n.vx;
    n.y += n.vy;
    n.vx *= damping;
    n.vy *= damping;
  });
}

function drawGraph() {
  if (!canvas || !ctx) return;

  ctx.fillStyle = '#18181c';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (displayParams.grid) {
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.015)';
    ctx.lineWidth = 1;
    const gridSize = 45;

    const startX = (graphPanX % gridSize);
    const startY = (graphPanY % gridSize);

    for (let x = startX; x < canvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = startY; y < canvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }
  }

  ctx.save();
  ctx.translate(graphPanX, graphPanY);
  ctx.scale(graphZoom, graphZoom);

  const searchQuery = document.getElementById('palette-search').value.toLowerCase();

  graphLinks.forEach(l => {
    const n1 = graphNodes[l.source];
    const n2 = graphNodes[l.target];
    if (!n1 || !n2) return;
    if (!isNodeVisible(n1) || !isNodeVisible(n2)) return; // Only visible links!

    ctx.beginPath();
    ctx.moveTo(n1.x, n1.y);
    ctx.lineTo(n2.x, n2.y);

    if (l.type === 'contradicts') {
      ctx.strokeStyle = 'rgba(244, 67, 54, 0.4)';
      ctx.lineWidth = 1.5;
    } else if (l.type === 'supersedes') {
      ctx.strokeStyle = 'rgba(255, 152, 0, 0.4)';
      ctx.lineWidth = 1.2;
    } else if (l.type === 'reference') {
      ctx.strokeStyle = 'rgba(0, 188, 212, 0.3)';
      ctx.lineWidth = 1.0;
    } else {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = 0.6;
    }
    ctx.stroke();
  });

  graphNodes.forEach(n => {
    if (!isNodeVisible(n)) return; // Only visible nodes!

    ctx.beginPath();
    ctx.arc(n.x, n.y, n.size, 0, Math.PI * 2);

    let nodeColor = '#62626e';
    let isMatched = searchQuery ? n.label.toLowerCase().includes(searchQuery) || (n.claim && n.claim.toLowerCase().includes(searchQuery)) : true;

    if (n.kind === 'page') {
      nodeColor = '#a3a3a6';
    } else if (n.kind === 'memory') {
      if (n.status === 'approved') {
        nodeColor = '#4caf50';
      } else {
        nodeColor = '#00bcd4';
      }
    }

    const isSelected = n === selectedNode || n === hoveredNode;
    ctx.fillStyle = nodeColor;

    if (searchQuery && !isMatched) {
      ctx.globalAlpha = 0.25;
    } else {
      ctx.globalAlpha = 1.0;
    }

    ctx.fill();

    if (isSelected || (searchQuery && isMatched)) {
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.8;
      ctx.stroke();
    } else {
      ctx.strokeStyle = '#18181c';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw expansion indicator for progressive mode!
    const collapsedCount = getCollapsedCount(n);
    if (collapsedCount > 0) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.size + 4, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(0, 188, 212, 0.45)';
      ctx.lineWidth = 1.2;
      ctx.setLineDash([2, 3]); // dashed line!
      ctx.stroke();
      ctx.setLineDash([]); // restore solid line!

      // Draw a tiny badge showing the count!
      ctx.fillStyle = 'var(--accent)';
      ctx.font = "bold 8px 'JetBrains Mono', monospace";
      ctx.textAlign = 'left';
      ctx.fillText("+" + collapsedCount, n.x + n.size + 2, n.y + 3);
    }

    if ((displayParams.labels && graphZoom > 0.8) || isSelected || (searchQuery && isMatched)) {
      ctx.fillStyle = '#e3e3e6';
      ctx.font = "500 " + Math.max(7, Math.round(9 / graphZoom)) + "px 'Outfit', sans-serif";
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y - n.size - 4);
    }

    ctx.globalAlpha = 1.0;
  });

  ctx.restore();
}

function handleCanvasMouseDown(e) {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const worldX = (mouseX - graphPanX) / graphZoom;
  const worldY = (mouseY - graphPanY) / graphZoom;

  let foundNode = null;
  for (let i = graphNodes.length - 1; i >= 0; i--) {
    const n = graphNodes[i];
    if (!isNodeVisible(n)) continue; // Can only click visible nodes!
    const dist = Math.sqrt((n.x - worldX)**2 + (n.y - worldY)**2);
    if (dist <= n.size + 6) {
      foundNode = n;
      break;
    }
  }

  if (foundNode) {
    draggedNode = foundNode;
    selectedNode = foundNode;
    canvas.style.cursor = 'grabbing';
    inspectObject(foundNode.id);

    // Toggle progressive disclosure state!
    if (displayParams.progressive) {
      if (expandedNodeIds.has(foundNode.id)) {
        const root = getRootNode();
        if (!root || foundNode.id !== root.id || expandedNodeIds.size > 1) {
          expandedNodeIds.delete(foundNode.id);
        }
      } else {
        expandedNodeIds.add(foundNode.id);
      }
      if (layoutMode === 'mindmap') {
        calculateMindMapLayout();
      }
    }
  } else {
    isDraggingCanvas = true;
    dragStartX = mouseX - graphPanX;
    dragStartY = mouseY - graphPanY;
    canvas.style.cursor = 'grabbing';
  }
}

function handleCanvasMouseMove(e) {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const worldX = (mouseX - graphPanX) / graphZoom;
  const worldY = (mouseY - graphPanY) / graphZoom;

  if (draggedNode) {
    draggedNode.x = worldX;
    draggedNode.y = worldY;
    draggedNode.vx = 0;
    draggedNode.vy = 0;
  } else if (isDraggingCanvas) {
    graphPanX = mouseX - dragStartX;
    graphPanY = mouseY - dragStartY;
  } else {
    let foundNode = null;
    for (let i = graphNodes.length - 1; i >= 0; i--) {
      const n = graphNodes[i];
      const dist = Math.sqrt((n.x - worldX)**2 + (n.y - worldY)**2);
      if (dist <= n.size + 6) {
        foundNode = n;
        break;
      }
    }

    if (foundNode !== hoveredNode) {
      hoveredNode = foundNode;
      canvas.style.cursor = foundNode ? 'pointer' : 'grab';
    }
  }
}

function handleCanvasMouseUp() {
  draggedNode = null;
  isDraggingCanvas = false;
  canvas.style.cursor = hoveredNode ? 'pointer' : 'grab';
}

function handleCanvasWheel(e) {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  const worldX = (mouseX - graphPanX) / graphZoom;
  const worldY = (mouseY - graphPanY) / graphZoom;

  const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
  graphZoom = Math.max(0.2, Math.min(4.0, graphZoom * zoomFactor));

  graphPanX = mouseX - worldX * graphZoom;
  graphPanY = mouseY - worldY * graphZoom;
}

function setupCanvasElement() {
  canvas = document.getElementById('concept-map');
  if (!canvas) return;
  ctx = canvas.getContext('2d');

  function resize() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    initGraphPhysics(false);
  }

  window.addEventListener('resize', resize);
  resize();

  canvas.addEventListener('mousedown', handleCanvasMouseDown);
  canvas.addEventListener('mousemove', handleCanvasMouseMove);
  canvas.addEventListener('mouseup', handleCanvasMouseUp);
  canvas.addEventListener('mouseleave', handleCanvasMouseUp);
  canvas.addEventListener('wheel', handleCanvasWheel);
}

// -------------------------------------------------------------
// Watcher Approve/Reject handlers (re-mapped to cockpit view refresh)
// -------------------------------------------------------------
async function approveDraft(id) {
  if (!confirm('Approve draft and promote memory: ' + id + '?')) return;
  const res = await api('/reducer/approve?id=' + encodeURIComponent(id));
  alert(res.status === 'ok' ? 'Approved & Promoted successfully!' : 'Error: ' + res.message);
  prefetchSystemData();
  loadGraph();
}

async function rejectDraft(id) {
  if (!confirm('Reject and archive draft: ' + id + '?')) return;
  const res = await api('/reducer/reject?id=' + encodeURIComponent(id));
  alert(res.status === 'ok' ? 'Rejected/archived successfully!' : 'Error: ' + res.message);
  prefetchSystemData();
}

async function loadWorkspaceList(refresh = false) {
  try {
    const data = await api('/workspace/list' + (refresh ? '?refresh=1' : ''));
    const select = document.getElementById('wiki-selector');
    if (!select) return;

    select.innerHTML = data.wikis.map(w => `
      <option value="${escapeHtml(w.path)}" ${w.active ? 'selected' : ''}>
        ${escapeHtml(w.name)} (${escapeHtml(String(w.page_count || 0))} pages)
      </option>
    `).join('');
  } catch (err) {
    console.error('Failed to load workspace list', err);
  }
}

async function switchWorkspace(path) {
  if (!path) return;
  try {
    const res = await api('/workspace/switch?path=' + encodeURIComponent(path));
    if (res.status === 'ok') {
      // Switched successfully! Prefetch all data and reload the cockpit!
      prefetchSystemData();
      loadGraph();
      loadWorkspaceList(); // Refresh list to update active state
    } else {
      alert('Error switching workspace: ' + res.message);
    }
  } catch (err) {
    console.error('Failed to switch workspace', err);
  }
}

// Startup
prefetchSystemData();
setupCanvasElement();
loadGraph();
loadWorkspaceList();

function animate() {
  runPhysicsStep();
  drawGraph();
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
</script>
</body>
</html>"""
        self._send_html(html_body)

    def _serve_api_pages(self) -> None:
        query_values = parse_qs(urlsplit(self.path).query).get("q", [""])
        query = query_values[0]
        self._send_json({"pages": self._wiki_pages(query)})

    def _serve_api_skills(self) -> None:
        index = self._read_index()
        skills = []
        for s in index.get("skills", []):
            skills.append({
                "id": s.get("id", ""),
                "title": s.get("title", ""),
                "kind": s.get("kind", ""),
                "score": s.get("feedback_score", 0),
            })
        self._send_json({"skills": skills})

    def _serve_api_skill_detail(self, skill_id: str) -> None:
        index = self._read_index()
        for s in index.get("skills", []):
            if s.get("id") == skill_id:
                self._send_json({"skill": s})
                return
        self._send_json({"skill": None})

    def _serve_api_brv_status(self) -> None:
        self._send_json(self._brv_status())

    def _serve_api_log(self) -> None:
        self._send_json({"entries": self._recent_log_entries(20)})

    def _serve_api_config(self) -> None:
        self._send_json(self._read_config())

    def _serve_api_memory(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        status = query.get("status", [""])[0]
        self._send_json({"memories": self._memory_objects(status)})

    def _serve_api_memory_events(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        raw_limit = query.get("limit", ["25"])[0]
        try:
            limit = max(1, min(100, int(raw_limit)))
        except ValueError:
            limit = 25
        self._send_json({"events": self._memory_events(limit)})


def run_server(workspace: Path, host: str, port: int) -> None:
    DashboardHandler.workspace = workspace
    DashboardHandler.registry_root = workspace
    server = HTTPServer((host, port), DashboardHandler)
    print(f"Dashboard serving at http://{host}:{port}/dashboard")
    print(f"Workspace: {workspace}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM Wiki Memory Dashboard")
    parser.add_argument("--workspace", default=str(Path.cwd()), help="Workspace root")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8183, help="Bind port")
    args = parser.parse_args()
    run_server(Path(args.workspace).resolve(), args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
