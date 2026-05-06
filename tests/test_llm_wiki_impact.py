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
MODULE_PATH = SUPPORT / "llm_wiki_impact.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_impact", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["llm_wiki_impact"] = module
    spec.loader.exec_module(module)
    return module


class WikiImpactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        subprocess.run(["git", "init"], cwd=self.workspace, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.workspace, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.workspace, check=True)
        (self.workspace / ".llm-wiki").mkdir()
        (self.workspace / ".llm-wiki" / "config.json").write_text('{"wiki_layer": {"vault_path": "."}}', encoding="utf-8")
        (self.workspace / "app").mkdir()
        (self.workspace / "app" / "auth.py").write_text("def login(): pass\n", encoding="utf-8")
        (self.workspace / "wiki" / "concepts").mkdir(parents=True)
        (self.workspace / "wiki" / "concepts" / "Auth.md").write_text(
            "---\ntype: concept\ntitle: Auth\n---\n\nThe auth.py file owns login behavior.\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=self.workspace, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.workspace, check=True, capture_output=True)
        (self.workspace / "app" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_diff_impact_reports_related_wiki_pages(self) -> None:
        payload = self.module.impact_report(self.workspace, base="HEAD")

        self.assertEqual(payload["summary"]["changed_file_count"], 1)
        self.assertTrue(any(item["wiki_page"] == "wiki/concepts/Auth.md" for item in payload["impacted_pages"]))

    def test_write_report_updates_meta_and_reports_folder(self) -> None:
        payload = self.module.impact_report(self.workspace, base="HEAD")

        reports = self.module.write_report(self.workspace, payload)

        self.assertEqual(reports["wiki_report_path"], "wiki/meta/diff-impact.md")
        self.assertTrue((self.workspace / "wiki" / "meta" / "diff-impact.md").exists())
        self.assertTrue((self.workspace / ".llm-wiki" / "reports" / "diff-impact.json").exists())

    def test_cli_accepts_workspace_after_subcommand(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), "diff", "--workspace", str(self.workspace), "--base", "HEAD", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(proc.stdout)
        self.assertEqual(payload["summary"]["changed_file_count"], 1)


if __name__ == "__main__":
    unittest.main()
