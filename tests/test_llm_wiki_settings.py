from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT = REPO_ROOT / "support" / "scripts"
MODULE_PATH = SUPPORT / "llm_wiki_settings.py"


def load_module():
    if str(SUPPORT) not in sys.path:
        sys.path.insert(0, str(SUPPORT))
    spec = importlib.util.spec_from_file_location("llm_wiki_settings", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["llm_wiki_settings"] = module
    spec.loader.exec_module(module)
    return module


class ProviderSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / ".llm-wiki").mkdir()
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_resolves_precedence_from_env_to_defaults(self) -> None:
        (self.workspace / ".llm-wiki" / "config.json").write_text(
            '{"provider_settings": {"provider": "packet", "model": "packet-model", "timeout_ms": 100}, '
            '"wiki_compile": {"output_language": "en"}}',
            encoding="utf-8",
        )
        (self.workspace / ".llm-wiki" / "agent-settings.json").write_text(
            '{"provider_settings": {"model": "agent-model", "endpoint": "http://agent"}}',
            encoding="utf-8",
        )
        (self.workspace / ".env").write_text(
            "LLM_WIKI_MODEL=env-file-model\nLLM_WIKI_TIMEOUT_MS=200\n",
            encoding="utf-8",
        )

        payload = self.module.resolve_provider_settings(
            self.workspace,
            environ={"LLM_WIKI_MODEL": "shell-model", "LLM_WIKI_PROVIDER": "shell-provider"},
        )

        self.assertEqual(payload["settings"]["provider"], "shell-provider")
        self.assertEqual(payload["sources"]["provider"], "environment")
        self.assertEqual(payload["settings"]["model"], "shell-model")
        self.assertEqual(payload["sources"]["model"], "environment")
        self.assertEqual(payload["settings"]["timeout_ms"], 200)
        self.assertEqual(payload["sources"]["timeout_ms"], ".env")
        self.assertEqual(payload["settings"]["endpoint"], "http://agent")
        self.assertEqual(payload["sources"]["endpoint"], "agent_settings")
        self.assertEqual(payload["settings"]["language"], "en")
        self.assertEqual(payload["sources"]["language"], "packet_config")

    def test_uses_defaults_when_no_settings_exist(self) -> None:
        (self.workspace / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")

        payload = self.module.resolve_provider_settings(self.workspace, environ={})

        self.assertEqual(payload["settings"]["provider"], "direct-file")
        self.assertEqual(payload["settings"]["timeout_ms"], 600000)
        self.assertEqual(payload["sources"]["provider"], "defaults")


if __name__ == "__main__":
    unittest.main()
