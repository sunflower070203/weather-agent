# Gradio Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a session-isolated Gradio chat interface that exposes the existing outdoor weather decision Agent and can run in ModelScope Studio.

**Architecture:** Keep `WeatherAgent` as the domain core and add a thin, testable UI adapter in `weather_agent/ui.py`. Store one mutable Agent per browser session in `gr.State`; `app.py` only builds and launches the interface. Pin the only new dependency for reproducible local and ModelScope installs.

**Tech Stack:** Python 3.10+, Gradio 6.22.0, standard-library `unittest`, existing ModelScope/Open-Meteo/TJWeather clients.

---

## File map

- Create `requirements.txt`: deployment dependency pin.
- Create `tests/test_ui.py`: UI adapter behavior and session-isolation tests.
- Create `weather_agent/ui.py`: dependency factory, chat adapter, plan formatting, reset and Gradio component tree.
- Create `app.py`: ModelScope-compatible application entry point.
- Modify `README.md`: local run instructions, required secrets and current verification evidence.

### Task 1: Pin and install Gradio

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Add the reproducible dependency**

```text
gradio==6.22.0
```

- [ ] **Step 2: Install it with the active Python runtime**

Run: `py -m pip install -r requirements.txt`

Expected: exit code 0 and `Successfully installed gradio-6.22.0` or an already-satisfied message.

- [ ] **Step 3: Verify the imported version**

Run: `py -c "import gradio; print(gradio.__version__)"`

Expected: `6.22.0`.

- [ ] **Step 4: Commit**

```powershell
git add requirements.txt
git commit -m "build: pin Gradio dependency"
```

### Task 2: Build the session-safe UI adapter with TDD

**Files:**
- Create: `tests/test_ui.py`
- Create: `weather_agent/ui.py`

- [ ] **Step 1: Write failing adapter tests**

```python
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from weather_agent.activity import ActivityPlan


NOW = datetime(2026, 8, 4, 14, 0, tzinfo=timezone(timedelta(hours=8)))


class UIAdapterTests(unittest.TestCase):
    def test_blank_message_does_not_call_agent(self):
        from weather_agent.ui import respond
        agent = Mock()
        cleared, history, returned_agent, summary = respond("  ", [], agent, now=NOW)
        self.assertEqual(cleared, "")
        self.assertIn("请输入", history[-1]["content"])
        self.assertIs(returned_agent, agent)
        agent.handle_message.assert_not_called()

    def test_response_appends_both_messages_and_formats_plan(self):
        from weather_agent.agent import AgentResult
        from weather_agent.ui import respond
        plan = ActivityPlan("cycling", "北京", NOW, 3)
        agent = Mock()
        agent.handle_message.return_value = AgentResult("question", "请确认地点", plan)
        _, history, _, summary = respond("去骑行", [], agent, now=NOW)
        self.assertEqual([item["role"] for item in history], ["user", "assistant"])
        self.assertIn("骑行", summary)
        self.assertIn("北京", summary)

    @patch("weather_agent.ui.create_agent")
    def test_new_sessions_receive_distinct_agents(self, create_agent):
        from weather_agent.ui import new_session
        create_agent.side_effect = [object(), object()]
        self.assertIsNot(new_session(), new_session())

    def test_reset_clears_history_and_agent(self):
        from weather_agent.ui import reset_session
        self.assertEqual(reset_session(), ([], None, "尚未填写活动计划。"))
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `py -m unittest tests.test_ui -v`

Expected: ERROR with `ModuleNotFoundError: No module named 'weather_agent.ui'`.

- [ ] **Step 3: Implement the minimal adapter**

Create `weather_agent/ui.py` with:

```python
from datetime import datetime

from weather_agent.agent import WeatherAgent
from weather_agent.extraction import ActivityExtractionError, ActivityExtractor
from weather_agent.geocoding import GeocodingClient
from weather_agent.modelscope import ModelScopeClient, ModelScopeError
from weather_agent.tjweather import TJWeatherClient, TJWeatherConfig, TJWeatherError


EMPTY_PLAN = "尚未填写活动计划。"
ACTIVITY_NAMES = {"cycling": "骑行", "hiking": "徒步", "camping": "露营"}


def create_agent():
    return WeatherAgent(
        ActivityExtractor(ModelScopeClient.from_environment()),
        GeocodingClient(),
        TJWeatherClient(TJWeatherConfig.from_environment()),
    )


def new_session():
    return create_agent()


def format_plan(plan):
    if not any((plan.activity_type, plan.location, plan.start_time, plan.duration_hours)):
        return EMPTY_PLAN
    start = plan.start_time.isoformat() if plan.start_time else "待补充"
    duration = f"{plan.duration_hours:g} 小时" if plan.duration_hours else "待补充"
    return "\n".join((
        f"**活动**：{ACTIVITY_NAMES.get(plan.activity_type, '待补充')}",
        f"**地点**：{plan.location or '待补充'}",
        f"**开始**：{start}",
        f"**时长**：{duration}",
    ))


