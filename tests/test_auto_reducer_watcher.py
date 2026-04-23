#!/usr/bin/env python3
"""Tests for auto-reducer watcher (M2)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCHER_MODULE_PATH = REPO_ROOT / "support" / "scripts" / "auto_reducer_watcher.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestAutoReducerWatcher(unittest.TestCase):
    def setUp(self) -> None:
        self.watcher = load_module(WATCHER_MODULE_PATH, "auto_reducer_watcher")
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _workspace_dirs(self):
        base = self.workspace / ".llm-wiki" / "skill-pipeline"
        return base, base / "sessions", base / "auto-packets", base / "auto-packets" / "rejected"

    def test_start_creates_marker(self) -> None:
        _, sessions_dir, _, _ = self._workspace_dirs()
        class Args:
            workspace = str(self.workspace)
            session_id = "sess-123"
            agent = "claude"
            goal = "bump submodule"
        self.watcher.cmd_start(Args())
        marker = sessions_dir / "sess-123.json"
        self.assertTrue(marker.exists())
        data = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(data["agent"], "claude")
        self.assertEqual(data["goal"], "bump submodule")

    def test_end_creates_draft(self) -> None:
        _, sessions_dir, drafts_dir, _ = self._workspace_dirs()
        # Create marker
        marker = sessions_dir / "sess-456.json"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps({
                "session_id": "sess-456",
                "agent": "codex",
                "goal": "fix build",
                "start_time": "2026-04-22T10:00:00Z",
                "start_git_status": "",
                "start_file_list": [],
            }),
            encoding="utf-8",
        )
        class Args:
            workspace = str(self.workspace)
            session_id = "sess-456"
            returncode = 0
        self.watcher.cmd_end(Args())
        drafts = list(drafts_dir.glob("auto-*.md"))
        self.assertEqual(len(drafts), 1)
        text = drafts[0].read_text(encoding="utf-8")
        self.assertIn("fix build", text)
        self.assertIn("success", text.lower())
        # Marker should be cleaned up
        self.assertFalse(marker.exists())

    def test_end_with_failure(self) -> None:
        _, sessions_dir, drafts_dir, _ = self._workspace_dirs()
        sessions_dir.mkdir(parents=True, exist_ok=True)
        marker = sessions_dir / "sess-fail.json"
        marker.write_text(
            json.dumps({
                "session_id": "sess-fail",
                "agent": "pi",
                "goal": "deploy app",
                "start_time": "2026-04-22T10:00:00Z",
                "start_git_status": "",
                "start_file_list": [],
            }),
            encoding="utf-8",
        )
        class Args:
            workspace = str(self.workspace)
            session_id = "sess-fail"
            returncode = 1
        self.watcher.cmd_end(Args())
        drafts = list(drafts_dir.glob("auto-*.md"))
        self.assertEqual(len(drafts), 1)
        text = drafts[0].read_text(encoding="utf-8")
        self.assertIn("failure", text.lower())

    def test_approve_moves_to_packets(self) -> None:
        _, _, drafts_dir, _ = self._workspace_dirs()
        drafts_dir.mkdir(parents=True, exist_ok=True)
        draft = drafts_dir / "auto-20260422100000-abc.md"
        draft.write_text("# Draft", encoding="utf-8")
        class Args:
            workspace = str(self.workspace)
            draft_id = "auto-20260422100000-abc"
        self.watcher.cmd_approve(Args())
        packets_dir = self.workspace / ".llm-wiki" / "skill-pipeline" / "packets"
        self.assertTrue((packets_dir / draft.name).exists())
        self.assertFalse(draft.exists())

    def test_reject_moves_to_rejected(self) -> None:
        _, _, drafts_dir, rejected_dir = self._workspace_dirs()
        drafts_dir.mkdir(parents=True, exist_ok=True)
        draft = drafts_dir / "auto-20260422100000-rej.md"
        draft.write_text("# Draft", encoding="utf-8")
        class Args:
            workspace = str(self.workspace)
            draft_id = "auto-20260422100000-rej"
        self.watcher.cmd_reject(Args())
        self.assertTrue((rejected_dir / draft.name).exists())
        self.assertFalse(draft.exists())

    def test_list_shows_pending(self) -> None:
        _, _, drafts_dir, _ = self._workspace_dirs()
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "auto-20260422100000-a.md").write_text("a", encoding="utf-8")
        (drafts_dir / "auto-20260422100000-b.md").write_text("b", encoding="utf-8")
        class Args:
            workspace = str(self.workspace)
        # cmd_list prints to stdout; we just verify it returns 0
        rc = self.watcher.cmd_list(Args())
        self.assertEqual(rc, 0)

    def test_show_displays_draft(self) -> None:
        _, _, drafts_dir, _ = self._workspace_dirs()
        drafts_dir.mkdir(parents=True, exist_ok=True)
        draft = drafts_dir / "auto-20260422100000-show.md"
        draft.write_text("# Test draft content", encoding="utf-8")
        class Args:
            workspace = str(self.workspace)
            draft_id = "auto-20260422100000-show"
        rc = self.watcher.cmd_show(Args())
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
