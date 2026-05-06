from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT = REPO_ROOT / "support" / "scripts"
MODULE_PATH = SUPPORT / "llm_wiki_lint.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_lint", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["llm_wiki_lint"] = module
    spec.loader.exec_module(module)
    return module


class WikiLintTests(unittest.TestCase):
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

    def write_note(self, rel: str, text: str) -> None:
        path = self.workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_lint_reports_broken_links_missing_frontmatter_and_duplicates(self) -> None:
        self.write_note(
            "wiki/concepts/Auth.md",
            "---\ntype: concept\ntitle: Auth\n---\n\nSee [[Missing Page]].\n",
        )
        self.write_note(
            "wiki/syntheses/Auth.md",
            "---\ntype: synthesis\ntitle: Auth\nsources: []\n---\n\nDuplicate title.\n",
        )
        self.write_note("wiki/sources/Raw Note.md", "No frontmatter here.")

        payload = self.module.lint_workspace(self.workspace)
        codes = {item["code"] for item in payload["findings"]}

        self.assertIn("broken-wikilink", codes)
        self.assertIn("missing-frontmatter", codes)
        self.assertIn("duplicate-title", codes)
        self.assertEqual(payload["page_count"], 3)
        self.assertGreaterEqual(payload["summary"]["error"], 2)

    def test_lint_reports_unresolved_contradiction_and_entity_observation(self) -> None:
        self.write_note(
            "wiki/entities/Project Status.md",
            "---\ntype: entity\ntitle: Project Status\ncontradicts:\n  - Old Status\n---\n\nBody.\n",
        )

        payload = self.module.lint_workspace(self.workspace)
        codes = {item["code"] for item in payload["findings"]}

        self.assertIn("unresolved-contradiction", codes)
        self.assertIn("entity-without-observation", codes)


if __name__ == "__main__":
    unittest.main()
