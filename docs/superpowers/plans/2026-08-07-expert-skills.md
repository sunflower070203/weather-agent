# 专家技能（Skill=专家身份）执行计划

- [x] 第一性原则取舍：专家身份 = 人设 + 知识挂载 + 输出职责；确定性调度，不引入 LLM 自由工具调用；
- [x] 新增 `weather_agent/experts.py`：`Expert` 注册表与 `ExpertContext`，3 位专家（气象顾问/户外安全顾问/装备与补给顾问）；
- [x] `data/outdoor-advice.json` 增加 `expert` 字段并扩充到 19 条；`KnowledgeBase.advice_for` 支持 `expert` 过滤；
- [x] `agent.py` 推荐渲染改为专家编排；保留结论/决策依据/风险峰值/方案/知识来源/偏好提示全部既有断言；
- [x] `ui.py` 右侧面板展示“已启用专家技能”；
- [x] `skills/<id>/SKILL.md` 三个声明式技能定义（frontmatter name/description，正文输出契约）；
- [x] `tests/test_experts.py` 与评估场景 `agent.028/029`；本地全量测试与评估通过后推送分支。

后续路线：若切换为 LLM 工具调用架构，三位专家可映射为 `interpret_weather` / `plan_outdoor_safety` / `recommend_gear` 三个工具。
