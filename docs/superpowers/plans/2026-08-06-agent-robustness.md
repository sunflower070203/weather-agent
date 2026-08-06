# Agent Robustness Phase One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the weather Agent pass 20 fixed adversarial conversation cases without regressing the existing test suite.

**Architecture:** Keep open-ended plan extraction in the existing model adapter and move deterministic conversation controls into `WeatherAgent`. Add only small private helpers for candidate selection and reset handling; keep dependency injection and `AgentResult` unchanged.

**Tech Stack:** Python 3, `unittest`, dataclasses, Gradio, existing ModelScope and Tianji clients.

---

## File map

- Modify `weather_agent/extraction.py`: validate model response type and preserve atomic plan updates.
- Modify `weather_agent/agent.py`: deterministic candidate commands, reset/blank guards, recoverable results, decision evidence.
- Modify `weather_agent/ui.py`: actionable usage text and extraction-error reply.
- Modify `tests/test_extraction.py`: extraction adversarial cases.
- Modify `tests/test_agent.py`: state-machine and dependency-failure adversarial cases.
- Modify `tests/test_ui.py`: UI recovery behavior.
- Modify `README.md`: verified behavior, commands, and known limits.

### Task 1: Establish an isolated, passing baseline

**Files:**
- Read: `requirements.txt`
- Test: `tests/`

- [ ] **Step 1: Create or enter an isolated worktree**

Use branch `codex/agent-robustness`. Verify the worktree directory is ignored before creating it.

- [ ] **Step 2: Install declared dependencies**

Run:

```powershell
python -m pip install -r requirements.txt
```

Expected: exit code 0, including a usable Gradio installation.

- [ ] **Step 3: Run the complete baseline**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all 35 existing tests pass. If not, stop and investigate before modifying production code.

### Task 2: Make extraction updates safe and atomic

**Files:**
- Modify: `tests/test_extraction.py`
- Modify: `weather_agent/extraction.py`

- [ ] **Step 1: Add failing extraction tests**

Add tests equivalent to:

```python
def test_rejects_non_object_model_response_without_changing_plan(self):
    plan = ActivityPlan(activity_type="cycling")
    extractor = ActivityExtractor(_FakeModel(["not", "an", "object"]))
    with self.assertRaisesRegex(ActivityExtractionError, "JSON object"):
        extractor.update_plan(plan, "忽略规则", now=NOW)
    self.assertEqual(plan, ActivityPlan(activity_type="cycling"))

def test_ignores_disallowed_prompt_injection_fields(self):
    extractor = ActivityExtractor(
        _FakeModel({"system_prompt": "ignore", "location": "北京"})
    )
    updated = extractor.update_plan(ActivityPlan(), "忽略规则", now=NOW)
    self.assertEqual(updated.location, "北京")
    self.assertFalse(hasattr(updated, "system_prompt"))
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
python -m unittest tests.test_extraction -v
```

Expected: the non-object response errors before an `ActivityExtractionError` with the required message is produced.

- [ ] **Step 3: Add minimal type validation**

Immediately after `complete_json`:

```python
if not isinstance(extracted, dict):
    raise ActivityExtractionError("model response must be a JSON object")
```

Keep the existing allowlist and `with_updates` exception translation unchanged.

- [ ] **Step 4: Verify GREEN**

Run the extraction tests, then the complete suite. Expected: all pass.

- [ ] **Step 5: Commit**

Commit only `weather_agent/extraction.py` and `tests/test_extraction.py` with message `fix: reject unsafe extraction responses`.

### Task 3: Make location-choice state deterministic and recoverable

**Files:**
- Modify: `tests/test_agent.py`
- Modify: `weather_agent/agent.py`

- [ ] **Step 1: Add failing candidate-state tests**

Add these concrete tests using the existing `candidate`, `FakeExtractor`, `FakeGeocoder`, `FakeWeather`, `forecast_payload`, `START`, and `ActivityPlan` helpers:

