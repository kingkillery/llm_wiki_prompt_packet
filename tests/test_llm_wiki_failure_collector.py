from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT_DIR = REPO_ROOT / "support" / "scripts"
FAILURE_MODULE_PATH = SUPPORT_DIR / "llm_wiki_failure_collector.py"
SKILL_MODULE_PATH = SUPPORT_DIR / "llm_wiki_skill_mcp.py"

if str(SUPPORT_DIR) not in sys.path:
    sys.path.insert(0, str(SUPPORT_DIR))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FailureCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_module = load_module("llm_wiki_skill_mcp", SKILL_MODULE_PATH)
        self.failure_module = load_module("llm_wiki_failure_collector", FAILURE_MODULE_PATH)
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / ".llm-wiki").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_config(self, threshold: int = 2, min_unique_sessions: int = 2) -> None:
        config = {
            "skills": {
                "pipeline": {
                    "failure_event_dir": ".llm-wiki/skill-pipeline/failures/events",
                    "failure_cluster_dir": ".llm-wiki/skill-pipeline/failures/clusters",
                    "failure_benchmark_dir": ".llm-wiki/skill-pipeline/failures/benchmarks",
                    "failure_promotion_threshold": threshold,
                    "failure_promotion_window_hours": 168,
                    "failure_promotion_min_unique_sessions": min_unique_sessions,
                }
            }
        }
        (self.workspace / ".llm-wiki" / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    def base_failure(self) -> dict[str, object]:
        return {
            "title": "Google Flights dropdown ambiguity",
            "kind": "ui",
            "goal": "Select an airport after typing a city into Google Flights.",
            "problem": "The agent stalls when Google Flights shows multiple airport rows for one city.",
            "trigger": "Apply when multiple airport rows appear and the location chip never commits.",
            "url_pattern": "https://www.google.com/travel/flights*",
            "evidence": "The agent hesitated at the airport dropdown and failed to select a row until a human pointed at the exact airport option.",
            "observations": [
                "Multiple airport rows can appear for the same city.",
                "Clicking the exact airport row resolves the ambiguity.",
            ],
            "tool_name": "browser_click",
            "error_class": "ambiguous_airport_suggestion",
            "error_message": "The agent did not choose a suggestion row.",
            "route_decision": "complete",
        }

    def test_record_writes_event_and_cluster_summary(self) -> None:
        self.write_config()
        collector = self.failure_module.FailureCollector(self.workspace)
        payload = self.base_failure() | {"session_id": "session-1", "trace_id": "trace-1"}

        result = collector.record(payload)

        self.assertEqual(result["status"], "recorded")
        self.assertTrue((self.workspace / result["event_path"]).exists())
        self.assertEqual(result["cluster"]["count"], 1)
        self.assertTrue((self.workspace / result["cluster"]["cluster_path"]).exists())

    def test_promote_repeated_failures_calls_skill_evolve(self) -> None:
        self.write_config(threshold=2, min_unique_sessions=2)
        collector = self.failure_module.FailureCollector(self.workspace)

        collector.record(self.base_failure() | {"session_id": "session-1", "trace_id": "trace-1"})
        collector.record(
            self.base_failure()
            | {
                "session_id": "session-2",
                "trace_id": "trace-2",
                "evidence": "A second run failed the same way until the exact airport row was clicked.",
            }
        )

        result = collector.promote()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["promoted"]), 1)
        promotion = result["promoted"][0]
        self.assertEqual(promotion["evolve_result"]["status"], "accepted")
        self.assertTrue((self.workspace / promotion["benchmark_path"]).exists())
        self.assertTrue((self.workspace / promotion["evolve_result"]["proposal_path"]).exists())
        self.assertTrue((self.workspace / promotion["evolve_result"]["surrogate_review_path"]).exists())
        self.assertTrue((self.workspace / promotion["evolve_result"]["evolution_run_path"]).exists())

        frontier = self.skill_module.SkillStore(self.workspace).list_frontier()
        self.assertEqual(len(frontier), 1)

        pending = collector.list_events(include_promoted=False)
        self.assertEqual(pending, [])

    def test_promote_preserves_subjective_pairwise_fields(self) -> None:
        self.write_config(threshold=2, min_unique_sessions=2)
        collector = self.failure_module.FailureCollector(self.workspace)
        subjective_failure = self.base_failure() | {
            "title": "Google Flights subjective guidance comparison",
            "verification_mode": "subjective_pairwise",
            "subjective_task": "Choose the better guidance for resolving the airport dropdown ambiguity.",
            "baseline_output": "Type the city and press Enter until it works.",
            "candidate_output": "Type the city, wait for suggestions, then click the exact airport row.",
        }

        collector.record(subjective_failure | {"session_id": "session-1", "trace_id": "trace-1"})
        collector.record(subjective_failure | {"session_id": "session-2", "trace_id": "trace-2"})

        result = collector.promote()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["promoted"]), 1)
        promotion = result["promoted"][0]
        evolve_payload = promotion["benchmark"]["evolve_payload"]
        self.assertEqual(evolve_payload["verification_mode"], "subjective_pairwise")
        self.assertEqual(evolve_payload["subjective_task"], subjective_failure["subjective_task"])
        self.assertEqual(evolve_payload["baseline_output"], subjective_failure["baseline_output"])
        self.assertEqual(evolve_payload["candidate_output"], subjective_failure["candidate_output"])
        self.assertEqual(promotion["evolve_result"]["surrogate_review"]["verification_mode"], "subjective_pairwise")


if __name__ == "__main__":
    unittest.main()
