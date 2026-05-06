from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT = REPO_ROOT / "support" / "scripts"
MODULE_PATH = SUPPORT / "llm_wiki_memory_capture.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_memory_capture", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["llm_wiki_memory_capture"] = module
    spec.loader.exec_module(module)
    return module


class MemoryCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / ".llm-wiki").mkdir()
        (self.workspace / ".llm-wiki" / "config.json").write_text(
            json.dumps(
                {
                    "memory_capture": {
                        "candidate_only": True,
                        "pii_sensitive": True,
                        "deny_paths": ["secret"],
                        "deny_generated_artifacts": True,
                    }
                }
            ),
            encoding="utf-8",
        )
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_capture_creates_candidate_and_strips_private_pii(self) -> None:
        result = self.module.capture_event(
            self.workspace,
            event="session-end",
            observation="Useful fact. <private>do not store this</private> Email me@example.com",
            tags=["wiki"],
        )

        self.assertTrue(result["captured"])
        payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "candidate")
        self.assertIn("Useful fact", payload["observation"])
        self.assertNotIn("do not store", payload["observation"])
        self.assertIn("[email omitted]", payload["observation"])
        self.assertEqual(payload["session_summary"][0], "Useful fact. [private content omitted] Email [email omitted]")

    def test_capture_skips_denied_paths_and_private_only_content(self) -> None:
        denied = self.module.capture_event(
            self.workspace,
            event="post-tool-use",
            observation="Sensitive report",
            source_path="reporting/tracking/export.json",
        )
        private_only = self.module.capture_event(
            self.workspace,
            event="post-tool-use",
            observation="<private>only secret</private>",
        )

        self.assertFalse(denied["captured"])
        self.assertEqual(denied["reason"], "source_path_denied")
        self.assertFalse(private_only["captured"])
        self.assertEqual(private_only["reason"], "empty_after_privacy_filter")


if __name__ == "__main__":
    unittest.main()
