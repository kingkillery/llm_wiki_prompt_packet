from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT = REPO_ROOT / "support" / "scripts"
MODULE_PATH = SUPPORT / "llm_wiki_generate.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_generate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class WikiGenerateTests(unittest.TestCase):
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
            "title": "Auth Architecture Map",
            "scope": "authentication flow",
            "type": "synthesis",
            "mode": "page",
            "path": "",
            "section_title": "Runtime Flow",
            "body": "Requests pass through middleware before token validation.",
            "body_file": "",
            "source": ["src/auth/middleware.ts"],
            "related": [],
            "tag": [],
            "diagram_kind": "architecture",
            "no_map": False,
            "no_diagram": False,
        }
        values.update(overrides)
        return Namespace(**values)

    def test_generate_page_creates_map_diagram_and_wiki_indexes(self) -> None:
        result = self.module.generate_wiki(self.args())

        self.assertEqual(result["action"], "created")
        note = self.workspace / "wiki" / "syntheses" / "Auth Architecture Map.md"
        self.assertTrue(note.exists())
        text = note.read_text(encoding="utf-8")
        self.assertIn("## Codebase Map", text)
        self.assertIn("```mermaid", text)
        self.assertIn("authentication flow", text)
        self.assertIn("src/auth/middleware.ts", text)
        self.assertIn("[[Auth Architecture Map]]", (self.workspace / "wiki" / "index.md").read_text(encoding="utf-8"))
        self.assertIn("save | Auth Architecture Map", (self.workspace / "wiki" / "log.md").read_text(encoding="utf-8"))

    def test_upsert_section_updates_existing_page_without_duplicate_section(self) -> None:
        self.module.generate_wiki(self.args())

        result = self.module.generate_wiki(
            self.args(
                mode="upsert-section",
                section_title="Runtime Flow",
                body="Second pass adds route-level behavior.",
                diagram_kind="sequence",
            )
        )

        self.assertEqual(result["action"], "updated")
        note = self.workspace / "wiki" / "syntheses" / "Auth Architecture Map.md"
        text = note.read_text(encoding="utf-8")
        self.assertEqual(text.count("## Runtime Flow"), 1)
        self.assertIn("Second pass adds route-level behavior.", text)
        self.assertIn("sequenceDiagram", text)
        self.assertIn("Action: updated", (self.workspace / "wiki" / "log.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
