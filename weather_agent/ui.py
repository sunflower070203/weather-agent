import os
from datetime import datetime

import gradio as gr

from weather_agent.agent import WeatherAgent
from weather_agent.extraction import ActivityExtractionError, ActivityExtractor
from weather_agent.geocoding import GeocodingClient
from weather_agent.modelscope import ModelScopeClient, ModelScopeError
from weather_agent.tjweather import TJWeatherClient, TJWeatherConfig, TJWeatherError


EMPTY_PLAN = "尚未填写活动计划。"
ACTIVITY_NAMES = {"cycling": "骑行", "hiking": "徒步", "camping": "露营"}
DEFAULT_APP_VERSION = "submission-2026-08-07"
APP_CSS = """
:root {
  --forest: #173b32;
  --forest-deep: #0d2923;
  --fog: #f4f3eb;
  --signal: #e86f36;
  --ink: #18332c;
}
.gradio-container {
  background:
    linear-gradient(rgba(23, 59, 50, .035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23, 59, 50, .035) 1px, transparent 1px),
    var(--fog) !important;
  background-size: 32px 32px !important;
  color: var(--ink) !important;
}
#field-header {
  border-left: 7px solid var(--signal);
  padding: 12px 18px;
  margin-bottom: 18px;
}
#field-header h1 { color: var(--forest-deep); letter-spacing: -.02em; }
#field-header p { max-width: 760px; }
#workspace { gap: 18px; align-items: stretch; }
#chat-panel, #plan-panel {
  background: rgba(255, 255, 250, .88);
  border: 1px solid rgba(23, 59, 50, .18);
  box-shadow: 0 14px 35px rgba(13, 41, 35, .08);
  border-radius: 4px;
  padding: 14px;
}
#plan-panel { border-top: 5px solid var(--forest); }
#capabilities {
  border-top: 1px solid rgba(23, 59, 50, .16);
  margin-top: 18px;
  padding-top: 12px;
}
#capabilities ul { padding-left: 1.2em; color: #52665f; }
#send-button { background: var(--signal) !important; color: white !important; }
#reset-button { border-color: var(--forest) !important; color: var(--forest) !important; }
.data-note {
  margin-top: 18px;
  color: #52665f;
  font-size: .88rem;
  border-top: 1px solid rgba(23, 59, 50, .16);
  padding-top: 12px;
}
@media (max-width: 760px) {
  #workspace { flex-direction: column !important; }
  #chat-panel, #plan-panel { min-width: 100% !important; }
}
"""
APP_THEME = gr.themes.Base(
    primary_hue="orange",
    secondary_hue="emerald",
    neutral_hue="stone",
)


def get_app_version(environ=None):
    source = os.environ if environ is None else environ
    value = source.get("WEATHER_AGENT_VERSION", "").strip()
    return value or DEFAULT_APP_VERSION


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
    except ActivityExtractionError:
        reply = (
            "抱歉，我没能可靠理解这次修改，请换一种说法并明确活动、地点、时间或时长。"
        )
        summary = format_plan(agent.plan) if agent else EMPTY_PLAN
    except (ModelScopeError, TJWeatherError) as exc:
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


def build_app(*, version=None):
    version = version or get_app_version()
    with gr.Blocks(title="户外天气决策 Agent") as demo:
        agent_state = gr.State(None)
        gr.Markdown(
            """
# 户外天气决策 Agent

把逐小时天气转化为可执行的骑行、徒步与露营建议。
**数据驱动的辅助判断，不替代气象部门预警和现场安全决策。**
""",
            elem_id="field-header",
        )

        with gr.Row(elem_id="workspace"):
            with gr.Column(scale=7, elem_id="chat-panel"):
                chatbot = gr.Chatbot(
                    value=[],
                    height=470,
                    label="决策对话",
                    placeholder="描述活动、地点、开始时间和预计时长。信息不足时，我会逐项追问。",
                )
                with gr.Row():
                    message = gr.Textbox(
                        placeholder="例如：明天上午8点在北京骑行3小时",
                        show_label=False,
                        scale=8,
                        container=False,
                    )
                    send = gr.Button("分析计划", variant="primary", elem_id="send-button")
                reset = gr.Button("重新开始", variant="secondary", elem_id="reset-button")
            with gr.Column(scale=3, min_width=280, elem_id="plan-panel"):
                gr.Markdown("### 当前活动计划")
                plan_summary = gr.Markdown(EMPTY_PLAN)
                gr.Markdown(
                    """
### 使用提示

- 地点出现多个候选时，可回复“2”“第二个”或“选北京那个”。
- 候选都不合适时回复“都不是”；输入“重新开始”可清空计划。
- 具体公园可能采用城市级天气坐标，结果会明确标注。
- 修改时间或地点后，Agent 会重新查询并评估。
"""
                )
                gr.Markdown(
                    """
### 已启用能力

- 自然语言理解：解析口语活动描述
- 多轮状态：逐项追问并保留活动计划
- 天气工具：中科天机逐小时真实数据
- 风险规则：降雨、大风、高温、低温确定性判断
- 知识库建议：19 条带来源的活动建议
- 风险偏好：保守、适中、冒险口径
- 边界：城市级近似，不替代官方预警

### 已启用专家技能

- 气象顾问：把时段天气翻译成通俗影响并给出决策依据
- 户外安全顾问：风险结论、方案取舍与应急预案
- 装备与补给顾问：按活动与风险给出装备建议（带知识库来源）
""",
                    elem_id="capabilities",
                )

        gr.Examples(
            examples=[
                ["明天上午8点在北京奥林匹克森林公园骑行3小时"],
                ["后天想去天津徒步，大约4小时"],
                ["下周末在上海露营一晚"],
            ],
            inputs=message,
            label="快速示例",
        )
        gr.Markdown(
            "天机天气提供逐小时气象数据；Open-Meteo 用于城市地理编码。"
            "城市级近似不能代表山地、峡谷或水域的局地天气。",
            elem_classes="data-note",
        )
        gr.Markdown(f"运行版本：`{version}`", elem_classes="data-note")

        interaction_inputs = [message, chatbot, agent_state]
        interaction_outputs = [message, chatbot, agent_state, plan_summary]
        message.submit(
            respond,
            inputs=interaction_inputs,
            outputs=interaction_outputs,
        )
        send.click(
            respond,
            inputs=interaction_inputs,
            outputs=interaction_outputs,
        )
        reset.click(
            reset_session,
            outputs=[chatbot, agent_state, plan_summary],
        )
    return demo
