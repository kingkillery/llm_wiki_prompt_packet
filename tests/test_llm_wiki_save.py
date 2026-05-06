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
            "supersedes": [],
            "contradicts": [],
            "observed_at": "",
            "valid_from": "",
            "valid_until": "",
            "promote_to": "",
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
        overview_text = (self.workspace / "wiki" / "overview.md").read_text(encoding="utf-8")
        self.assertIn("Wiki Overview", overview_text)
        self.assertIn("[[Research Retrieval Patterns]]", overview_text)

    def test_save_updates_existing_note_instead_of_duplicate(self) -> None:
        self.module.save_note(self.args())
        result = self.module.save_note(self.args(body="New durable detail."))

        self.assertEqual(result["action"], "updated")
        notes = list((self.workspace / "wiki" / "syntheses").glob("*.md"))
        self.assertEqual(len(notes), 1)
        self.assertIn("New durable detail.", notes[0].read_text(encoding="utf-8"))

    def test_save_query_note_to_queries_folder(self) -> None:
        result = self.module.save_note(
            self.args(
                title="What did we learn about retrieval?",
                type="query",
                question="What did we learn about retrieval?",
                body="Use compact results before full notes.",
            )
        )

        self.assertEqual(result["path"], "wiki/queries/What did we learn about retrieval.md")
        note = self.workspace / "wiki" / "queries" / "What did we learn about retrieval.md"
        note_text = note.read_text(encoding="utf-8")
        self.assertIn("type: query", note_text)
        self.assertIn('question: "What did we learn about retrieval?"', note_text)
        self.assertIn("[[What did we learn about retrieval]]", (self.workspace / "wiki" / "index.md").read_text(encoding="utf-8"))

    def test_query_note_can_promote_to_synthesis(self) -> None:
        result = self.module.save_note(
            self.args(
                title="What did we learn about retrieval?",
                type="query",
                question="What did we learn about retrieval?",
                body="Use compact results before full notes.",
                promote_to="synthesis",
            )
        )

        self.assertEqual(result["promoted_path"], "wiki/syntheses/What did we learn about retrieval.md")
        promoted = self.workspace / "wiki" / "syntheses" / "What did we learn about retrieval.md"
        promoted_text = promoted.read_text(encoding="utf-8")
        self.assertIn("type: synthesis", promoted_text)
        self.assertIn("[[What did we learn about retrieval]]", promoted_text)
        self.assertIn("Promoted from saved query", promoted_text)

    def test_save_records_conflict_and_temporal_metadata(self) -> None:
        result = self.module.save_note(
            self.args(
                title="Changing Entity Fact",
                type="entity",
                body="The active blocker changed.",
                contradicts=["[[Old Entity Fact]]"],
                supersedes=["[[Prior Entity Fact]]"],
                observed_at="2026-05-06T09:00:00",
                valid_from="2026-05-06",
                valid_until="2026-06-01",
            )
        )

        self.assertEqual(result["path"], "wiki/entities/Changing Entity Fact.md")
        text = (self.workspace / "wiki" / "entities" / "Changing Entity Fact.md").read_text(encoding="utf-8")
        self.assertIn("contradicts:", text)
        self.assertIn("[[Old Entity Fact]]", text)
        self.assertIn("supersedes:", text)
        self.assertIn("[[Prior Entity Fact]]", text)
        self.assertIn('observed_at: "2026-05-06T09:00:00"', text)
        self.assertIn('valid_from: "2026-05-06"', text)
        self.assertIn('valid_until: "2026-06-01"', text)
        self.assertIn("## Possible Conflict", text)

    def test_save_flags_likely_conflict_before_write(self) -> None:
        self.module.save_note(
            self.args(
                title="Model Routing Decision",
                type="decision",
                body="Model routing uses standard retrieval for architecture decisions.",
            )
        )

        result = self.module.save_note(
            self.args(
                title="Architecture Retrieval Update",
                type="synthesis",
                body="Model routing no longer uses standard retrieval for architecture decisions.",
            )
        )

        self.assertEqual(result["likely_conflicts"], ["wiki/decisions/Model Routing Decision.md"])
        text = (self.workspace / "wiki" / "syntheses" / "Architecture Retrieval Update.md").read_text(encoding="utf-8")
        self.assertIn("Likely conflicts detected before save", text)
        self.assertIn("[[Model Routing Decision]]", text)


if __name__ == "__main__":
    unittest.main()
