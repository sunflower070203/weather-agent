from dataclasses import dataclass
from datetime import timedelta

from weather_agent.activity import ActivityPlan
from weather_agent.forecast import ForecastDataError, WeatherForecast
from weather_agent.geocoding import GeocodingError, LocationCandidate
from weather_agent.risks import RiskAssessment, assess_weather_risks
from weather_agent.tjweather import TJWeatherError


ORDINAL_CHOICES = {
    "第一个": 0,
    "第二个": 1,
    "第三个": 2,
    "第四个": 3,
    "第五个": 4,
}
NONE_OF_THESE = {"都不是", "没有合适的", "重新选地点"}


@dataclass(frozen=True)
class AgentResult:
    kind: str
    message: str
    plan: ActivityPlan
    candidates: tuple[LocationCandidate, ...] = ()
    risks: tuple[RiskAssessment, ...] = ()


class WeatherAgent:
    def __init__(self, extractor, geocoder, weather):
        self.extractor = extractor
        self.geocoder = geocoder
        self.weather = weather
        self.plan = ActivityPlan()
        self.pending_locations = ()

    def handle_message(self, message, *, now):
        text = message.strip()
        if not text or not any(character.isalnum() for character in text):
            return AgentResult(
                "question", "请补充有效的活动信息。", self.plan
            )
        if text in {"重新开始", "重置", "清空计划"}:
            self.plan = ActivityPlan()
            self.pending_locations = ()
            return AgentResult(
                "reset", "已重新开始，请告诉我计划的户外活动。", self.plan
            )

        if self.pending_locations:
            if text in NONE_OF_THESE:
                self.pending_locations = ()
                self.plan = self.plan.with_updates({"location": None})
                return AgentResult(
                    "question", "请提供更具体的活动地点。", self.plan
                )

            selected_index = self._candidate_index(text)
            if selected_index is not None:
                selected = self.pending_locations[selected_index]
                self.pending_locations = ()
                return self._evaluate(selected)

            if text.isdigit() or (text.startswith("第") and text.endswith("个")):
                return self._location_choice_result(self.pending_locations)

            self.pending_locations = ()

        self.plan = self.extractor.update_plan(self.plan, message, now=now)
        if not self.plan.is_ready():
            return AgentResult("question", self.plan.next_question(), self.plan)

        try:
            candidates = self.geocoder.search(self.plan.location)
        except GeocodingError:
            return AgentResult(
                "error", "地点查询失败，请稍后重试或提供更明确的地点。", self.plan
            )

        if not candidates:
            return AgentResult(
                "error", "没有找到这个地点，请补充城市或行政区。", self.plan
            )
        if len(candidates) > 1:
            self.pending_locations = tuple(candidates)
            return self._location_choice_result(self.pending_locations)
        return self._evaluate(candidates[0])

    def _candidate_index(self, text):
        if text.isdigit():
            index = int(text) - 1
            return index if 0 <= index < len(self.pending_locations) else None

        if text in ORDINAL_CHOICES:
            index = ORDINAL_CHOICES[text]
            return index if index < len(self.pending_locations) else None

        matches = [
            index
            for index, candidate in enumerate(self.pending_locations)
            if candidate.display_name in text
            or (candidate.admin1 and candidate.admin1 in text)
        ]
        return matches[0] if len(matches) == 1 else None

    def _location_choice_result(self, candidates):
        choices = "\n".join(
                f"{index}. {candidate.display_name}"
                for index, candidate in enumerate(candidates, start=1)
            )
        return AgentResult(
            "location_choice",
            f"找到多个可能地点，请回复序号确认：\n{choices}",
            self.plan,
            candidates=tuple(candidates),
        )

    def _evaluate(self, location):
        try:
            payload = self.weather.fetch(
                longitude=location.longitude, latitude=location.latitude
            )
            forecast = WeatherForecast.from_api(payload)
            end_time = self.plan.start_time + timedelta(
                hours=self.plan.duration_hours
            )
            points = forecast.between(self.plan.start_time, end_time)
        except (TJWeatherError, ForecastDataError, KeyError, TypeError, ValueError):
            return AgentResult(
                "error",
                "无法获取天气数据，因此不能可靠评估本次活动，请稍后重试。",
                self.plan,
            )

        if not points:
            return AgentResult(
                "error",
                "活动时间不在当前有效预报范围内，无法进行可靠评估。"
                "请调整活动时间后重新查询。",
                self.plan,
            )

        risks = tuple(assess_weather_risks(points))
        return AgentResult(
            "recommendation",
            self._format_recommendation(location, forecast, points, risks),
            self.plan,
            risks=risks,
        )

    def _format_recommendation(self, location, forecast, points, risks):
        approximation = (
            "天气坐标为城市级近似；" if location.is_approximate else ""
        )
        evidence = (
            f"地点：{location.display_name}；活动时段："
            f"{self.plan.start_time.isoformat()} 起 {self.plan.duration_hours:g} 小时；"
            f"{approximation}预报起报时间：{forecast.time_init.isoformat()}。"
        )
        if not risks:
            return (
                f"当前规则未识别到明显天气风险。{evidence}\n"
                "方案一：按原计划进行，并在出发前再次核对临近预报。\n"
                "方案二：保留室内或缩短路线作为天气突变时的备选。"
            )

        risk_text = "；".join(
            f"{risk.kind} {risk.level}：{risk.value:.1f} {risk.unit}"
            for risk in risks
        )
        return (
            f"检测到天气风险：{risk_text}。{evidence}\n"
            "方案一：调整活动时间，避开风险较高的时段后重新查询。\n"
            "方案二：改为更短、更易撤离的路线；若风险持续则取消活动。"
        )
