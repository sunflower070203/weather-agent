# 评测集扩充执行计划

- [x] 从冻结 main 建立独立分支 `codex/eval-harness`，线上版本保持不变。
- [x] 建立 `evals/` 包：假对象、场景数据、运行器。
- [x] 编写 21 项 Agent 级确定性场景，覆盖 README 对抗矩阵 1-16 及新增行为。
- [x] 实现 `python -m evals.run` 生成 `evals/report.md`。
- [x] 新增 `tests/test_evals.py`，评测集纳入 unittest 强制回归。
- [x] 更新 README 测试范围、进度表和开发记录。
- [x] 本地运行全部测试与评测，确认通过后提交分支。

后续路线：按价值排序为 Skill 化工具边界、会话内偏好记忆、多 Agent。
