import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from weather_agent.activity import ActivityPlan
from weather_agent.forecast import WeatherPoint
from weather_agent.geocoding import LocationCandidate


BEIJING_TZ = timezone(timedelta(hours=8))
START = datetime(2026, 8, 6, 8, 0, tzinfo=BEIJING_TZ)


class FakeExtractor:
    def __init__(self, plans):
        self.plans = iter(plans)

    def update_plan(self, plan, user_message, *, now):
        return next(self.plans)


class FakeGeocoder:
    def __init__(self, candidates):
        self.candidates = candidates
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return self.candidates


class FakeWeather:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    def fetch(self, *, longitude, latitude):
        self.calls.append((longitude, latitude))
        if self.error:
            raise self.error
        return self.payload


def candidate(name, latitude, longitude, admin1):
    return LocationCandidate(name, latitude, longitude, "中国", admin1, "Asia/Shanghai")


def forecast_payload(*, rain=0.0, wind=2.0, temperature=25.0):
    return {
        "time_init": "2026-08-04T08:00:00+08:00",
        "data": [
            {
                "time": "2026-08-06T08:00:00+08:00",
                "wd10m": 180,
                "ws10m": wind,
                "t2m": temperature,
                "rh2m": 60,
                "psz": 100000,
                "tp": rain,
            }
        ],
    }


