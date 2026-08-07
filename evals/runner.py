"""Run scenario data against a scripted WeatherAgent and write a report.

Usage:
    python -m evals.run [scenarios.json] [report.md]

The runner is fully deterministic: no network, no model, no randomness.
It verifies the agent's state machine and tool orchestration only.
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime

from weather_agent.agent import WeatherAgent

from evals.fakes import (
    FakeGeocoder,
    FakeWeather,
    ScriptedExtractor,
    candidate_from_dict,
    geocoding_error,
    weather_error,
)

EVALS_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_SCENARIOS = EVALS_DIR / "scenarios.json"
DEFAULT_REPORT = EVALS_DIR / "report.md"
DEFAULT_TIME_INIT = "2026-08-04T08:00:00+08:00"


def _build_weather_payload(spec):
    data = []
    for point in spec.get("points", []):
        data.append(
            {
                "time": point["time"],
                "wd10m": point.get("wd10m", 180),
                "ws10m": point.get("wind", 2.0),
                "t2m": point.get("temperature", 25.0),
                "rh2m": point.get("rh2m", 60),
                "psz": point.get("psz", 100000),
                "tp": point.get("rain", 0.0),
            }
        )
    return {"time_init": spec.get("time_init", DEFAULT_TIME_INIT), "data": data}


def _plan_checks(plan, expected):
    failures = []
    for field, value in (expected or {}).items():
        actual = getattr(plan, field)
        if field == "start_time" and isinstance(value, str):
            value = datetime.fromisoformat(value)
        if actual != value:
            failures.append(f"plan.{field}: expected {value!r}, got {actual!r}")
    return failures


def run_scenario(scenario):
    failures = []
    now = datetime.fromisoformat(scenario["now"])

    extractor = ScriptedExtractor(scenario.get("extractor_updates", []))
    geocoder_spec = scenario.get("geocoder", {})
    geocoder = FakeGeocoder(
        [
            [candidate_from_dict(item) for item in results]
            for results in geocoder_spec.get("results", [])
        ],
        error=geocoding_error(geocoder_spec.get("error")),
    )
    weather_spec = scenario.get("weather", {})
    weather = FakeWeather(
        payload=None if weather_spec.get("error") else _build_weather_payload(weather_spec),
        error=weather_error(weather_spec.get("error")),
    )
    agent = WeatherAgent(extractor, geocoder, weather)

    for index, step in enumerate(scenario["steps"], start=1):
        result = agent.handle_message(step["message"], now=now)
        if result.kind != step["expect_kind"]:
            failures.append(
                f"step {index}: kind expected {step['expect_kind']}, got {result.kind}"
            )
        for snippet in step.get("message_contains", []):
            if snippet not in result.message:
                failures.append(
                    f"step {index}: message missing {snippet!r}: {result.message!r}"
                )
        for snippet in step.get("message_not_contains", []):
            if snippet in result.message:
                failures.append(
                    f"step {index}: message unexpectedly contains {snippet!r}"
                )

    expected_queries = scenario.get("expect_geocoder_queries")
    if expected_queries is not None and geocoder.queries != expected_queries:
        failures.append(
            f"geocoder queries: expected {expected_queries}, got {geocoder.queries}"
        )
    expected_calls = scenario.get("expect_weather_calls")
    if expected_calls is not None and weather.calls != [
        tuple(call) for call in expected_calls
    ]:
        failures.append(
            f"weather calls: expected {expected_calls}, got {weather.calls}"
        )
    if scenario.get("expect_no_weather_calls") and weather.calls:
        failures.append(f"weather should not be called, got {weather.calls}")
    expected_extractor = scenario.get("expect_extractor_calls")
    if expected_extractor is not None and extractor.calls != expected_extractor:
        failures.append(
            f"extractor calls: expected {expected_extractor}, got {extractor.calls}"
        )
    failures.extend(_plan_checks(agent.plan, scenario.get("expect_final_plan")))

    return {
        "id": scenario["id"],
        "category": scenario["category"],
        "name": scenario["name"],
        "passed": not failures,
        "failures": failures,
    }


def run_all(scenarios):
    results = [run_scenario(scenario) for scenario in scenarios]
    by_category = {}
    for result in results:
        counts = by_category.setdefault(
            result["category"], {"total": 0, "passed": 0}
        )
        counts["total"] += 1
        if result["passed"]:
            counts["passed"] += 1
    return {
        "results": results,
        "by_category": by_category,
        "total": len(results),
        "passed": sum(result["passed"] for result in results),
    }


def write_report(report, path):
    lines = [
        "# Agent 确定性评测报告",
        "",
        "评测不访问网络或模型，只验证状态机与工具编排。",
        "",
        f"通过 {report['passed']}/{report['total']} 项。",
        "",
        "| 分类 | 通过/总数 |",
        "|---|---|",
    ]
    for category, counts in sorted(report["by_category"].items()):
        lines.append(f"| {category} | {counts['passed']}/{counts['total']} |")
    lines.extend(
        [
            "",
            "| ID | 分类 | 场景 | 结果 | 失败原因 |",
            "|---|---|---|---|---|",
        ]
    )
    for result in report["results"]:
        status = "通过" if result["passed"] else "失败"
        reason = "；".join(result["failures"]) or "-"
        lines.append(
            f"| {result['id']} | {result['category']} | {result['name']} "
            f"| {status} | {reason} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    scenarios_path = pathlib.Path(args[0]) if args else DEFAULT_SCENARIOS
    report_path = pathlib.Path(args[1]) if len(args) > 1 else DEFAULT_REPORT
    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))
    report = run_all(scenarios)
    write_report(report, report_path)
    print(f"{report['passed']}/{report['total']} scenarios passed")
    for result in report["results"]:
        if not result["passed"]:
            print(
                f"FAIL {result['id']} {result['name']}: "
                f"{'; '.join(result['failures'])}"
            )
    print(f"report written to {report_path}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

