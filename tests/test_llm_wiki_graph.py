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
MODULE_PATH = SUPPORT / "llm_wiki_graph.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_graph", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["llm_wiki_graph"] = module
    spec.loader.exec_module(module)
    return module


class WikiGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / ".llm-wiki").mkdir()
        (self.workspace / ".llm-wiki" / "config.json").write_text(
            '{"wiki_layer": {"vault_path": ".", "graph_path": "graph/graph.json", "graph_html_path": "graph/graph.html", "tours_path": "wiki/tours"}}',
            encoding="utf-8",
        )
        (self.workspace / "wiki" / "concepts").mkdir(parents=True)
        (self.workspace / "wiki" / "concepts" / "Auth.md").write_text(
            "---\ntype: concept\ntitle: Auth\n---\n\nAuth links to [[Login Flow]].\n",
            encoding="utf-8",
        )
        (self.workspace / "wiki" / "syntheses").mkdir(parents=True)
        (self.workspace / "wiki" / "syntheses" / "Login Flow.md").write_text(
            "---\ntype: synthesis\ntitle: Login Flow\nsources:\n  - Auth\n---\n\nFlow.\n",
            encoding="utf-8",
        )
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_build_graph_extracts_wikilinks_and_writes_artifacts(self) -> None:
        payload = self.module.build_graph(self.workspace, write=True)

        self.assertEqual(len(payload["nodes"]), 2)
        self.assertFalse(payload["cached"])
        self.assertRegex(payload["cache_key"], r"^[0-9a-f]{64}$")
        self.assertTrue(any(edge["source"] == "Auth" and edge["target"] == "Login Flow" for edge in payload["edges"]))
        self.assertTrue((self.workspace / "graph" / "graph.json").exists())
        self.assertTrue((self.workspace / "graph" / "graph.html").exists())

    def test_build_graph_reuses_cache_when_note_hashes_match(self) -> None:
        self.module.build_graph(self.workspace, write=True)

        payload = self.module.build_graph(self.workspace, write=True)

        self.assertTrue(payload["cached"])

    def test_generate_tour_writes_ordered_markdown(self) -> None:
        payload = self.module.generate_tour(self.workspace, topic="onboarding", write=True)

        self.assertTrue(payload["steps"])
        tour = self.workspace / "wiki" / "tours" / "onboarding.md"
        self.assertTrue(tour.exists())
        self.assertIn("# Tour: onboarding", tour.read_text(encoding="utf-8"))

    def test_cli_accepts_workspace_after_subcommand(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), "build", "--workspace", str(self.workspace), "--json"],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(proc.stdout)
        self.assertEqual(len(payload["nodes"]), 2)


if __name__ == "__main__":
    unittest.main()
