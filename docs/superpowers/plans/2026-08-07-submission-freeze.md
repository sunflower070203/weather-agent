# Submission Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a traceable, documented, tested, deployable competition submission candidate without adding new Agent capabilities.

**Architecture:** Keep `WeatherAgent` and all tool behavior unchanged. Add a small UI-only version marker, then build a documentation and release-evidence layer around the existing tested Agent. Treat ModelScope version parity as a deployment gate before interpreting online behavior as a code defect.

**Tech Stack:** Python 3.12, Gradio 6.17.3, unittest, Git, ModelScope Studio

---

## File map

- Modify `weather_agent/ui.py`: resolve and display a safe submission version string.
- Modify `tests/test_ui.py`: verify default, configured, and rendered version values.
- Modify `README.md`: replace stale progress, counts, dates, and next actions with verified submission status.
- Create `docs/submission-checklist.md`: operational submission checklist.
- Create `docs/demo-script.md`: fixed three-minute demonstration.
- Create `docs/architecture.md`: explain why this is an Agent and how data flows.
- Create `docs/development-retrospective.md`: reusable development-process retrospective.
- Create `dist/weather-agent-submission-2026-08.zip`: generated release artifact; never commit it.

### Task 1: Add a visible release version

**Files:**
- Modify: `tests/test_ui.py`
- Modify: `weather_agent/ui.py`

- [ ] **Step 1: Write failing version resolution tests**

Add to `UIAdapterTests`:

```python
def test_app_version_uses_safe_default(self):
    from weather_agent.ui import get_app_version

    self.assertEqual(get_app_version({}), "submission-2026-08-07")

def test_app_version_uses_deployment_value(self):
    from weather_agent.ui import get_app_version

    self.assertEqual(
        get_app_version({"WEATHER_AGENT_VERSION": "rc-8c10dff"}),
        "rc-8c10dff",
    )

def test_build_app_renders_release_version(self):
    from weather_agent.ui import build_app

    demo = build_app(version="rc-test")
    self.assertIn("rc-test", str(demo.config))
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```powershell
& 'C:\Users\Sunny\Documents\weather-agent\.worktrees\codex-agent-robustness\.venv\Scripts\python.exe' -m unittest tests.test_ui.UIAdapterTests.test_app_version_uses_safe_default tests.test_ui.UIAdapterTests.test_app_version_uses_deployment_value tests.test_ui.UIAdapterTests.test_build_app_renders_release_version -v
```

Expected: FAIL because `get_app_version` and the `version` argument do not exist.

- [ ] **Step 3: Implement the minimal UI-only version marker**

In `weather_agent/ui.py`, add `import os`, then:

```python
DEFAULT_APP_VERSION = "submission-2026-08-07"


def get_app_version(environ=None):
    source = os.environ if environ is None else environ
    value = source.get("WEATHER_AGENT_VERSION", "").strip()
    return value or DEFAULT_APP_VERSION
```

Change the application factory signature and add a footer line:

```python
def build_app(*, version=None):
    version = version or get_app_version()
    with gr.Blocks(title="户外天气决策 Agent") as demo:
        # existing UI remains unchanged
        gr.Markdown(f"运行版本：`{version}`", elem_classes="data-note")
```

Do not pass the version into `WeatherAgent`, tools, prompts, or API calls.

- [ ] **Step 4: Run focused and full tests**

Run the three focused tests from Step 2, then:

```powershell
& 'C:\Users\Sunny\Documents\weather-agent\.worktrees\codex-agent-robustness\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

Expected: 60 tests, 0 failures.

- [ ] **Step 5: Commit the version marker**

```powershell
git add tests/test_ui.py weather_agent/ui.py
git commit -m "feat: expose submission version"
```

### Task 2: Build the reviewer-facing documentation package

**Files:**
- Modify: `README.md`
- Create: `docs/submission-checklist.md`
- Create: `docs/demo-script.md`
- Create: `docs/architecture.md`
- Create: `docs/development-retrospective.md`

- [ ] **Step 1: Correct README facts**

Make these exact factual changes without rewriting unrelated historical records:

