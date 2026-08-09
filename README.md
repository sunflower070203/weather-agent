# 户外天气决策 Agent

面向骑行、徒步、露营场景的多轮对话天气决策 Agent：把口语化的活动描述转成结构化计划，接入真实逐小时天气数据，用确定性规则识别风险，并给出可执行的主方案与备选方案。

- 在线演示：[ModelScope 创空间](https://modelscope.cn/studios/sunh0203/outdoor-weather-agent/summary)
- 参赛作品：天气智能创造营 · 生活服务赛道（提交期 2026-08-10 至 2026-08-16）
- 许可证：MIT

## 功能特性

- 多轮对话补齐活动信息：活动类型、地点、开始时间、时长、参与人群与风险偏好；
- 真实天气数据：中科天机天气 API（1 小时分辨率，最长 10 天预报），模型不编造天气；
- 确定性风险规则：按活动时段识别降雨、大风、高温、低温四类风险，阈值透明可改；
- 数据化方案：方案一给出最近的无风险替代时段，方案二按风险类型给出缓解动作，并附风险峰值证据；
- 三位专家分段推荐：气象顾问、户外安全顾问、装备与补给顾问，推荐附带 `知识库#` 来源；
- 修改后重评估：用户修改时间或地点后保留有效状态，重新查询并更新结论；
- 安全降级：地点歧义需用户确认，预报越界、模型异常或天气服务失败时明确停止，不生成无依据结论；
- 会话内偏好记忆：用户风险偏好只影响建议口径，不影响风险等级。

## 快速开始

```powershell
git clone https://github.com/sunflower070203/weather-agent.git
cd weather-agent
pip install -r requirements.txt
# 先配置环境变量（见下节）
python app.py
```

然后访问 <http://127.0.0.1:7860>。

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `MODELSCOPE_ACCESS_TOKEN` | 是 | ModelScope Access Token，用于调用大模型推理 |
| `TJWEATHER_API_KEY` | 是 | 中科天机天气 API Key |
| `TJWEATHER_SUBSCRIPTION_ID` | 是 | 中科天机天气订阅 ID |
| `WEATHER_AGENT_VERSION` | 否 | 部署版本标识，显示在页面底部 |

密钥只通过环境变量注入，不写入仓库。

## 项目结构

```text
app.py                    # Gradio 入口，监听 0.0.0.0:7860
weather_agent/
  activity.py             # ActivityPlan 活动状态
  extraction.py           # 大模型结构化提取与字段白名单
  geocoding.py            # 地名查询与候选确认
  tjweather.py            # 中科天机天气 API 客户端
  forecast.py             # 预报解析与活动时段筛选
  risks.py                # 四类风险确定性规则
  planning.py             # 替代时段搜索与风险缓解方案
  knowledge.py            # 确定性活动建议与来源标注
  experts.py              # 三位专家分段推荐
  modelscope.py           # 大模型推理客户端（Qwen）
  agent.py                # 会话状态机与编排
  ui.py                   # Gradio 界面与版本标识
data/outdoor-advice.json  # 活动建议语料
skills/                   # 三个声明式专家技能定义
evals/                    # Agent 级确定性评测（29 项场景）
tests/                    # 单元与场景测试（99 项）
docs/                     # 架构、演示、复盘、提交清单与开发记录
```

## 工作原理

语言模型负责理解口语、提取与更新计划字段、组织解释；参数校验、天气请求、时段筛选、风险计算、状态变更和错误分类由确定性程序负责。模型输出先经过类型与字段白名单校验，不能直接成为可信天气事实。

```text
用户输入 -> 结构化提取（LLM + 字段白名单） -> ActivityPlan 状态
  -> 缺失字段追问 / 地点候选确认
  -> 天气工具（真实逐小时数据）
  -> 活动时段筛选
  -> 确定性风险规则（降雨/大风/高温/低温）
  -> 专家技能编排（结论、依据、方案、装备建议）
  -> 用户修改计划 -> 保留状态重新评估
```

原则：能通过明确规则计算的内容，不交给大模型猜测。

## 能力边界

- 支持骑行、徒步、露营三类活动、单个地点、未来 10 天内的预报；
- 风险规则是产品口径，不是官方气象预警，不提供路线级预报；
- 地理编码面向城市更可靠，公园等具体地点在指定城市会降级为城市坐标并明确标注；
- 会话内状态与偏好记忆，无跨会话长期记忆、账号或数据库；
- 采用确定性知识库，不引入向量 RAG、MCP 或插件；
- 单一 Agent，不包含多 Agent 协作、语音、地图或定时提醒。

## 测试与评测

```powershell
python -m unittest discover -s tests -v   # 99 项单元与场景测试
python -m evals.run                       # 29 项确定性 Agent 场景，生成 evals/report.md
```

评测不访问网络、不调用模型，只验证状态机与工具编排；`tests/test_evals.py` 把评测集纳入 unittest，任一场景失败即测试失败。

## 部署到 ModelScope

1. 在[魔搭创空间](https://modelscope.cn/studios/sunh0203/outdoor-weather-agent)同步项目文件，启动入口 `python app.py`；
2. 在创空间配置上表环境变量，部署候选版时将 `WEATHER_AGENT_VERSION` 设为发布标识；
3. 部署后核对页面底部版本号，并用新会话执行一次完整评估、一次修改后重评估；
4. 完整发布门槛见 [docs/submission-checklist.md](docs/submission-checklist.md)。

## 文档

- [Agent 架构与能力边界](docs/architecture.md)
- [三分钟演示脚本](docs/demo-script.md)
- [开发复盘](docs/development-retrospective.md)
- [开发记录](docs/DEVELOPMENT_LOG.md)
- [提交检查清单](docs/submission-checklist.md)
- [确定性评测报告](evals/report.md)

## 许可证

[MIT](LICENSE)
