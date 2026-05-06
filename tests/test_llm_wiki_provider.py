from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_provider.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_provider", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["llm_wiki_provider"] = module
    spec.loader.exec_module(module)
    return module


class DirectFileWikiProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_read_write_search_round_trip(self) -> None:
        provider = self.module.DirectFileWikiProvider(self.vault)
        result = provider.write("wiki/syntheses/Test Note.md", "A useful research finding.")

        self.assertEqual(result.action, "created")
        self.assertEqual(result.transport, "direct-file")
        self.assertEqual(provider.read("wiki/syntheses/Test Note.md"), "A useful research finding.")
        self.assertTrue(provider.exists("wiki/syntheses/Test Note.md"))
        self.assertEqual(provider.search("research finding")[0]["path"], "wiki/syntheses/Test Note.md")

    def test_rejects_path_traversal(self) -> None:
        provider = self.module.DirectFileWikiProvider(self.vault)
        with self.assertRaises(self.module.WikiProviderError):
            provider.write("../outside.md", "nope")

    def test_provider_from_workspace_uses_wiki_layer_vault(self) -> None:
        workspace = self.vault / "workspace"
        wiki_vault = self.vault / "obsidian"
        (workspace / ".llm-wiki").mkdir(parents=True)
        wiki_vault.mkdir()
        (workspace / ".llm-wiki" / "config.json").write_text(
            '{"wiki_layer": {"vault_path": "../obsidian"}}',
            encoding="utf-8",
        )

        provider = self.module.provider_from_workspace(workspace)

        self.assertEqual(provider.vault_path, wiki_vault.resolve())

    def test_provider_from_workspace_requires_configured_vault_path(self) -> None:
        workspace = self.vault / "workspace"
        (workspace / ".llm-wiki").mkdir(parents=True)
        (workspace / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")

        with self.assertRaisesRegex(self.module.WikiProviderError, "Ask the user where"):
            self.module.provider_from_workspace(workspace)


if __name__ == "__main__":
    unittest.main()