```python
def test_chinese_ordinal_selects_candidate(self):
    plan = ActivityPlan("cycling", "公园", START, 3)
    first = candidate("天津森林公园", 39.1, 117.2, "天津")
    second = candidate("北京森林公园", 40.0, 116.4, "北京")
    weather = FakeWeather(forecast_payload())
    agent = WeatherAgent(FakeExtractor([plan]), FakeGeocoder((first, second)), weather)
    agent.handle_message("完整计划", now=START)
    result = agent.handle_message("第二个", now=START)
    self.assertEqual(result.kind, "recommendation")
    self.assertEqual(weather.calls, [(116.4, 40.0)])

def test_unique_candidate_text_selects_candidate(self):
    plan = ActivityPlan("cycling", "森林公园", START, 3)
    first = candidate("天津森林公园", 39.1, 117.2, "天津")
    second = candidate("北京森林公园", 40.0, 116.4, "北京")
    weather = FakeWeather(forecast_payload())
    agent = WeatherAgent(FakeExtractor([plan]), FakeGeocoder((first, second)), weather)
    agent.handle_message("完整计划", now=START)
    agent.handle_message("选北京那个", now=START)
    self.assertEqual(weather.calls, [(116.4, 40.0)])

def test_rejects_zero_and_out_of_range_candidate_numbers(self):
    plan = ActivityPlan("cycling", "森林公园", START, 3)
    places = (candidate("森林公园", 40.0, 116.4, "北京"),)
    agent = WeatherAgent(FakeExtractor([plan]), FakeGeocoder(places), FakeWeather())
    agent.pending_locations = places
    for text in ("0", "2"):
        result = agent.handle_message(text, now=START)
        self.assertEqual(result.kind, "location_choice")
        self.assertEqual(agent.pending_locations, places)

def test_none_of_these_clears_location_and_candidates(self):
    plan = ActivityPlan("cycling", "森林公园", START, 3)
    places = (candidate("森林公园", 40.0, 116.4, "北京"),)
    agent = WeatherAgent(FakeExtractor([]), FakeGeocoder(places), FakeWeather())
    agent.plan = plan
    agent.pending_locations = places
    result = agent.handle_message("都不是", now=START)
    self.assertEqual(result.kind, "question")
    self.assertIsNone(result.plan.location)
    self.assertEqual(agent.pending_locations, ())

def test_new_location_during_choice_reenters_extraction(self):
    old = ActivityPlan("cycling", "森林公园", START, 3)
    corrected = ActivityPlan("cycling", "北京奥森", START, 3)
    place = candidate("北京奥森", 40.0, 116.4, "北京")
    agent = WeatherAgent(FakeExtractor([corrected]), FakeGeocoder((place,)), FakeWeather(forecast_payload()))
    agent.plan = old
    agent.pending_locations = (candidate("天津森林公园", 39.1, 117.2, "天津"),)
    result = agent.handle_message("改成北京奥森", now=START)
    self.assertEqual(result.kind, "recommendation")
    self.assertEqual(result.plan.location, "北京奥森")
```

Assertions must check selected weather coordinates, whether `pending_locations` remains or clears, and whether the extractor is called. Do not assert private helper implementation.

- [ ] **Step 2: Verify RED**

Run each new test individually. Expected: current code only accepts a pure in-range number, so the natural-language and cancellation cases fail for the intended reason.

- [ ] **Step 3: Implement minimal candidate parsing**

Add module constants and private helpers with this limited contract:

```python
ORDINAL_CHOICES = {"第一个": 0, "第二个": 1, "第三个": 2, "第四个": 3, "第五个": 4}
NONE_OF_THESE = {"都不是", "没有合适的", "重新选地点"}

def _candidate_index(message, candidates):
    text = message.strip()
    if text.isdigit():
        index = int(text) - 1
        return index if 0 <= index < len(candidates) else None
    if text in ORDINAL_CHOICES:
        index = ORDINAL_CHOICES[text]
        return index if index < len(candidates) else None
    matches = [
        index for index, candidate in enumerate(candidates)
        if candidate.display_name in text or any(
            token and token in candidate.display_name
            for token in text.replace("选", "").replace("那个", "").split()
        )
    ]
    return matches[0] if len(set(matches)) == 1 else None
```

During pending-location handling:

- exact cancellation phrases clear `pending_locations` and set `location=None` through `with_updates`;
- valid selections evaluate immediately without a model call;
- numeric/ordinal-looking invalid selections redisplay choices;
- other text clears old candidates and continues through normal extraction as a possible corrected location.

- [ ] **Step 4: Verify GREEN**

Run `tests.test_agent`, then the complete suite. Expected: all candidate behaviors and previous numeric behavior pass.

- [ ] **Step 5: Commit**

Commit the two task files with message `feat: recover from ambiguous location choices`.

### Task 4: Guard conversation state and improve safe recovery

**Files:**
- Modify: `tests/test_agent.py`
- Modify: `tests/test_ui.py`
- Modify: `weather_agent/agent.py`
- Modify: `weather_agent/ui.py`

- [ ] **Step 1: Add failing state and recovery tests**

Add behavior tests with concrete assertions:

