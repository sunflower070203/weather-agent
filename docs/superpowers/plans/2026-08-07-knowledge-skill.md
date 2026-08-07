# 知识建议能力执行计划

- [x] 第一性原则取舍：只做确定性知识库，推迟 MCP、向量 RAG 与插件。
- [x] 新增 `weather_agent/knowledge.py` 与 `data/outdoor-advice.json`（12 条语料）。
- [x] Agent 推荐语附带 `知识库#id` 来源。
- [x] 新增 `tests/test_knowledge.py`、Agent 级来源测试与评测场景 `agent.022`。
- [x] 更新 README、架构文档与设计文档。
- [x] 本地验证全部测试与评测后推送分支。

后续路线：会话内偏好记忆（消费已有 `risk_preference` 字段），最后再评估多 Agent。