def respond(message, history, agent, *, now=None):
    history = list(history or [])
    if not message or not message.strip():
        history.append({"role": "assistant", "content": "请输入你的户外活动计划。"})
        return "", history, agent, format_plan(agent.plan) if agent else EMPTY_PLAN
    try:
        agent = agent or new_session()
        result = agent.handle_message(message.strip(), now=now or datetime.now().astimezone())
        reply = result.message
        summary = format_plan(result.plan)
    except (ActivityExtractionError, ModelScopeError, TJWeatherError) as exc:
        reply = f"服务配置暂不可用：{exc}"
        summary = format_plan(agent.plan) if agent else EMPTY_PLAN
    history.extend((
        {"role": "user", "content": message.strip()},
        {"role": "assistant", "content": reply},
    ))
    return "", history, agent, summary


def reset_session():
    return [], None, EMPTY_PLAN
```

- [ ] **Step 4: Run focused and full tests**

Run: `py -m unittest tests.test_ui -v`

Expected: 4 tests pass.

Run: `py -m unittest discover -s tests -v`

Expected: all existing 30 tests plus the 4 UI tests pass.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_ui.py weather_agent/ui.py
git commit -m "feat: add session-safe chat adapter"
```

### Task 3: Build the Gradio application

**Files:**
- Modify: `weather_agent/ui.py`
- Create: `app.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Add a failing smoke test for the component tree**

```python
def test_build_app_returns_gradio_blocks(self):
    import gradio as gr
    from weather_agent.ui import build_app
    self.assertIsInstance(build_app(), gr.Blocks)
```

- [ ] **Step 2: Run the smoke test and verify RED**

Run: `py -m unittest tests.test_ui.UIAdapterTests.test_build_app_returns_gradio_blocks -v`

Expected: ERROR with `cannot import name 'build_app'`.

- [ ] **Step 3: Add the Gradio component tree**

Add `build_app()` to `weather_agent/ui.py`. It must use `gr.State(None)`, a `gr.Chatbot(type="messages")`, `gr.Markdown` for the plan summary, a message `gr.Textbox`, send and reset buttons, three `gr.Examples`, and bind both textbox submission and button click to `respond`. Bind reset to `reset_session`. Use CSS variables for a deep-green, fog-white and orange observation-log theme, with a single-column media query below 760 px.

The function must not call `create_agent()` while building the page; Agent creation occurs lazily on the first message so missing secrets do not prevent the page from loading.

- [ ] **Step 4: Create the deployment entry point**

```python
from weather_agent.ui import build_app


demo = build_app()


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=4).launch(
        server_name="0.0.0.0",
        server_port=7860,
    )
```

- [ ] **Step 5: Run smoke and regression tests**

Run: `py -m unittest tests.test_ui -v`

Expected: 5 tests pass.

Run: `py -m unittest discover -s tests -v`

Expected: 35 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add app.py weather_agent/ui.py tests/test_ui.py
git commit -m "feat: add Gradio competition interface"
```

### Task 4: Verify locally and document deployment

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document exact local commands and ModelScope secrets**

Add commands for `py -m pip install -r requirements.txt`, `py app.py`, and `py -m unittest discover -s tests -v`. List only the names `MODELSCOPE_ACCESS_TOKEN`, `TJWEATHER_API_KEY`, and `TJWEATHER_SUBSCRIPTION_ID`, never their values.

- [ ] **Step 2: Start the server**

Run: `py app.py`

Expected: Gradio listens on `http://127.0.0.1:7860` or `http://0.0.0.0:7860` without traceback.

- [ ] **Step 3: Perform browser acceptance**

Open `http://127.0.0.1:7860` and verify:

- title, warning and examples render;
- `2026年8月6日上午8点在北京奥林匹克森林公园骑行3小时` enters the Agent flow;
- selecting a numbered location produces a weather-grounded recommendation;
- reset clears both chat and plan summary;
- a second browser session starts empty.

- [ ] **Step 4: Run final verification**

Run: `py -m unittest discover -s tests -v`

Expected: 35 tests pass with zero failures.

Run: `py -m compileall -q weather_agent tests app.py`

Expected: exit code 0.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 5: Commit**

```powershell
git add README.md
git commit -m "docs: add local and ModelScope runbook"
```

After local acceptance, upload or synchronize the committed repository files to `sunh0203/outdoor-weather-agent`, configure the three secret names in ModelScope, deploy, and repeat the browser acceptance flow against the public URL.
