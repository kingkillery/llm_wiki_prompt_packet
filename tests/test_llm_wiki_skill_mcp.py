from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_skill_mcp.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_skill_mcp", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SkillPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def make_store(self):
        return self.module.SkillStore(self.workspace)

    def base_payload(self) -> dict[str, object]:
        return {
            "title": "Google Flights dropdown requires suggestion click",
            "kind": "ui",
            "applies_to": ["https://www.google.com/travel/flights*"],
            "goal": "Select an airport after typing a city into Google Flights.",
            "trigger": "Apply when Google Flights ignores the typed city until a suggestion row is clicked.",
            "preconditions": "The location field is focused and the suggestion list has had a moment to render.",
            "fast_path": "1. Type the city.\n2. Wait for the suggestion list.\n3. Click the first matching suggestion instead of pressing Enter.\n4. Continue once the chip appears.",
            "failure_modes": "- The suggestion list can render slowly.\n- Pressing Enter before the list appears does nothing.",
            "evidence": "The first run burned several steps by pressing Enter repeatedly. Re-running with a suggestion click removed the exploration cost and completed cleanly.",
            "important_context": "Google Flights looks obvious, but the typed city does not commit on Enter. The agent has to wait for the suggestion list and click a row. This is easy to miss and expensive to rediscover.",
            "observations": [
                "Typing the city and pressing Enter does not select the location.",
                "The suggestion list appears after a short delay.",
                "Clicking the suggestion row creates the location chip immediately.",
            ],
            "risks": ["The dropdown may render slowly on the first load."],
            "next_actions": ["Poll until the suggestion list appears.", "Click the suggestion row instead of submitting early."],
            "files": ["raw/observations/google-flights.md"],
            "references": ["https://www.google.com/travel/flights"],
            "outcome": "The second run skipped the failed Enter attempts and completed in fewer calls.",
        }

    def test_pipeline_run_creates_skill_and_artifacts(self) -> None:
        store = self.make_store()
        result = store.pipeline_run(self.base_payload())

        self.assertEqual(result["status"], "saved")
        skill = result["skill"]
        self.assertEqual(skill["validation_status"], "validated")
        self.assertTrue(skill["brief_refs"])
        self.assertTrue((self.workspace / result["reflection"]["brief_path"]).exists())
        self.assertTrue((self.workspace / result["packet_path"]).exists())
        self.assertTrue((self.workspace / result["delta_path"]).exists())
        self.assertTrue((self.workspace / result["validation"]["validation_path"]).exists())
        self.assertTrue((self.workspace / "wiki" / "skills" / "active" / f"{skill['id']}.md").exists())
        self.assertEqual(result["packet"]["route_decision"], "complete")
        self.assertIn(skill["id"], result["packet"]["related_skill_ids"])
        self.assertIn(result["delta_path"], result["packet"]["artifact_refs"])
        self.assertIn(result["validation"]["validation_path"], result["packet"]["artifact_refs"])

        log_text = (self.workspace / "wiki" / "log.md").read_text(encoding="utf-8")
        index_text = (self.workspace / "wiki" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertIn("saved", log_text)
        self.assertIn(skill["id"], index_text)
        self.assertIn("packets", store.data)
        self.assertEqual(len(store.data["packets"]), 1)

    def test_reflect_long_task_writes_packet_and_artifact_refs(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["long_task"] = True
        payload["route_decision"] = "escalate_to_parent"
        payload["route_reason"] = "Need parent approval before curating a new reusable skill."
        payload["artifact_refs"] = [".llm-wiki/skill-pipeline/validations/example.json"]

        result = store.reflect(payload)

        self.assertEqual(result["status"], "ok")
        self.assertTrue((self.workspace / result["brief_path"]).exists())
        self.assertTrue((self.workspace / result["packet_path"]).exists())
        self.assertEqual(result["packet"]["route_decision"], "escalate_to_parent")
        self.assertIn(result["brief_path"], result["packet"]["artifact_refs"])
        self.assertNotIn("evidence", result["packet"])
        self.assertNotIn("fast_path", result["packet"])
        self.assertNotIn("failure_modes", result["packet"])

    def test_pipeline_auto_merges_duplicates(self) -> None:
        store = self.make_store()
        first = store.pipeline_run(self.base_payload())

        second_payload = self.base_payload()
        second_payload["title"] = "Google Flights airport suggestion click"
        second_payload["observations"] = second_payload["observations"] + [
            "If the list has multiple airports, choose the exact airport name before continuing."
        ]
        second_payload["failure_modes"] = "- Multiple airports can appear for the same city.\n- Pressing Enter too early still fails."
        second_payload["evidence"] = second_payload["evidence"] + "\nA later run also confirmed the multi-airport case."
        second_payload["route_decision"] = "complete"

        second = store.pipeline_run(second_payload)

        self.assertEqual(second["status"], "merged")
        active_files = list((self.workspace / "wiki" / "skills" / "active").glob("*.md"))
        self.assertEqual(len(active_files), 1)
        self.assertGreaterEqual(len(second["skill"]["brief_refs"]), 2)
        self.assertIn("Multiple airports", second["skill"]["failure_modes"])
        self.assertEqual(first["skill"]["id"], second["target_skill_id"])
        self.assertIn(second["target_skill_id"], second["packet"]["related_skill_ids"])
        self.assertEqual(len(store.list_packets(second["target_skill_id"])), 2)

    def test_pipeline_blocks_pii(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["evidence"] = payload["evidence"] + "\nContact user@example.com before retrying."

        result = store.pipeline_run(payload)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("pii_detected", result["reason"])
        self.assertEqual(list((self.workspace / ".llm-wiki" / "skill-pipeline" / "briefs").glob("*.md")), [])
        self.assertEqual(list((self.workspace / ".llm-wiki" / "skill-pipeline" / "packets").glob("*.json")), [])
        self.assertEqual(store.data["skills"], {})

    def test_validate_requires_route_fields_for_non_complete(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["long_task"] = True
        payload["route_decision"] = "reroute_to_sibling"
        payload["route_reason"] = "Needs a UI-specific agent."

        result = store.validate(payload)

        self.assertEqual(result["status"], "blocked")
        route_checks = {check["name"]: check for check in result["checks"]}
        self.assertEqual(route_checks["route_reroute"]["status"], "fail")
        self.assertIn("assigned_target", route_checks["route_reroute"]["detail"])

    def test_pipeline_run_routes_without_curation_when_non_complete(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["long_task"] = True
        payload["route_decision"] = "retry_same_worker"
        payload["route_reason"] = "Need one more pass to resolve the flaky dropdown timing."
        payload["unresolved_questions"] = ["What is the minimum wait needed before the suggestion row is clickable?"]

        result = store.pipeline_run(payload)

        self.assertEqual(result["status"], "retry_same_worker")
        self.assertEqual(list((self.workspace / "wiki" / "skills" / "active").glob("*.md")), [])
        self.assertEqual(store.data["skills"], {})
        self.assertEqual(result["packet"]["pipeline_status"], "retry_same_worker")
        self.assertIn(result["delta_path"], result["packet"]["artifact_refs"])

    def test_validate_enforces_hop_and_retry_limits(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["long_task"] = True
        payload["route_decision"] = "escalate_to_parent"
        payload["route_reason"] = "Need a higher-level decision on whether this belongs in the skill library."
        payload["artifact_refs"] = [".llm-wiki/skill-pipeline/briefs/example.md"]
        payload["hop_count"] = 3
        payload["retry_count"] = 2

        result = store.validate(payload)

        self.assertEqual(result["status"], "blocked")
        route_checks = {check["name"]: check for check in result["checks"]}
        self.assertEqual(route_checks["hop_budget"]["status"], "fail")
        self.assertEqual(route_checks["retry_budget"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