class WeatherAgentTests(unittest.TestCase):
    def test_asks_next_question_without_calling_tools_when_plan_is_incomplete(self):
        from weather_agent.agent import WeatherAgent

        extractor = FakeExtractor([ActivityPlan(activity_type="cycling")])
        geocoder = FakeGeocoder(())
        weather = FakeWeather()

        result = WeatherAgent(extractor, geocoder, weather).handle_message(
            "我想骑行", now=START
        )

        self.assertEqual(result.kind, "question")
        self.assertEqual(result.message, "活动地点在哪里？")
        self.assertEqual(geocoder.queries, [])
        self.assertEqual(weather.calls, [])

    def test_requests_confirmation_when_location_has_multiple_candidates(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "奥森公园", START, 3)
        candidates = (
            candidate("奥林匹克森林公园", 40.02, 116.39, "北京"),
            candidate("奥林森林公园", 41.10, 123.00, "辽宁"),
        )
        agent = WeatherAgent(
            FakeExtractor([plan]), FakeGeocoder(candidates), FakeWeather()
        )

        result = agent.handle_message("后天去奥森公园骑行三小时", now=START)

        self.assertEqual(result.kind, "location_choice")
        self.assertEqual(result.candidates, candidates)
        self.assertIn("1.", result.message)
        self.assertIn("2.", result.message)

    def test_confirmed_location_runs_weather_and_reports_rule_based_risk(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "奥森公园", START, 3)
        place = candidate("奥林匹克森林公园", 40.02, 116.39, "北京")
        weather = FakeWeather(forecast_payload(rain=3.0))
        agent = WeatherAgent(FakeExtractor([plan]), FakeGeocoder((place,)), weather)

        result = agent.handle_message("完整计划", now=START)

        self.assertEqual(result.kind, "recommendation")
        self.assertEqual(weather.calls, [(116.39, 40.02)])
        self.assertEqual(result.risks[0].kind, "precipitation")
        self.assertEqual(result.risks[0].level, "medium")
        self.assertIn("方案一", result.message)
        self.assertIn("方案二", result.message)
        self.assertIn("3.0 mm/hr", result.message)

    def test_numeric_location_choice_uses_selected_candidate(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "奥森公园", START, 3)
        first = candidate("奥林匹克森林公园", 40.02, 116.39, "北京")
        second = candidate("奥林森林公园", 41.10, 123.00, "辽宁")
        weather = FakeWeather(forecast_payload())
        agent = WeatherAgent(
            FakeExtractor([plan]), FakeGeocoder((first, second)), weather
        )

        agent.handle_message("完整计划", now=START)
        result = agent.handle_message("2", now=START)

        self.assertEqual(result.kind, "recommendation")
        self.assertEqual(weather.calls, [(123.00, 41.10)])

    def test_chinese_ordinal_selects_candidate(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "森林公园", START, 3)
        first = candidate("天津森林公园", 39.1, 117.2, "天津")
        second = candidate("北京森林公园", 40.0, 116.4, "北京")
        weather = FakeWeather(forecast_payload())
        agent = WeatherAgent(FakeExtractor([]), FakeGeocoder(()), weather)
        agent.plan = plan
        agent.pending_locations = (first, second)

        result = agent.handle_message("第二个", now=START)

        self.assertEqual(result.kind, "recommendation")
        self.assertEqual(weather.calls, [(116.4, 40.0)])

    def test_unique_candidate_text_selects_candidate(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "森林公园", START, 3)
        first = candidate("天津森林公园", 39.1, 117.2, "天津")
        second = candidate("北京森林公园", 40.0, 116.4, "北京")
        weather = FakeWeather(forecast_payload())
        agent = WeatherAgent(FakeExtractor([]), FakeGeocoder(()), weather)
        agent.plan = plan
        agent.pending_locations = (first, second)

        agent.handle_message("选北京那个", now=START)

        self.assertEqual(weather.calls, [(116.4, 40.0)])

    def test_ambiguous_candidate_text_keeps_pending_choices(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "森林公园", START, 3)
        places = (
            candidate("北京东城森林公园", 39.9, 116.4, "北京"),
            candidate("北京西山森林公园", 39.9, 116.2, "北京"),
        )
        agent = WeatherAgent(FakeExtractor([]), FakeGeocoder(()), FakeWeather())
        agent.plan = plan
        agent.pending_locations = places

        result = agent.handle_message("选北京那个", now=START)

        self.assertEqual(result.kind, "location_choice")
        self.assertEqual(agent.pending_locations, places)

    def test_invalid_candidate_numbers_keep_pending_choices(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "森林公园", START, 3)
        places = (candidate("北京森林公园", 40.0, 116.4, "北京"),)
        agent = WeatherAgent(FakeExtractor([]), FakeGeocoder(()), FakeWeather())
        agent.plan = plan
        agent.pending_locations = places

        for message in ("0", "2", "第两个"):
            with self.subTest(message=message):
                result = agent.handle_message(message, now=START)
                self.assertEqual(result.kind, "location_choice")
                self.assertEqual(agent.pending_locations, places)

    def test_none_of_candidates_clears_only_location(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "森林公园", START, 3)
        places = (candidate("北京森林公园", 40.0, 116.4, "北京"),)
        agent = WeatherAgent(FakeExtractor([]), FakeGeocoder(()), FakeWeather())
        agent.plan = plan
        agent.pending_locations = places

        result = agent.handle_message("都不是", now=START)

        self.assertEqual(result.kind, "question")
        self.assertEqual(result.message, "请提供更具体的活动地点。")
        self.assertIsNone(result.plan.location)
        self.assertEqual(result.plan.activity_type, "cycling")
        self.assertEqual(agent.pending_locations, ())

    def test_new_location_during_choice_reenters_extraction(self):
        from weather_agent.agent import WeatherAgent

        old = ActivityPlan("cycling", "森林公园", START, 3)
        corrected = ActivityPlan("cycling", "北京奥森", START, 3)
        place = candidate("北京奥森", 40.0, 116.4, "北京")
        agent = WeatherAgent(
            FakeExtractor([corrected]),
            FakeGeocoder((place,)),
            FakeWeather(forecast_payload()),
        )
        agent.plan = old
        agent.pending_locations = (
            candidate("天津森林公园", 39.1, 117.2, "天津"),
        )

        result = agent.handle_message("改成北京奥森", now=START)

        self.assertEqual(result.kind, "recommendation")
        self.assertEqual(result.plan.location, "北京奥森")
        self.assertEqual(agent.pending_locations, ())

    def test_activity_change_during_choice_is_applied_and_acknowledged(self):
        from weather_agent.agent import WeatherAgent

        old = ActivityPlan("hiking", "上海", START, 4)
        updated = ActivityPlan("camping", "上海", START, 4)
        places = (
            candidate("上海", 31.23, 121.47, "上海市"),
            candidate("上海", 29.00, 120.00, "浙江"),
        )
        extractor = Mock()
        extractor.update_plan.return_value = updated
        agent = WeatherAgent(extractor, FakeGeocoder(places), FakeWeather())
        agent.plan = old
        agent.pending_locations = places

        result = agent.handle_message("改成露营", now=START)

        self.assertEqual(result.kind, "location_choice")
        self.assertEqual(result.plan.activity_type, "camping")
        self.assertIn("已更新计划", result.message)
        extractor.update_plan.assert_called_once_with(old, "改成露营", now=START)

    def test_unrelated_text_during_choice_keeps_candidates_without_extraction(self):
        from weather_agent.agent import WeatherAgent

        places = (
            candidate("上海", 31.23, 121.47, "上海市"),
            candidate("上海", 29.00, 120.00, "浙江"),
        )
        extractor = Mock()
        agent = WeatherAgent(extractor, FakeGeocoder(()), FakeWeather())
        agent.plan = ActivityPlan("hiking", "上海", START, 4)
        agent.pending_locations = places

        result = agent.handle_message("天气怎么样", now=START)

        self.assertEqual(result.kind, "location_choice")
        self.assertEqual(result.candidates, places)
        extractor.update_plan.assert_not_called()

    def test_weather_failure_returns_safe_error_without_recommendation(self):
        from weather_agent.agent import WeatherAgent
        from weather_agent.tjweather import TJWeatherError

        plan = ActivityPlan("hiking", "香山", START, 2)
        place = candidate("香山", 39.99, 116.18, "北京")
        weather = FakeWeather(error=TJWeatherError("timeout"))
        agent = WeatherAgent(FakeExtractor([plan]), FakeGeocoder((place,)), weather)

        result = agent.handle_message("完整计划", now=START)

        self.assertEqual(result.kind, "error")
        self.assertIn("无法获取天气数据", result.message)
        self.assertNotIn("适合", result.message)

    def test_marks_city_level_coordinates_as_approximate(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "北京奥林匹克森林公园", START, 3)
        place = replace(
            candidate("北京", 39.91, 116.40, "北京市"),
            resolved_query="北京",
            is_approximate=True,
        )
        agent = WeatherAgent(
            FakeExtractor([plan]),
            FakeGeocoder((place,)),
            FakeWeather(forecast_payload()),
        )

        result = agent.handle_message("完整计划", now=START)

        self.assertIn("城市级近似", result.message)

    def test_safe_recommendation_labels_public_decision_evidence(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "北京", START, 3)
        place = candidate("北京", 40.0, 116.4, "北京")
        agent = WeatherAgent(
            FakeExtractor([plan]),
            FakeGeocoder((place,)),
            FakeWeather(forecast_payload()),
        )

        result = agent.handle_message("完整计划", now=START)

        self.assertIn("决策依据：", result.message)
        self.assertIn("规则结果：未识别到明显天气风险", result.message)
        self.assertIn("预报起报时间", result.message)

    def test_risky_recommendation_labels_triggered_rule_evidence(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "北京", START, 3)
        place = candidate("北京", 40.0, 116.4, "北京")
        agent = WeatherAgent(
            FakeExtractor([plan]),
            FakeGeocoder((place,)),
            FakeWeather(forecast_payload(rain=3.0)),
        )

        result = agent.handle_message("完整计划", now=START)

        self.assertIn("决策依据：", result.message)
        self.assertIn("规则结果：precipitation medium", result.message)

    def test_punctuation_only_message_does_not_call_extractor(self):
        from weather_agent.agent import WeatherAgent

        extractor = Mock()
        agent = WeatherAgent(extractor, FakeGeocoder(()), FakeWeather())

        result = agent.handle_message("？！……", now=START)

        self.assertEqual(result.kind, "question")
        self.assertIn("有效", result.message)
        extractor.update_plan.assert_not_called()

    def test_reset_command_clears_plan_and_pending_candidates(self):
        from weather_agent.agent import WeatherAgent

        agent = WeatherAgent(Mock(), FakeGeocoder(()), FakeWeather())
        agent.plan = ActivityPlan("cycling", "北京", START, 3)
        agent.pending_locations = (
            candidate("北京", 40.0, 116.4, "北京"),
        )

        result = agent.handle_message("重新开始", now=START)

        self.assertEqual(result.kind, "reset")
        self.assertEqual(result.plan, ActivityPlan())
        self.assertEqual(agent.pending_locations, ())

    def test_geocoding_failure_preserves_plan_and_suggests_retry(self):
        from weather_agent.agent import WeatherAgent
        from weather_agent.geocoding import GeocodingError

        plan = ActivityPlan("cycling", "北京", START, 3)
        geocoder = Mock()
        geocoder.search.side_effect = GeocodingError("timeout")
        agent = WeatherAgent(FakeExtractor([plan]), geocoder, FakeWeather())

        result = agent.handle_message("完整计划", now=START)

        self.assertEqual(result.plan, plan)
        self.assertIn("重试", result.message)

    def test_out_of_range_forecast_suggests_time_change(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "北京", START, 3)
        place = candidate("北京", 40.0, 116.4, "北京")
        payload = forecast_payload()
        payload["data"][0]["time"] = "2026-08-07T08:00:00+08:00"
        agent = WeatherAgent(
            FakeExtractor([plan]),
            FakeGeocoder((place,)),
            FakeWeather(payload),
        )

        result = agent.handle_message("完整计划", now=START)

        self.assertIn("调整活动时间", result.message)

    def test_past_start_time_is_rejected_before_geocoding(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "北京", START - timedelta(hours=1), 3)
        geocoder = FakeGeocoder((candidate("北京", 40.0, 116.4, "北京市"),))
        weather = FakeWeather(forecast_payload())
        agent = WeatherAgent(FakeExtractor([plan]), geocoder, weather)

        result = agent.handle_message("昨天在北京骑行三小时", now=START)

        self.assertEqual(result.kind, "question")
        self.assertIn("未来时间", result.message)
        self.assertEqual(geocoder.queries, [])
        self.assertEqual(weather.calls, [])

    def test_duration_over_seven_days_is_rejected_before_geocoding(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("cycling", "北京", START, 1000)
        geocoder = FakeGeocoder((candidate("北京", 40.0, 116.4, "北京市"),))
        weather = FakeWeather(forecast_payload())
        agent = WeatherAgent(FakeExtractor([plan]), geocoder, weather)

        result = agent.handle_message("在北京骑行一千小时", now=START)

        self.assertEqual(result.kind, "question")
        self.assertIn("缩短", result.message)
        self.assertEqual(geocoder.queries, [])
        self.assertEqual(weather.calls, [])

    def test_recommendation_appends_knowledge_advice_with_source(self):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan("camping", "北京", START, 3)
        place = candidate("北京", 40.0, 116.4, "北京")
        agent = WeatherAgent(
            FakeExtractor([plan]),
            FakeGeocoder((place,)),
            FakeWeather(forecast_payload(temperature=36.0)),
        )

        result = agent.handle_message("完整计划", now=START)

        self.assertEqual(result.kind, "recommendation")
        self.assertIn("知识库#", result.message)


if __name__ == "__main__":
    unittest.main()
