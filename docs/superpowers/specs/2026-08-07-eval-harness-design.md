# 评测集扩充设计

## 目标

把 README 中的固定对抗矩阵从“文字清单”升级为可重复执行的评测集：场景写在 `evals/scenarios.json`，由 `evals/runner.py` 确定性运行并生成 `evals/report.md`。新增或修改行为时，先在场景数据中描述预期，再让代码满足预期。

## 范围

- 覆盖 Agent 层状态机与工具编排：追问、地点候选确认、计划修改与重评估、安全拒绝、服务降级、决策依据、可信边界。
- 不访问网络，不调用模型；模型提取结果由 `extractor_updates` 模拟。
- 模型输出层（非 JSON、非法活动类型、提示注入白名单）和 UI 错误路径继续由 `tests/test_extraction.py`、`tests/test_ui.py` 覆盖，不重复搬进评测集。

## 结构

| 文件 | 职责 |
|---|---|
| `evals/scenarios.json` | 场景数据，可读、可编辑、可作提交材料 |
| `evals/runner.py` | 运行场景、汇总分类、生成 Markdown 报告 |
| `evals/fakes.py` | 脚本化提取器、地理编码、天气服务替身 |
| `evals/report.md` | 生成的评测报告（由 runner 输出并提交） |
| `tests/test_evals.py` | 评测集被 unittest 强制执行，任一场景失败即测试失败 |

## 场景字段

| 字段 | 含义 |
|---|---|
| `now` | 会话固定时间，保证过去时间判断可复现 |
| `extractor_updates` | 每次调用依次应用的计划更新，模拟模型提取结果 |
| `geocoder.results` | 每次搜索依次返回的候选集 |
| `geocoder.error` | `GeocodingError` 模拟地理编码服务失败 |
| `weather.points` | 逐小时数据点，字段支持 `rain`、`wind`、`temperature` |
| `weather.error` | `TJWeatherError` 模拟天气服务失败 |
| `steps` | 多轮对话步骤：`message`、`expect_kind`、`message_contains`、`message_not_contains` |
| `expect_geocoder_queries` | 断言地理编码查询顺序 |
| `expect_weather_calls` | 断言天气调用坐标顺序 |
| `expect_no_weather_calls` | 断言不调用天气服务 |
| `expect_extractor_calls` | 断言模型调用次数 |
| `expect_final_plan` | 断言最终计划字段 |

## 对抗矩阵映射

| README 对抗矩阵 | 评测场景 | 说明 |
|---|---|---|
| 1 信息不足只追问 | `agent.001` | 四轮补齐且不调用工具 |
| 2 多地点候选确认 | `agent.004` | 候选必须确认 |
| 3 纯数字选择 | `agent.004` | 步骤 2 使用数字 |
| 4 中文序数词 | `agent.005` | 第二个 |
| 5 唯一名称片段 | `agent.006` | 选北京那个 |
| 6 无效序号不改变状态 | `agent.007` | 0、第两个后仍可正常选择 |
| 7 都不是只清除地点 | `agent.008` | 保留其余计划 |
| 8 候选状态改写地点 | `agent.009` | 重新进入提取与查询 |
| 9 仅标点输入 | `agent.003` | 不调用模型 |
| 10 重新开始清空状态 | `agent.015` | 重置后无旧计划残留 |
| 11 地理编码失败 | `agent.016` | 保留计划并提示重试 |
| 12 天气服务失败 | `agent.017` | 不生成适宜性结论 |
| 13 预报范围外 | `agent.014` | 建议调整时间 |
| 14 城市级近似标注 | `agent.021` | 明确标注近似坐标 |
| 15 无风险显示依据 | `agent.019` | 决策依据与规则结果 |
| 16 有风险显示规则 | `agent.020` | 等级、数值与单位 |
| 17-20 提取与 UI 路径 | 单元测试 | 非 JSON、非法类型、注入白名单、UI 解析失败 |

另含新增行为：`agent.002` 一次性完整计划、`agent.010` 修改时间后重评估、`agent.011` 修改活动类型、`agent.018` 无地点候选。

## 运行方式

```powershell
py -m evals.run
```

输出 `evals/report.md`；有任一场景失败时退出码为 1。评测集同样被 `python -m unittest discover -s tests -v` 强制检查。

## 局限

- 场景数据只表达 Agent 层行为，模型输出质量不在评测范围内。
- 未来若模型替换或提示词变化，`extractor_updates` 仍是手动标注的预期，不随真实模型自动校准。
- 报告不含时间戳，保证每次运行结果可 diff。

