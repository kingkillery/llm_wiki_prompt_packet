#!/usr/bin/env python3
"""Tests for dashboard server (M5)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_MODULE_PATH = REPO_ROOT / "support" / "scripts" / "dashboard_server.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestDashboardServer(unittest.TestCase):
    def setUp(self) -> None:
        self.dashboard = load_module(DASHBOARD_MODULE_PATH, "dashboard_server")
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        # Seed minimal wiki structure
        (self.workspace / "wiki" / "concepts").mkdir(parents=True)
        (self.workspace / "wiki" / "concepts" / "memory-layering.md").write_text(
            "# Memory Layering\n\nFive layers of memory.\n", encoding="utf-8"
        )
        (self.workspace / ".llm-wiki").mkdir(parents=True, exist_ok=True)
        (self.workspace / ".llm-wiki" / "skill-index.json").write_text(
            json.dumps({
                "skills": [
                    {"id": "skill-git-rebase", "title": "Git rebase", "kind": "workflow", "feedback_score": 0}
                ]
            }),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_handler_reads_config(self) -> None:
        handler = self.dashboard.DashboardHandler
        handler.workspace = self.workspace
        cfg = handler._read_config(handler)
        self.assertIsInstance(cfg, dict)

    def test_handler_wiki_pages(self) -> None:
        handler = self.dashboard.DashboardHandler
        handler.workspace = self.workspace
        pages = handler._wiki_pages(handler, "")
        self.assertEqual(len(pages), 1)
        self.assertIn("memory layering", pages[0]["title"])

    def test_handler_wiki_pages_search(self) -> None:
        handler = self.dashboard.DashboardHandler
        handler.workspace = self.workspace
        pages = handler._wiki_pages(handler, "memory")
        self.assertEqual(len(pages), 1)
        pages = handler._wiki_pages(handler, "nonexistent")
        self.assertEqual(len(pages), 0)

    def test_handler_read_index(self) -> None:
        handler = self.dashboard.DashboardHandler
        handler.workspace = self.workspace
        idx = handler._read_index(handler)
        self.assertEqual(len(idx.get("skills", [])), 1)

    def test_handler_recent_log_entries(self) -> None:
        handler = self.dashboard.DashboardHandler
        handler.workspace = self.workspace
        # Seed a log file
        (self.workspace / "wiki" / "log.md").write_text(
            "# Wiki Log\n\n## 2026-04-22T10:00:00Z - test event\n- line one\n- line two\n",
            encoding="utf-8",
        )
        entries = handler._recent_log_entries(handler, limit=5)
        self.assertEqual(len(entries), 1)
        self.assertIn("test event", entries[0]["heading"])
        self.assertIn("line one", entries[0]["body"])

    def test_wiki_pages_have_obsidian_url(self) -> None:
        handler = self.dashboard.DashboardHandler
        handler.workspace = self.workspace
        pages = handler._wiki_pages(handler, "")
        self.assertEqual(len(pages), 1)
        self.assertIn("obsidian://", pages[0]["obsidian_url"])


if __name__ == "__main__":
    unittest.main()