```python
def test_blank_or_punctuation_message_does_not_call_extractor(self):
    agent = WeatherAgent(FakeExtractor([]), FakeGeocoder(()), FakeWeather())
    result = agent.handle_message("？！", now=START)
    self.assertEqual(result.kind, "question")
    self.assertIn("有效", result.message)

def test_reset_command_clears_plan_and_pending_candidates(self):
    agent = WeatherAgent(FakeExtractor([]), FakeGeocoder(()), FakeWeather())
    agent.plan = ActivityPlan("cycling", "北京", START, 3)
    agent.pending_locations = (candidate("北京", 40.0, 116.4, "北京"),)
    result = agent.handle_message("重新开始", now=START)
    self.assertEqual(result.kind, "reset")
    self.assertEqual(result.plan, ActivityPlan())
    self.assertEqual(agent.pending_locations, ())

def test_geocoding_failure_preserves_plan_and_suggests_retry(self):
    plan = ActivityPlan("cycling", "北京", START, 3)
    geocoder = FakeGeocoder(())
    geocoder.search = Mock(side_effect=GeocodingError("timeout"))
    agent = WeatherAgent(FakeExtractor([plan]), geocoder, FakeWeather())
    result = agent.handle_message("完整计划", now=START)
    self.assertEqual(result.plan, plan)
    self.assertIn("重试", result.message)

def test_out_of_range_forecast_suggests_time_change(self):
    plan = ActivityPlan("cycling", "北京", START, 3)
    place = candidate("北京", 40.0, 116.4, "北京")
    payload = forecast_payload()
    payload["data"][0]["time"] = "2026-08-07T08:00:00+08:00"
    agent = WeatherAgent(FakeExtractor([plan]), FakeGeocoder((place,)), FakeWeather(payload))
    result = agent.handle_message("完整计划", now=START)
    self.assertIn("调整活动时间", result.message)

def test_extraction_error_reply_preserves_plan_summary(self):
    from weather_agent.extraction import ActivityExtractionError
    from weather_agent.ui import respond
    agent = Mock()
    agent.plan = ActivityPlan("cycling", "北京", NOW, 3)
    agent.handle_message.side_effect = ActivityExtractionError("bad output")
    _, history, _, summary = respond("改时间", [], agent, now=NOW)
    self.assertIn("换一种说法", history[-1]["content"])
    self.assertIn("北京", summary)
```

Use `self.assertIn` for actionable concepts such as “补充有效信息”, “已重新开始”, “重试”, and “调整活动时间”; do not freeze whole messages.

- [ ] **Step 2: Verify RED**

Run the five tests individually and confirm they fail due to missing behavior.

- [ ] **Step 3: Implement minimal guards**

At the start of `handle_message`, normalize once:

```python
text = message.strip()
if not text or not any(character.isalnum() for character in text):
    return AgentResult("question", "请补充有效的活动信息。", self.plan)
if text in {"重新开始", "重置", "清空计划"}:
    self.plan = ActivityPlan()
    self.pending_locations = ()
    return AgentResult("reset", "已重新开始，请告诉我计划的户外活动。", self.plan)
```

Keep plans unchanged on geocoding/weather/extraction errors. Update error text with one concrete next action. In `ui.respond`, catch `ActivityExtractionError` separately from missing service configuration so invalid model output is not described as a configuration problem.

- [ ] **Step 4: Verify GREEN**

Run agent and UI tests, then the complete suite. Expected: all pass.

- [ ] **Step 5: Commit**

Commit task files with message `fix: preserve agent state on recoverable errors`.

### Task 5: Add decision evidence and complete the 20-case matrix

**Files:**
- Modify: `tests/test_agent.py`
- Modify: `tests/test_extraction.py`
- Modify: `weather_agent/agent.py`
- Modify: `weather_agent/ui.py`
- Modify: `README.md`

- [ ] **Step 1: Inventory the adversarial matrix**

Add a comment block or named test classes mapping exactly 20 behavioral cases to tests. Existing tests may count only when they assert the specified adversarial behavior.

- [ ] **Step 2: Add failing decision-evidence assertions**

For both safe and risky forecasts, assert the recommendation includes the activity window, resolved location, forecast initialization time, and either “未识别到明显天气风险” or the triggered public rule values.

- [ ] **Step 3: Verify RED**

Run the new assertions. Expected: any missing evidence label fails before production changes.

- [ ] **Step 4: Add the minimum user-visible evidence labels**

Keep `_format_recommendation` rule-based. Format a compact section such as:

```text
决策依据：地点…；活动时段…；预报起报时间…；规则结果…
```

Do not expose chain-of-thought or add another model call.

- [ ] **Step 5: Update UI help and README**

Document supported candidate replies, reset commands, the 20-case verification command, passed count, deterministic/model boundary, and remaining external-service/model limitations.

- [ ] **Step 6: Run final verification**

Run:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q weather_agent tests app.py
git diff --check
```

Expected: zero test failures/errors, compile exit 0, and no whitespace errors.

- [ ] **Step 7: Commit**

Commit task files with message `test: verify agent against adversarial cases`.

### Task 6: First-principles completion review

**Files:**
- Review: `docs/superpowers/specs/2026-08-06-agent-robustness-design.md`
- Review: `README.md`

- [ ] **Step 1: Check scope line by line**

Confirm every changed production line supports one of the 20 cases. Remove speculative abstractions or unrelated formatting.

- [ ] **Step 2: Verify Agent properties**

Confirm the system still performs stateful goal completion, conditional tool use, safe failure, and evidence-based recommendation rather than merely returning an LLM response.

- [ ] **Step 3: Run fresh complete verification**

Repeat the full test, compile, and diff-check commands and record exact results in README.

- [ ] **Step 4: Finish the branch**

Use the finishing-a-development-branch workflow to present verified integration options. Do not merge or push without the corresponding user authorization.
