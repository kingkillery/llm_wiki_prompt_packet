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
from pathlib import Path
from typing import Any

# Use stdlib only; no external framework dependencies
from http.server import HTTPServer, BaseHTTPRequestHandler


class DashboardHandler(BaseHTTPRequestHandler):
    workspace: Path = Path.cwd()

    def log_message(self, fmt: str, *args) -> None:
        # Suppress default logging for cleaner output
        pass

    def _send_json(self, data: dict) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_html(self, body: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _read_config(self) -> dict:
        path = self.workspace / ".llm-wiki" / "config.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _read_index(self) -> dict:
        path = self.workspace / ".llm-wiki" / "skill-index.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _brv_status(self) -> dict:
        try:
            result = subprocess.run(
                ["brv", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "available": result.returncode == 0,
                "output": result.stdout.strip() if result.returncode == 0 else result.stderr.strip(),
            }
        except FileNotFoundError:
            return {"available": False, "output": "brv not installed"}
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
            pages.append({
                "path": rel,
                "title": title,
                "snippet": content[:200].replace("\n", " "),
                "obsidian_url": f"obsidian://open?vault=llm-wiki&file={rel.replace('/', '%2F')}",
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

    def do_GET(self) -> None:
        if self.path == "/dashboard" or self.path == "/dashboard/":
            self._serve_index()
        elif self.path == "/dashboard/api/pages":
            self._serve_api_pages()
        elif self.path == "/dashboard/api/skills":
            self._serve_api_skills()
        elif self.path.startswith("/dashboard/api/skills/"):
            skill_id = self.path.split("/")[-1]
            self._serve_api_skill_detail(skill_id)
        elif self.path == "/dashboard/api/brv/status":
            self._serve_api_brv_status()
        elif self.path == "/dashboard/api/log":
            self._serve_api_log()
        elif self.path == "/dashboard/api/config":
            self._serve_api_config()
        else:
            self._send_html("<h1>Not Found</h1>", 404)

    def _serve_index(self) -> None:
        html_body = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LLM Wiki Dashboard</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 1rem; background: #f5f5f5; color: #222; }
  header { margin-bottom: 1rem; }
  h1 { font-size: 1.4rem; margin: 0 0 0.5rem; }
  .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
  .card { background: #fff; border-radius: 8px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .card h2 { font-size: 1rem; margin: 0 0 0.5rem; }
  input[type="search"] { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 0.5rem; }
  ul { list-style: none; padding: 0; margin: 0; }
  li { padding: 0.4rem 0; border-bottom: 1px solid #eee; }
  li:last-child { border-bottom: none; }
  a { color: #0366d6; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .meta { color: #666; font-size: 0.85rem; }
  .status-ok { color: #22863a; }
  .status-bad { color: #cb2431; }
</style>
</head>
<body>
<header>
  <h1>LLM Wiki Dashboard</h1>
  <div class="meta">Workspace: """ + html.escape(str(self.workspace)) + """</div>
</header>
<div class="grid">
  <div class="card">
    <h2>Wiki Pages</h2>
    <input type="search" id="page-search" placeholder="Search wiki..." oninput="searchPages(this.value)">
    <ul id="page-list"><li>Loading...</li></ul>
  </div>
  <div class="card">
    <h2>Active Skills</h2>
    <ul id="skill-list"><li>Loading...</li></ul>
  </div>
  <div class="card">
    <h2>BRV Status</h2>
    <div id="brv-status">Loading...</div>
  </div>
  <div class="card">
    <h2>Recent Log</h2>
    <ul id="log-list"><li>Loading...</li></ul>
  </div>
</div>
<script>
async function api(path) {
  const r = await fetch('/dashboard/api' + path);
  return r.json();
}

async function searchPages(q) {
  const data = await api('/pages?q=' + encodeURIComponent(q));
  const list = document.getElementById('page-list');
  list.innerHTML = data.pages.length
    ? data.pages.map(p => `<li><a href="${escapeHtml(p.obsidian_url)}" title="Open in Obsidian">${escapeHtml(p.title)}</a><div class="meta">${escapeHtml(p.path)}</div></li>`).join('')
    : '<li>No pages found.</li>';
}

async function loadSkills() {
  const data = await api('/skills');
  const list = document.getElementById('skill-list');
  list.innerHTML = data.skills.length
    ? data.skills.map(s => `<li><strong>${escapeHtml(s.title)}</strong> <span class="meta">(${escapeHtml(s.id)}) score ${s.score}</span></li>`).join('')
    : '<li>No skills indexed.</li>';
}

async function loadBrv() {
  const data = await api('/brv/status');
  const el = document.getElementById('brv-status');
  el.innerHTML = data.available
    ? `<span class="status-ok">Connected</span><pre style="white-space:pre-wrap;font-size:0.8rem">${escapeHtml(data.output)}</pre>`
    : `<span class="status-bad">Disconnected</span><pre style="white-space:pre-wrap;font-size:0.8rem">${escapeHtml(data.output)}</pre>`;
}

async function loadLog() {
  const data = await api('/log');
  const list = document.getElementById('log-list');
  list.innerHTML = data.entries.length
    ? data.entries.map(e => `<li><strong>${escapeHtml(e.heading)}</strong><pre style="white-space:pre-wrap;font-size:0.8rem;margin:0.25rem 0 0">${escapeHtml(e.body)}</pre></li>`).join('')
    : '<li>No log entries.</li>';
}

function escapeHtml(t) {
  const div = document.createElement('div');
  div.textContent = t;
  return div.innerHTML;
}

searchPages('');
loadSkills();
loadBrv();
loadLog();
</script>
</body>
</html>"""
        self._send_html(html_body)

    def _serve_api_pages(self) -> None:
        qs = self.path.split("?")[1] if "?" in self.path else ""
        query = ""
        for part in qs.split("&"):
            if part.startswith("q="):
                query = part[2:].replace("+", " ")
                break
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


def run_server(workspace: Path, host: str, port: int) -> None:
    DashboardHandler.workspace = workspace
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
