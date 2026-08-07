"""Expert-identity skills for the outdoor weather decision agent.

Each expert is a deterministic persona that owns one section of the
recommendation output. The registry in this module is the runtime skill
system: definition (id/name/description), trigger (should_render) and
execution (render). The declarative SKILL.md files under skills/ mirror
these definitions for humans and for a future LLM-tool-calling runtime.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from weather_agent.activity import ActivityPlan
from weather_agent.forecast import WeatherForecast, WeatherPoint
from weather_agent.geocoding import LocationCandidate
from weather_agent.knowledge import KnowledgeBase
from weather_agent.planning import find_clear_window, peak_risks
from weather_agent.risks import RiskAssessment


RISK_LABELS = {
    "precipitation": "降雨",
    "wind": "大风",
    "high_temperature": "高温",
    "low_temperature": "低温",
}
LEVEL_LABELS = {"low": "低", "medium": "中等", "high": "高"}
RISK_IMPACTS = {
    "precipitation": "路面湿滑、能见度下降，雨具与防滑措施要提前备好",
    "wind": "阵风明显，注意平衡并避免在空旷高处长时间逗留",
    "high_temperature": "体感闷热，注意补水与防暑，尽量避开正午时段",
    "low_temperature": "体感偏冷，注意保暖并防范失温风险",
}
RISK_MITIGATION = {
    "precipitation": "携带雨具并避开积水路段",
    "wind": "避开桥梁、空旷与迎风路段",
    "high_temperature": "增加补水并避开正午高温",
    "low_temperature": "注意保暖分层与失温风险",
}


@dataclass(frozen=True)
class ExpertContext:
    plan: ActivityPlan
    location: LocationCandidate
    forecast: WeatherForecast
    points: tuple[WeatherPoint, ...]
    risks: tuple[RiskAssessment, ...]
    knowledge: KnowledgeBase


@dataclass(frozen=True)
class Expert:
    id: str
    name: str
    description: str
    should_render: Callable[[ExpertContext], bool]
    render: Callable[[ExpertContext], str | None]


def _risk_text(risks):
    return "；".join(
        f"{risk.kind} {risk.level}：{risk.value:.1f} {risk.unit}"
        for risk in risks
    )


def _render_weather_interpreter(ctx):
    points = ctx.points
    start = ctx.plan.start_time
    end = start + timedelta(hours=ctx.plan.duration_hours)
    temperatures = [point.temperature_c for point in points]
    peak_rain = max(points, key=lambda p: p.precipitation_mm_h).precipitation_mm_h
    peak_wind = max(points, key=lambda p: p.wind_speed_m_s).wind_speed_m_s

    lines = ["**气象顾问**"]
    summary = (
        f"- 时段概况：{start:%m月%d日 %H:%M}-{end:%H:%M}，"
        f"气温 {min(temperatures):.1f}-{max(temperatures):.1f}°C"
    )
    if peak_rain > 0:
        summary += f"，最高降水 {peak_rain:.1f} mm/hr"
    if peak_wind >= 5.5:
        summary += f"，最大风力 {peak_wind:.1f} m/s"
    lines.append(summary)

    if ctx.risks:
        plain = "；".join(
            f"{RISK_LABELS[risk.kind]}风险为{LEVEL_LABELS[risk.level]}：{RISK_IMPACTS[risk.kind]}"
            for risk in ctx.risks
        )
        lines.append(f"- 通俗解读：活动时段内{plain}。")
    else:
        lines.append("- 通俗解读：活动时段内天气总体平稳，暂无明显不利因素。")

    lines.append("**决策依据**：")
    lines.append(f"- 地点：{ctx.location.display_name}")
    lines.append(
        f"- 活动时段：{start.isoformat()} 起 {ctx.plan.duration_hours:g} 小时"
    )
    lines.append(f"- 预报起报时间：{ctx.forecast.time_init.isoformat()}")
    lines.append(f"- 规则结果：{_risk_text(ctx.risks) or '未识别到明显天气风险'}")
    for risk in peak_risks(ctx.risks):
        lines.append(
            f"- 风险峰值：{risk.kind} {risk.level} "
            f"{risk.value:.1f} {risk.unit}（{risk.time:%H:%M}）"
        )
    if ctx.location.is_approximate:
        lines.append("- 天气坐标为城市级近似；")
    return "\n".join(lines)


def _render_outdoor_safety(ctx):
    lines = ["**户外安全顾问**"]
    if ctx.risks:
        lines.append("已经帮你把这次活动的天气看过了，有几个点需要留意。")
        lines.append(f"**结论**：检测到天气风险：{_risk_text(ctx.risks)}。")
        window = find_clear_window(
            ctx.forecast.points, ctx.plan.start_time, ctx.plan.duration_hours
        )
        if window:
            start, end = window
            names = "、".join(
                RISK_LABELS.get(risk.kind, risk.kind) for risk in ctx.risks
            )
            plan_one = (
                "1. 方案一：建议将活动调整到 "
                f"{start:%m月%d日 %H:%M} 至 {end:%H:%M}，"
                f"该时段未命中{names}风险。"
            )
        else:
            plan_one = "1. 方案一：调整活动时间，避开风险较高的时段后重新查询。"
        mitigations = [
            RISK_MITIGATION[risk.kind]
            for risk in ctx.risks
            if risk.kind in RISK_MITIGATION
        ]
        if mitigations:
            plan_two = (
                "2. 方案二："
                + "；".join(dict.fromkeys(mitigations))
                + "，缩短暴露时间；若风险持续则取消活动。"
            )
        else:
            plan_two = "2. 方案二：改为更短、更易撤离的路线；若风险持续则取消活动。"
    else:
        lines.append("已经帮你把这次活动的天气看好了，整体比较顺利。")
        lines.append("**结论**：当前规则未识别到明显天气风险。")
        plan_one = "1. 方案一：按原计划进行，并在出发前再次核对临近预报。"
        plan_two = "2. 方案二：保留室内或缩短路线作为天气突变时的备选。"
    lines.append("**方案**")
    lines.append(plan_one)
    lines.append(plan_two)
    if ctx.plan.risk_preference == "conservative":
        lines.append("**偏好提示**：你偏好保守，建议优先采用更稳妥的备选方案。")
    elif ctx.plan.risk_preference == "adventurous":
        lines.append("**偏好提示**：你接受较高风险，但请仍以数据结果为准。")
    return "\n".join(lines)


def _gear_topics(ctx):
    return [risk.kind for risk in ctx.risks] or ["general"]


def _gear_advice(ctx):
    return ctx.knowledge.advice_for(
        ctx.plan.activity_type, _gear_topics(ctx), expert="gear-advisor"
    )


def _should_render_gear(ctx):
    return bool(_gear_advice(ctx))


def _render_gear_advisor(ctx):
    advice = _gear_advice(ctx)
    if not advice:
        return None
    lines = ["**装备与补给顾问**"]
    lines.extend(f"- {entry.text}（知识库#{entry.id}）" for entry in advice)
    return "\n".join(lines)


EXPERT_SKILLS = (
    Expert(
        id="weather-interpreter",
        name="气象顾问",
        description="把逐小时预报与风险规则结果翻译成通俗的时段天气解读，并给出可追溯的决策依据。",
        should_render=lambda ctx: True,
        render=_render_weather_interpreter,
    ),
    Expert(
        id="outdoor-safety",
        name="户外安全顾问",
        description="基于风险规则给出结论、方案取舍与应急预案，必要时建议避开风险时段。",
        should_render=lambda ctx: True,
        render=_render_outdoor_safety,
    ),
    Expert(
        id="gear-advisor",
        name="装备与补给顾问",
        description="按活动类型与风险主题检索知识库，给出装备、补给与穿着建议并标注来源。",
        should_render=_should_render_gear,
        render=_render_gear_advisor,
    ),
)
