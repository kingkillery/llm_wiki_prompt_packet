from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT = REPO_ROOT / "support" / "scripts"
MODULE_PATH = SUPPORT / "llm_wiki_compile.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_compile", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["llm_wiki_compile"] = module
    spec.loader.exec_module(module)
    return module


class WikiCompileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / ".llm-wiki").mkdir()
        (self.workspace / ".llm-wiki" / "config.json").write_text(
            '{"wiki_layer": {"vault_path": ".", "compile_state_path": ".llm-wiki/state/wiki-compile.json"}}',
            encoding="utf-8",
        )
        (self.workspace / "raw" / "imports").mkdir(parents=True)
        (self.workspace / "raw" / "imports" / "source.md").write_text(
            "Initial source.\nConcept: Retrieval Routing\nEntity: Obsidian Vault\n",
            encoding="utf-8",
        )
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_status_reports_pending_changed_sources(self) -> None:
        payload = self.module.compile_status(self.workspace)

        self.assertEqual(payload["source_count"], 1)
        self.assertEqual(payload["pending_changed_sources"], 1)
        self.assertEqual(payload["changed_sources"][0]["path"], "raw/imports/source.md")

    def test_compile_marks_sources_then_detects_future_change(self) -> None:
        first = self.module.mark_compiled(self.workspace, changed_only=True)
        self.assertEqual(first["compiled_sources"], ["raw/imports/source.md"])
        self.assertEqual(first["pending_changed_sources"], 0)
        source_note = self.workspace / "wiki" / "sources" / "source.md"
        self.assertTrue(source_note.exists())
        source_text = source_note.read_text(encoding="utf-8")
        self.assertIn("type: source", source_text)
        self.assertIn("  - raw/imports/source.md", source_text)
        self.assertTrue((self.workspace / "wiki" / "syntheses" / "source Synthesis.md").exists())
        self.assertTrue((self.workspace / "wiki" / "concepts" / "Retrieval Routing.md").exists())
        self.assertTrue((self.workspace / "wiki" / "entities" / "Obsidian Vault.md").exists())
        state = (self.workspace / ".llm-wiki" / "state" / "wiki-compile.json").read_text(encoding="utf-8")
        self.assertIn('"wiki/sources/source.md"', state)
        self.assertIn('"wiki/syntheses/source Synthesis.md"', state)
        self.assertIn('"wiki/concepts/Retrieval Routing.md"', state)
        self.assertIn('"wiki/entities/Obsidian Vault.md"', state)

        unchanged = self.module.compile_status(self.workspace)
        self.assertEqual(unchanged["pending_changed_sources"], 0)

        (self.workspace / "raw" / "imports" / "source.md").write_text("Changed source.", encoding="utf-8")
        changed = self.module.compile_status(self.workspace)
        self.assertEqual(changed["pending_changed_sources"], 1)

    def test_prompt_budget_warns_and_clips_oversized_sources(self) -> None:
        (self.workspace / ".llm-wiki" / "config.json").write_text(
            (
                '{"wiki_layer": {"vault_path": ".", "compile_state_path": ".llm-wiki/state/wiki-compile.json"}, '
                '"wiki_compile": {"total_token_budget": 20, "per_source_token_budget": 10}}'
            ),
            encoding="utf-8",
        )
        (self.workspace / "raw" / "imports" / "large.md").write_text("x" * 200, encoding="utf-8")

        payload = self.module.compile_status(self.workspace)
        budget = payload["prompt_budget"]

        clipped = [item for item in budget["sources"] if item["path"] == "raw/imports/large.md"][0]
        self.assertTrue(clipped["clipped"])
        self.assertLessEqual(clipped["budgeted_tokens"], clipped["token_budget"])
        self.assertGreaterEqual(len(budget["warnings"]), 1)

    def test_cli_accepts_workspace_after_subcommand(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), "status", "--workspace", str(self.workspace), "--json"],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(proc.stdout)
        self.assertEqual(payload["source_count"], 1)


if __name__ == "__main__":
    unittest.main()
