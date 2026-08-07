import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from weather_agent.activity import ActivityPlan
from weather_agent.experts import EXPERT_SKILLS, ExpertContext
from weather_agent.forecast import WeatherForecast, WeatherPoint
from weather_agent.geocoding import LocationCandidate
from weather_agent.knowledge import KnowledgeBase
from weather_agent.risks import assess_weather_risks


TZ = timezone(timedelta(hours=8))
START = datetime(2026, 8, 8, 8, 0, tzinfo=TZ)
FORECAST_INIT = datetime(2026, 8, 4, 8, 0, tzinfo=TZ)


def point(*, rain=0.0, wind=2.0, temperature=25.0):
    return WeatherPoint(
        time=START,
        wind_direction_deg=180,
        wind_speed_m_s=wind,
        temperature_c=temperature,
        relative_humidity_pct=60,
        surface_pressure_pa=100000,
        precipitation_mm_h=rain,
    )


def location():
    return LocationCandidate("北京", 39.9, 116.4, "中国", "北京市", "Asia/Shanghai")


def context(
    *,
    activity="cycling",
    rain=0.0,
    wind=2.0,
    temperature=25.0,
    risk_preference="moderate",
    knowledge=None,
):
    plan = ActivityPlan(activity, "北京", START, 3, risk_preference=risk_preference)
    points = (point(rain=rain, wind=wind, temperature=temperature),)
    forecast = WeatherForecast(FORECAST_INIT, points)
    risks = tuple(assess_weather_risks(points))
    return ExpertContext(
        plan=plan,
        location=location(),
        forecast=forecast,
        points=points,
        risks=risks,
        knowledge=knowledge if knowledge is not None else KnowledgeBase.default(),
    )


def expert(expert_id):
    return next(item for item in EXPERT_SKILLS if item.id == expert_id)


class ExpertRegistryTests(unittest.TestCase):
    def test_registry_has_three_experts_in_order(self):
        self.assertEqual(
            [item.id for item in EXPERT_SKILLS],
            ["weather-interpreter", "outdoor-safety", "gear-advisor"],
        )

    def test_every_expert_has_name_and_description(self):
        for item in EXPERT_SKILLS:
            self.assertTrue(item.name)
            self.assertTrue(item.description)

    def test_weather_and_safety_always_render(self):
        ctx = context()
        for expert_id in ("weather-interpreter", "outdoor-safety"):
            self.assertTrue(expert(expert_id).should_render(ctx))

    def test_gear_advisor_skips_when_no_matching_advice(self):
        ctx = context(activity="camping", wind=9.0)
        self.assertFalse(expert("gear-advisor").should_render(ctx))


class ExpertRenderTests(unittest.TestCase):
    def test_weather_interpreter_renders_plain_language_and_evidence(self):
        rendered = expert("weather-interpreter").render(context(rain=3.0))
        self.assertIn("**气象顾问**", rendered)
        self.assertIn("通俗解读", rendered)
        self.assertIn("**决策依据**：", rendered)
        self.assertIn("规则结果：precipitation medium：3.0 mm/hr", rendered)

    def test_weather_interpreter_marks_approximate_coordinates(self):
        ctx = replace(context(), location=replace(location(), is_approximate=True))
        self.assertIn("城市级近似", expert("weather-interpreter").render(ctx))

    def test_safety_renders_conclusion_and_plans(self):
        rendered = expert("outdoor-safety").render(context(rain=3.0))
        self.assertIn("**户外安全顾问**", rendered)
        self.assertIn("**结论**：检测到天气风险：precipitation medium", rendered)
        self.assertIn("**方案**", rendered)
        self.assertIn("1. 方案一", rendered)

    def test_safety_respects_conservative_preference(self):
        rendered = expert("outdoor-safety").render(
            context(rain=3.0, risk_preference="conservative")
        )
        self.assertIn("**偏好提示**", rendered)
        self.assertIn("保守", rendered)

    def test_gear_advisor_cites_knowledge_source(self):
        rendered = expert("gear-advisor").render(context(rain=3.0))
        self.assertIn("**装备与补给顾问**", rendered)
        self.assertIn("知识库#gear-rain-cycling", rendered)


class ExpertAgentIntegrationTests(unittest.TestCase):
    class _Extractor:
        def __init__(self, plan):
            self.plan = plan

        def update_plan(self, plan, user_message, *, now):
            return self.plan

    class _Geocoder:
        def search(self, query):
            return (location(),)

    class _Weather:
        def __init__(self, payload):
            self.payload = payload

        def fetch(self, *, longitude, latitude):
            return self.payload

    def _payload(self, rain=0.0):
        return {
            "time_init": "2026-08-04T08:00:00+08:00",
            "data": [
                {
                    "time": "2026-08-08T08:00:00+08:00",
                    "wd10m": 180,
                    "ws10m": 2.0,
                    "t2m": 25.0,
                    "rh2m": 60,
                    "psz": 100000,
                    "tp": rain,
                }
            ],
        }

    def _recommendation(self, activity, rain):
        from weather_agent.agent import WeatherAgent

        plan = ActivityPlan(activity, "北京", START, 3)
        agent = WeatherAgent(
            self._Extractor(plan),
            self._Geocoder(),
            self._Weather(self._payload(rain=rain)),
        )
        return agent.handle_message("完整计划", now=START).message

    def test_rainy_recommendation_contains_all_expert_sections(self):
        message = self._recommendation("cycling", rain=3.0)
        for header in ("**气象顾问**", "**户外安全顾问**", "**装备与补给顾问**"):
            self.assertIn(header, message)
        self.assertIn("知识库#gear-rain-cycling", message)

    def test_clear_recommendation_still_uses_all_expert_sections(self):
        message = self._recommendation("hiking", rain=0.0)
        for header in ("**气象顾问**", "**户外安全顾问**", "**装备与补给顾问**"):
            self.assertIn(header, message)
        self.assertIn("未识别到明显天气风险", message)


if __name__ == "__main__":
    unittest.main()
