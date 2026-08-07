# 知识建议能力设计（Skill 化第一步）

## 第一性原则取舍

户外决策场景存在真实需求：用户想知道“这种天气做这个活动要注意什么”。建议必须可追溯，不能由模型自由发挥。

本阶段只做确定性知识库：

- 语料：`data/outdoor-advice.json`，按活动和风险主题组织；
- 检索：`KnowledgeBase.advice_for` 按活动与主题确定性匹配，取前两条；
- 引用：建议末尾标注 `（知识库#id）`，可回溯到语料条目。

明确不做并说明理由：

- 向量 RAG：需要嵌入模型与向量库，增加部署和评测成本，当前语料规模下收益不匹配；
- MCP：当前是确定性状态机驱动工具调用，不是 LLM 自由工具调用。引入 MCP 会重写编排并破坏评测集，先保留演进设计；
- 插件：本部署是 Gradio 创空间，没有插件宿主，不适用；
- 长期记忆：`ActivityPlan` 已有 `risk_preference` 等字段但无消费者，本轮先不新造记忆机制。

## 演进路径（不实现）

若未来切换为 LLM 工具调用架构，`advice_for`、天气查询、地理编码可统一映射为 MCP tools：

```text
tool weather_forecast(longitude, latitude) -> ForecastPayload
tool geocode_location(query) -> LocationCandidates
tool outdoor_advice(activity, topics) -> AdviceWithSource
```

届时评测集负责验证工具选择与参数，而不是只验证页面可用。

## 语料格式

| 字段 | 含义 |
|---|---|
| `id` | 唯一条目标识，展示为 `知识库#id` |
| `activity` | `cycling`、`hiking`、`camping` 或 `any` |
| `topics` | 风险主题：`precipitation`、`wind`、`high_temperature`、`low_temperature`、`general` |
| `text` | 建议正文 |

## 检索算法

- 活动精确匹配或命中任一风险主题才进入候选；
- 活动精确匹配 2 分，`any` 条目 1 分；
- 命中任一风险主题 3 分；
- 按分数降序、`id` 升序排序，取前 2 条。

## 评测

- 单元测试：语料加载、主题匹配、无风险回退、排序与数量限制；
- Agent 测试：推荐语包含 `知识库#` 来源；
- 评测场景 `agent.022`：高温露营建议附带来源与风险等级。

## 局限

语料是人工整理的通用建议，不替代官方预警和现场判断；检索无语义泛化，新增语料需要人工维护条目。
