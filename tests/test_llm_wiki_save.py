from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT = REPO_ROOT / "support" / "scripts"
MODULE_PATH = SUPPORT / "llm_wiki_save.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_save", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class WikiSaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / ".llm-wiki").mkdir()
        (self.workspace / ".llm-wiki" / "config.json").write_text(
            '{"wiki_layer": {"vault_path": "."}}',
            encoding="utf-8",
        )
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def args(self, **overrides):
        values = {
            "workspace": str(self.workspace),
            "title": "Research Retrieval Patterns",
            "type": "synthesis",
            "body": "Retrieval should preserve source-backed claims.",
            "body_file": "",
            "source": ["[[Source A]]"],
            "related": ["[[Concept A]]"],
            "tag": ["research"],
            "question": "",
            "answer_quality": "solid",
            "confidence": "medium",
            "url": "",
            "mode": "create-or-update",
        }
        values.update(overrides)
        return Namespace(**values)

    def test_save_creates_note_index_log_and_hot(self) -> None:
        result = self.module.save_note(self.args())

        self.assertEqual(result["action"], "created")
        note = self.workspace / "wiki" / "syntheses" / "Research Retrieval Patterns.md"
        self.assertTrue(note.exists())
        note_text = note.read_text(encoding="utf-8")
        self.assertIn("type: synthesis", note_text)
        self.assertIn("[[Source A]]", note_text)
        self.assertIn("Retrieval should preserve source-backed claims.", note_text)
        self.assertIn("[[Research Retrieval Patterns]]", (self.workspace / "wiki" / "index.md").read_text(encoding="utf-8"))
        self.assertIn("save | Research Retrieval Patterns", (self.workspace / "wiki" / "log.md").read_text(encoding="utf-8"))
        self.assertIn("Recent Context", (self.workspace / "wiki" / "hot.md").read_text(encoding="utf-8"))

    def test_save_updates_existing_note_instead_of_duplicate(self) -> None:
        self.module.save_note(self.args())
        result = self.module.save_note(self.args(body="New durable detail."))

        self.assertEqual(result["action"], "updated")
        notes = list((self.workspace / "wiki" / "syntheses").glob("*.md"))
        self.assertEqual(len(notes), 1)
        self.assertIn("New durable detail.", notes[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
