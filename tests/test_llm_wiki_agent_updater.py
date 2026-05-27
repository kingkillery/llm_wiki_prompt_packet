from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_agent_updater.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_agent_updater", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AgentUpdaterProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_claims_from_markdown_json_response(self) -> None:
        raw = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "```json\n{\"claims\":[\"Codex hooks should stay wired.\"]}\n```"
                        }
                    }
                ]
            }
        )

        claims = self.module.claims_from_response(raw)

        self.assertEqual(claims, ["Codex hooks should stay wired."])

    def test_context_claims_falls_back_to_openrouter(self) -> None:
        def fake_provider(provider: str, _text: str):
            if provider == "siliconflow":
                return [], "siliconflow:missing-api-key"
            if provider == "openrouter":
                return ["OpenRouter can act as cheap context lane."], "openrouter"
            raise AssertionError(provider)

        env = {
            **os.environ,
            "LLM_WIKI_CONTEXT_PROVIDERS": "siliconflow,openrouter",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(self.module, "provider_claims", side_effect=fake_provider):
                claims, provider, statuses = self.module.context_claims("Remember this durable repo fact.")

        self.assertEqual(provider, "openrouter")
        self.assertEqual(claims, ["OpenRouter can act as cheap context lane."])
        self.assertEqual(statuses, ["siliconflow:missing-api-key", "openrouter"])

    def test_read_json_accepts_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text('{"hook_event_name":"UserPromptSubmit"}', encoding="utf-8-sig")

            payload = self.module.read_json(path)

        self.assertEqual(payload["hook_event_name"], "UserPromptSubmit")


if __name__ == "__main__":
    unittest.main()