- State that the activity creation period ends on August 9 and submission runs August 10-16.
- Mark the single-Agent decision loop, Gradio UI, GitHub repository, and ModelScope deployment as implemented.
- State the fresh automated-test count from Task 1 rather than retaining 35, 50, or 57 as the current total.
- Mark submission materials as in progress until every file in this task exists.
- Add the public Studio link and the release version expected on that page.
- List known limitations: city-level approximation, three supported activity types, forecast-window bounds, and no official-warning replacement.
- State explicitly that Skill, RAG, long-term Memory, and multi-Agent are not current capabilities.

- [ ] **Step 2: Create the submission checklist**

`docs/submission-checklist.md` must contain checkboxes for:

```markdown
- [ ] Public ModelScope Studio opens in a logged-out browser
- [ ] Displayed release version matches the release commit
- [ ] Three required secrets exist only in ModelScope secret management
- [ ] Main, modification, past-time, 1000-hour, and reset scenarios pass
- [ ] README, architecture, demo, and retrospective links work
- [ ] GitHub commit, tag, ZIP checksum, Studio URL, and submission screenshot are saved
- [ ] No token-bearing URL appears in docs, logs, screenshots, or ZIP
```

Include the exact local verification commands and the three variable names, but no secret values.

- [ ] **Step 3: Create the fixed three-minute demo script**

Use this sequence in `docs/demo-script.md`:

1. 0:00-0:30 — problem and Agent boundary.
2. 0:30-1:30 — future Tianjin hiking plan, follow-up completion, real weather evidence, two alternatives.
3. 1:30-2:05 — modify the activity time and show state retention plus reevaluation.
4. 2:05-2:35 — submit a 1000-hour plan and show deterministic refusal before tools.
5. 2:35-3:00 — reset, show empty state, architecture and public repository.

Every spoken claim must map to visible UI evidence or a linked test. Do not claim official warning accuracy or autonomous route planning.

- [ ] **Step 4: Create the architecture explanation**

`docs/architecture.md` must include:

```text
User message
  -> Qwen structured slot extraction
  -> ActivityPlan session state
  -> deterministic validation and candidate state
  -> Open-Meteo geocoding
  -> Tianji hourly weather API
  -> deterministic risk rules
  -> evidence + two action alternatives
  -> user modification loops back into the same state
```

Explain the four Agent properties: goal-directed state, conditional tool use, deterministic decision control, and feedback-driven replanning. Contrast them with a stateless chatbot and a one-shot tool wrapper.

- [ ] **Step 5: Create the development retrospective**

`docs/development-retrospective.md` must cover: first-principles scope, API verification, state modeling, structured model output, tool boundaries, deterministic rules, adversarial tests, deployment drift, and scope freeze. End with a reusable nine-step Agent development checklist.

- [ ] **Step 6: Check documentation consistency**

Run:

```powershell
rg -n "35项|50项|57项|未开始|尚未建立|2026-08-10 前" README.md docs/submission-checklist.md docs/demo-script.md docs/architecture.md docs/development-retrospective.md
rg -n "studio_token|MODELSCOPE_ACCESS_TOKEN=|TJWEATHER_API_KEY=|TJWEATHER_SUBSCRIPTION_ID=" README.md docs
git diff --check
```

Expected: no stale current-status claims, no secret values or token-bearing URLs, and no whitespace errors. Historical records may retain their original test counts when explicitly dated.

- [ ] **Step 7: Commit the documentation package**

```powershell
git add README.md docs/submission-checklist.md docs/demo-script.md docs/architecture.md docs/development-retrospective.md
git commit -m "docs: prepare competition submission"
```

### Task 3: Verify and publish the candidate branch

**Files:**
- Verify all tracked source and documentation files

- [ ] **Step 1: Run the full local gate**

```powershell
& 'C:\Users\Sunny\Documents\weather-agent\.worktrees\codex-agent-robustness\.venv\Scripts\python.exe' -m unittest discover -s tests -v
& 'C:\Users\Sunny\Documents\weather-agent\.worktrees\codex-agent-robustness\.venv\Scripts\python.exe' -m compileall -q weather_agent tests app.py
git diff --check origin/main...HEAD
git status --short
```

