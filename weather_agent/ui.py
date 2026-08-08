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
  --paper: #f5efe1;
  --paper-deep: #efe7d4;
  --ink: #2b2722;
  --forest: #1f4a3a;
  --forest-deep: #143026;
  --signal: #e2622b;
  --muted: #7c7261;
  --serif: "Songti SC", "STSong", "Noto Serif SC", "SimSun", serif;
}
.gradio-container {
  background:
    radial-gradient(circle at 12% 8%, rgba(226, 98, 43, .07), transparent 34%),
    radial-gradient(circle at 88% 92%, rgba(31, 74, 58, .07), transparent 40%),
    repeating-linear-gradient(0deg, rgba(43, 39, 34, .028) 0 1px, transparent 1px 26px),
    var(--paper) !important;
  color: var(--ink) !important;
  font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", "Helvetica Neue", sans-serif !important;
}
@keyframes field-rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
#field-header {
  animation: field-rise .5s ease-out both;
}
#field-header .field-hero {
  position: relative;
  overflow: hidden;
  border-left: 8px solid var(--signal);
  background:
    radial-gradient(circle at 84% 22%, rgba(242, 161, 90, .14), transparent 34%),
    linear-gradient(100deg, rgba(255, 252, 244, .9), rgba(255, 252, 244, .55) 58%, rgba(207, 224, 232, .42));
  box-shadow: 0 18px 44px rgba(31, 74, 58, .10);
  border-radius: 12px 12px 4px 4px;
  padding: 26px 30px 20px;
  margin: 0 0 18px;
}
#field-header .hero-art {
  position: absolute;
  top: 18px;
  right: 18px;
  height: 128px;
  opacity: .95;
  pointer-events: none;
}
#field-header .hero-art svg { height: 100%; width: auto; display: block; }
#field-header .overline {
  margin: 0 300px 6px 0;
  font-family: var(--serif);
  font-size: .78rem;
  letter-spacing: .18em;
  color: var(--signal);
  font-weight: 700;
}
#field-header h1 {
  margin: 0 300px 0 0;
  font-family: var(--serif);
  font-size: 2.1rem;
  line-height: 1.15;
  color: var(--forest-deep);
  letter-spacing: .02em;
}
#field-header .tagline { margin: 8px 300px 0 0; max-width: 620px; color: var(--muted); font-size: .98rem; }
#field-header .note { margin: 4px 300px 0 0; max-width: 620px; font-size: .86rem; color: var(--muted); }
#field-header .expert-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
  max-width: 62%;
  position: relative;
  z-index: 1;
}
#field-header .stamp {
  font-family: var(--serif);
  font-weight: 700;
  font-size: .9rem;
  color: var(--forest-deep);
  background: rgba(255, 252, 244, .72);
  border: 1.5px dashed var(--forest);
  border-radius: 999px;
  padding: 6px 14px;
  transform: rotate(-1.2deg);
  box-shadow: 0 2px 0 rgba(31, 74, 58, .08);
}
#field-header .stamp:nth-child(2) { transform: rotate(.8deg); border-color: var(--signal); }
#field-header .stamp:nth-child(3) { transform: rotate(-.6deg); }
#workspace {
  gap: 18px;
  align-items: stretch;
  animation: field-rise .5s ease-out .12s both;
}
#chat-panel, #plan-panel {
  position: relative;
  background: rgba(255, 252, 244, .86);
  border: 1px solid rgba(43, 39, 34, .13);
  border-radius: 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .65), 0 18px 44px rgba(31, 74, 58, .10);
  padding: 22px 22px 18px;
}
#chat-panel::before, #plan-panel::before {
  content: "";
  position: absolute;
  top: -12px; left: 50%;
  width: 96px; height: 26px;
  transform: translateX(-50%) rotate(-1.6deg);
  background: rgba(226, 98, 43, .15);
  border: 1px dashed rgba(43, 39, 34, .22);
  border-radius: 3px;
  pointer-events: none;
}
#plan-panel h3, #capabilities h3 {
  margin: 0 0 12px;
  font-family: var(--serif);
  font-size: 1.05rem;
  color: var(--forest-deep);
  letter-spacing: .04em;
}
#capabilities h3 { margin-top: 14px; font-size: .98rem; }
#plan-summary {
  position: relative;
  background: rgba(255, 253, 248, .92);
  border-left: 4px solid var(--signal);
  border-radius: 0 8px 8px 0;
  padding: 12px 14px;
  margin: 6px 0 18px;
  font-size: .9rem;
  line-height: 1.7;
}
#plan-summary::after {
  content: "PLAN";
  position: absolute;
  top: 10px; right: 12px;
  font-family: var(--serif);
  font-size: .68rem;
  letter-spacing: .16em;
  color: rgba(226, 98, 43, .75);
  border: 1px solid rgba(226, 98, 43, .45);
  border-radius: 3px;
  padding: 2px 7px;
  transform: rotate(5deg);
}
#capabilities {
  border-top: 1px dashed rgba(43, 39, 34, .16);
  margin-top: 18px;
  padding-top: 12px;
}
#capabilities ul { padding-left: 1.2em; color: var(--muted); line-height: 1.85; }
#send-button {
  background: var(--signal) !important;
  color: #fff !important;
  border-radius: 8px !important;
  font-weight: 700 !important;
  transition: filter .15s ease, transform .1s ease !important;
}
#send-button:hover { filter: brightness(1.07) !important; }
#send-button:active { transform: scale(.97) !important; }
#reset-button {
  border: 1px solid var(--forest) !important;
  color: var(--forest) !important;
  background: transparent !important;
  border-radius: 8px !important;
}
#reset-button:hover { background: rgba(31, 74, 58, .08) !important; }
.data-note {
  margin-top: 18px;
  color: var(--muted);
  font-size: .86rem;
  border-top: 1px solid rgba(43, 39, 34, .14);
  padding-top: 12px;
  animation: field-rise .5s ease-out .22s both;
}
#chat-panel ::-webkit-scrollbar, #plan-panel ::-webkit-scrollbar { width: 8px; }
#chat-panel ::-webkit-scrollbar-thumb, #plan-panel ::-webkit-scrollbar-thumb {
  background: rgba(43, 39, 34, .22);
  border-radius: 999px;
}
@media (max-width: 760px) {
  #workspace { flex-direction: column !important; }
  #chat-panel, #plan-panel { min-width: 100% !important; }
  #field-header h1 { font-size: 1.65rem; }
  #field-header .field-hero { padding: 20px 20px 16px; }
  #field-header .hero-art { display: none; }
  #field-header .overline,
  #field-header h1,
  #field-header .tagline,
  #field-header .note {
    margin-right: 0;
  }
  #field-header .expert-badges { max-width: 100%; }
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
        gr.HTML(
            """
<div class="field-hero">
  <div class="hero-art" aria-hidden="true">
    <svg viewBox="0 0 460 200" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#dcebef"/><stop offset="1" stop-color="#f3ead6"/>
        </linearGradient>
      </defs>
      <rect width="460" height="200" fill="url(#sky)"/>
      <circle cx="368" cy="58" r="26" fill="#f2a15a" opacity=".92"/>
      <path d="M0 150 L118 74 L210 142 L286 96 L380 150 L460 118 L460 200 L0 200 Z" fill="#3f6b58" opacity=".9"/>
      <path d="M0 200 L0 170 L96 116 L168 164 L252 128 L344 178 L460 140 L460 200 Z" fill="#1f4a3a" opacity=".95"/>
    </svg>
  </div>
  <p class="overline">OUTDOOR WEATHER NOTE · 户外天气手帐</p>
  <h1>户外天气决策 Agent</h1>
  <p class="tagline">把逐小时天气转化为可执行的骑行、徒步与露营建议。</p>
  <p class="note">数据驱动的辅助判断，不替代气象部门预警和现场安全决策。</p>
  <div class="expert-badges">
    <span class="stamp">🌦️ 气象顾问</span>
    <span class="stamp">🦺 户外安全顾问</span>
    <span class="stamp">🎒 装备与补给顾问</span>
  </div>
</div>
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
                plan_summary = gr.Markdown(EMPTY_PLAN, elem_id="plan-summary")
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

- 🧠 自然语言理解：解析口语活动描述
- 🔄 多轮状态：逐项追问并保留活动计划
- 🌤️ 天气工具：中科天机逐小时真实数据
- ⚠️ 风险规则：降雨、大风、高温、低温确定性判断
- 📚 知识库建议：19 条带来源的活动建议
- 🎯 风险偏好：保守、适中、冒险口径
- 📍 边界：城市级近似，不替代官方预警

### 已启用专家技能

- 🌦️ 气象顾问：把时段天气翻译成通俗影响并给出决策依据
- 🦺 户外安全顾问：风险结论、方案取舍与应急预案
- 🎒 装备与补给顾问：按活动与风险给出装备建议（带知识库来源）
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
