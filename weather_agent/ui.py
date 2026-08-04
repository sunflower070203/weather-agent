from datetime import datetime

from weather_agent.agent import WeatherAgent
from weather_agent.extraction import ActivityExtractionError, ActivityExtractor
from weather_agent.geocoding import GeocodingClient
from weather_agent.modelscope import ModelScopeClient, ModelScopeError
from weather_agent.tjweather import TJWeatherClient, TJWeatherConfig, TJWeatherError


EMPTY_PLAN = "尚未填写活动计划。"
ACTIVITY_NAMES = {"cycling": "骑行", "hiking": "徒步", "camping": "露营"}


def create_agent():
    return WeatherAgent(
        ActivityExtractor(ModelScopeClient.from_environment()),
        GeocodingClient(),
        TJWeatherClient(TJWeatherConfig.from_environment()),
    )


def new_session():
    return create_agent()


def format_plan(plan):
    if not any(
        (plan.activity_type, plan.location, plan.start_time, plan.duration_hours)
    ):
        return EMPTY_PLAN
    start = plan.start_time.isoformat() if plan.start_time else "待补充"
    duration = (
        f"{plan.duration_hours:g} 小时" if plan.duration_hours else "待补充"
    )
    return "\n".join(
        (
            f"**活动**：{ACTIVITY_NAMES.get(plan.activity_type, '待补充')}",
            f"**地点**：{plan.location or '待补充'}",
            f"**开始**：{start}",
            f"**时长**：{duration}",
        )
    )


def respond(message, history, agent, *, now=None):
    history = list(history or [])
    if not message or not message.strip():
        history.append(
            {"role": "assistant", "content": "请输入你的户外活动计划。"}
        )
        summary = format_plan(agent.plan) if agent else EMPTY_PLAN
        return "", history, agent, summary

    try:
        agent = agent or new_session()
        result = agent.handle_message(
            message.strip(), now=now or datetime.now().astimezone()
        )
        reply = result.message
        summary = format_plan(result.plan)
    except (ActivityExtractionError, ModelScopeError, TJWeatherError) as exc:
        reply = f"服务配置暂不可用：{exc}"
        summary = format_plan(agent.plan) if agent else EMPTY_PLAN

    history.extend(
        (
            {"role": "user", "content": message.strip()},
            {"role": "assistant", "content": reply},
        )
    )
    return "", history, agent, summary


def reset_session():
    return [], None, EMPTY_PLAN