Expected: 60 tests pass; compile and diff checks exit 0; working tree is clean.

- [ ] **Step 2: Audit the candidate diff**

```powershell
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
git grep -n -E "studio_token|sk-[A-Za-z0-9]|MODELSCOPE_ACCESS_TOKEN=|TJWEATHER_API_KEY=|TJWEATHER_SUBSCRIPTION_ID=" HEAD -- . ':!docs/submission-checklist.md'
```

Expected changed scope: one UI file, one UI test file, README, and the approved submission documents. Secret scan returns no actual credential.

- [ ] **Step 3: Push and open a reviewable PR**

```powershell
git push -u origin codex/submission-freeze
```

Open a PR titled `Prepare competition submission candidate`. The body must list version-marker behavior, documentation deliverables, test count, and the required ModelScope post-merge gate.

### Task 4: Deploy and run the online release gate

**Files:**
- ModelScope Studio deployment branch
- `docs/submission-checklist.md` after evidence is known

- [ ] **Step 1: Merge the reviewed GitHub PR**

Confirm CI/diff status first. Merge normally; do not force-push or rewrite `main`.

- [ ] **Step 2: Synchronize the merged snapshot to ModelScope**

Preserve ModelScope platform history and `.gitattributes`. Set `WEATHER_AGENT_VERSION` in ModelScope secret/environment management to `rc-<GitHub short merge commit>`, push the ordinary deployment commit, and trigger redeploy.

- [ ] **Step 3: Prove version parity before behavioral testing**

Open the public Studio in a fresh page. The displayed version must exactly equal the configured `rc-<commit>` value. If it differs, stop: redeploy or inspect platform logs without changing Agent logic.

- [ ] **Step 4: Run five isolated online scenarios**

Use a fresh session for each independent scenario:

```text
1. 明天上午9点在天津徒步4小时
2. 周末上午9点在杭州徒步4小时 -> 改成露营
3. 昨天上午8点在天津骑行3小时
4. 明天上午8点在天津骑行1000小时
5. Create any plan -> click 重新开始 -> 我想去徒步
```

Expected:

- Scenario 1 reaches a weather recommendation with evidence and two alternatives.
- Scenario 2 retains location/time/duration and changes activity to camping.
- Scenario 3 asks for a future time before a weather recommendation.
- Scenario 4 asks for 168 hours or less before a weather recommendation.
- Scenario 5 contains no old location, time, or duration.

- [ ] **Step 5: Record release evidence**

Update `docs/submission-checklist.md` with the GitHub merge commit, ModelScope deployment commit, displayed release version, test count, online results, date, and remaining known limitations. Commit and propagate this evidence only if doing so does not change the already verified runtime files; otherwise retain it as the final release-note commit and do not redeploy unnecessarily.

### Task 5: Create the recoverable source package

**Files:**
- Create locally: `dist/weather-agent-submission-2026-08.zip`
- Create locally: `dist/weather-agent-submission-2026-08.sha256`

- [ ] **Step 1: Create a clean archive from the release commit**

```powershell
New-Item -ItemType Directory -Force dist | Out-Null
git archive --format=zip --output="dist/weather-agent-submission-2026-08.zip" HEAD
Get-FileHash "dist/weather-agent-submission-2026-08.zip" -Algorithm SHA256 | ForEach-Object Hash | Set-Content "dist/weather-agent-submission-2026-08.sha256"
```

Do not build the ZIP by recursively copying the workspace.

- [ ] **Step 2: Inspect archive contents**

```powershell
tar -tf "dist/weather-agent-submission-2026-08.zip"
```

Expected: source, tests, requirements, license, README, and docs only; no `.git`, `.env`, `.venv`, `.worktrees`, cache, or `_knowledge_base`.

- [ ] **Step 3: Tag the verified candidate**

```powershell
git tag -a "submission-2026-08" -m "Weather Agent competition submission candidate"
git push origin "submission-2026-08"
```

Create and push the tag only after the displayed online version and all five scenarios pass.
