from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT = REPO_ROOT / "support" / "scripts"
MODULE_PATH = SUPPORT / "llm_wiki_search.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_search", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["llm_wiki_search"] = module
    spec.loader.exec_module(module)
    return module


class WikiSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / ".llm-wiki").mkdir()
        (self.workspace / ".llm-wiki" / "config.json").write_text('{"wiki_layer": {"vault_path": "."}}', encoding="utf-8")
        (self.workspace / "wiki" / "concepts").mkdir(parents=True)
        (self.workspace / "wiki" / "concepts" / "Retrieval Routing.md").write_text(
            "---\ntype: concept\ntitle: Retrieval Routing\n---\n\nRetrieval routing uses compact search before full note content.\n",
            encoding="utf-8",
        )
        (self.workspace / "wiki" / "log.md").write_text(
            "# Wiki Log\n\n## [2026-05-06] save | Retrieval Routing\n- Location: wiki/concepts/Retrieval Routing.md\n",
            encoding="utf-8",
        )
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_search_index_returns_compact_ids_without_full_content(self) -> None:
        payload = self.module.search_index(self.workspace, "retrieval routing", limit=3)

        self.assertEqual(payload["results"][0]["id"], "r1")
        self.assertEqual(payload["results"][0]["path"], "wiki/concepts/Retrieval Routing.md")
        self.assertIn("snippet", payload["results"][0])
        self.assertNotIn("content", payload["results"][0])

    def test_timeline_and_get_fetch_selected_context(self) -> None:
        timeline = self.module.timeline(self.workspace, "Retrieval Routing")
        full = self.module.get_records(self.workspace, ["wiki/concepts/Retrieval Routing.md"])

        self.assertTrue(timeline["entries"])
        self.assertIn("full note content", full["records"][0]["content"])


if __name__ == "__main__":
    unittest.main()
