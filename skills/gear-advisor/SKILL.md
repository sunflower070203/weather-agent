---
name: gear-advisor
description: 装备与补给顾问技能，按活动类型与风险主题检索确定性知识库，给出装备、补给与穿着建议并标注知识库来源。当 Agent 需要给出针对性的装备清单或补给建议时使用。
---

# 装备与补给顾问（Gear Advisor）

职责：输出装备、补给与穿着建议，每条建议标注知识库来源。

触发：推荐方案生成阶段，当知识库中存在与活动类型、风险主题匹配的装备类条目时渲染本段；无匹配条目不输出。

输入：`ExpertContext`（活动计划、地点、预报、时段点、风险结果、知识库）。

输出契约：

- 段标题：`**装备与补给顾问**`
- 建议行：`- {建议}（知识库#{id}）`
- 检索：`KnowledgeBase.advice_for(activity, topics, expert="gear-advisor")`

实现：`weather_agent/experts.py` 中 `_render_gear_advisor`。语料位于 `data/outdoor-advice.json`，按 `expert` 字段归属本技能。本文件为声明式定义，运行时以代码注册表为准。

未来迁移：若切换为 LLM 工具调用架构，本技能可映射为 `tool recommend_gear(context) -> str`，或由 LLM 直接读取本文件作为角色指令。
