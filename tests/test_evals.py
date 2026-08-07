import json
import unittest

from evals.runner import EVALS_DIR, run_all, run_scenario


MINIMAL_SCENARIO = {
    "id": "test.001",
    "category": "测试",
    "name": "最小通过场景",
    "now": "2026-08-05T08:00:00+08:00",
    "extractor_updates": [
        {
            "activity_type": "cycling",
            "location": "北京",
            "start_time": "2026-08-08T08:00:00+08:00",
            "duration_hours": 3,
        }
    ],
    "geocoder": {
        "results": [
            [
                {
                    "name": "北京",
                    "latitude": 39.9,
                    "longitude": 116.4,
                    "admin1": "北京市",
                    "country": "中国",
                    "timezone": "Asia/Shanghai",
                }
            ]
        ]
    },
    "weather": {"points": [{"time": "2026-08-08T08:00:00+08:00"}]},
    "steps": [{"message": "完整计划", "expect_kind": "recommendation"}],
    "expect_weather_calls": [[116.4, 39.9]],
}

FAILING_SCENARIO = {
    **MINIMAL_SCENARIO,
    "id": "test.002",
    "steps": [{"message": "完整计划", "expect_kind": "error"}],
}


class ScenarioFileTests(unittest.TestCase):
    def load_scenarios(self):
        return json.loads(
            (EVALS_DIR / "scenarios.json").read_text(encoding="utf-8")
        )

    def test_scenarios_file_has_unique_ids_and_core_fields(self):
        scenarios = self.load_scenarios()
        ids = [scenario["id"] for scenario in scenarios]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(scenarios), 21)
        for scenario in scenarios:
            for field in ("id", "category", "name", "now", "steps"):
                self.assertIn(field, scenario)
            for step in scenario["steps"]:
                self.assertIn("message", step)
                self.assertIn("expect_kind", step)

    def test_all_scenarios_pass(self):
        scenarios = self.load_scenarios()
        report = run_all(scenarios)
        failures = [item for item in report["results"] if not item["passed"]]
        self.assertEqual(
            report["passed"],
            report["total"],
            "\n".join(
                f"{item['id']}: {'; '.join(item['failures'])}"
                for item in failures
            ),
        )


class RunnerTests(unittest.TestCase):
    def test_runner_marks_passing_scenario(self):
        result = run_scenario(MINIMAL_SCENARIO)
        self.assertTrue(result["passed"], result["failures"])

    def test_runner_reports_step_failure(self):
        result = run_scenario(FAILING_SCENARIO)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("kind expected" in item for item in result["failures"])
        )

    def test_report_aggregates_by_category(self):
        report = run_all([MINIMAL_SCENARIO, FAILING_SCENARIO])
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["passed"], 1)
        self.assertEqual(report["by_category"]["测试"]["total"], 2)
        self.assertEqual(report["by_category"]["测试"]["passed"], 1)


if __name__ == "__main__":
    unittest.main()

