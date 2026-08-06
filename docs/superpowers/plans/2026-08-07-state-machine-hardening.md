# State Machine Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the four state-machine and validation defects reproduced by the 2026-08-06 live black-box test without adding new architecture.

**Architecture:** Keep `WeatherAgent` as the orchestration boundary. Add deterministic interruption and plan validation before tool calls, and conservatively normalize municipality geocoding results inside `GeocodingClient`. Preserve all existing public return types and dependency injection.

**Tech Stack:** Python 3.12, `unittest`, dataclasses, Gradio 6.17.3, existing Open-Meteo and Tianji clients.

---

## File map

- Modify `weather_agent/agent.py`: candidate-stage interruption and pre-tool plan validation.
- Modify `weather_agent/geocoding.py`: municipality exact-match filtering and deterministic candidate ranking.
- Modify `tests/test_agent.py`: state and boundary regressions.
- Modify `tests/test_geocoding.py`: municipality regression cases.
- Modify `tests/test_ui.py`: full reset lifecycle regression.
- Modify `README.md`: exact verification result and remaining limits.

### Task 1: Prove reset lifecycle behavior

**Files:**
- Modify: `tests/test_ui.py`
- Modify only if the test fails: `weather_agent/ui.py`

- [ ] Add `test_reset_then_response_creates_agent_without_old_plan` using a populated mock Agent, `reset_session()`, then `respond()` with the returned `None` state while patching `new_session`. Assert empty history/summary after reset and that the next response uses a distinct Agent with an empty plan.
- [ ] Run `python -m unittest tests.test_ui.UIAdapterTests.test_reset_then_response_creates_agent_without_old_plan -v`.
- [ ] If it passes immediately, record that the current adapter already satisfies the contract and do not edit `ui.py`; if it fails for state retention, make only the output/state correction required by the assertion.
- [ ] Run `python -m unittest tests.test_ui -v` and commit the regression evidence.

### Task 2: Allow explicit modifications while location choice is pending

**Files:**
- Modify: `tests/test_agent.py`
- Modify: `weather_agent/agent.py`

- [ ] Add a failing test where `pending_locations` is populated and the user says `改成露营`; the extractor returns a camping plan. Assert the extractor receives the message, candidates clear, and the updated activity reaches normal evaluation.
- [ ] Add a control test where unrelated text during candidate selection continues to redisplay the candidates without calling the extractor.
- [ ] Run both tests and confirm only the explicit-modification test fails because current `LOCATION_CHANGE_PREFIXES` cannot distinguish activity/time/duration changes.
- [ ] Replace the location-only prefix constant with a narrowly named interruption predicate supporting `改成`, `换成`, `改为`, `时间改`, `地点改`, and `时长改`. Keep reset, cancellation, and candidate selection ahead of it.
- [ ] Run `python -m unittest tests.test_agent -v` and commit with `fix: allow plan changes during location choice`.

### Task 3: Reject invalid time and duration before geocoding

**Files:**
- Modify: `tests/test_agent.py`
- Modify: `weather_agent/agent.py`

- [ ] Add `test_past_start_time_is_rejected_before_geocoding`: extractor returns a complete plan whose start is before `now`; assert a question result mentioning future time and zero geocoder/weather calls.
- [ ] Add `test_duration_over_seven_days_is_rejected_before_geocoding`: extractor returns duration `1000`; assert a question result requesting a shorter duration and zero tool calls.
- [ ] Run each test individually and confirm both fail because the current code calls the geocoder.
- [ ] Add `_validate_plan(now)` returning an optional `AgentResult`; call it after `is_ready()` and before `geocoder.search()`. Use `start_time < now` and `duration_hours > 168` only.
- [ ] Run `python -m unittest tests.test_agent -v` and commit with `fix: validate plans before tool calls`.

### Task 4: Reduce municipality false ambiguity

**Files:**
- Modify: `tests/test_geocoding.py`
- Modify: `weather_agent/geocoding.py`

- [ ] Add a failing Beijing test with results for Beijing municipality, Chongqing, and Sichuan. Assert `search("北京")` returns only the candidate whose normalized name and `admin1` identify Beijing municipality.
- [ ] Add a non-municipality test with two Hangzhou results. Assert both remain, with the exact-name Zhejiang candidate ranked first.
- [ ] Run the two tests and verify the Beijing test fails while the conservative Hangzhou behavior remains unchanged.
- [ ] Add small private normalization/ranking helpers. Municipality filtering applies only to `北京/北京市`, `天津/天津市`, `上海/上海市`, and `重庆/重庆市`; all other queries are sorted but not discarded.
- [ ] Run `python -m unittest tests.test_geocoding -v` and commit with `fix: prioritize exact municipality locations`.

### Task 5: Documentation and complete verification

**Files:**
- Modify: `README.md`

- [ ] Append a 2026-08-07 development record with the defects fixed, tests added, exact commands, and the remaining need for ModelScope live redeployment verification.
- [ ] Run:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q weather_agent tests app.py
git diff --check
```

- [ ] Record the exact test count only after the command succeeds.
- [ ] Review every production diff line against the four approved defects; remove unrelated changes.
- [ ] Commit with `docs: record state machine hardening verification`.

### Task 6: Publish for review

- [ ] Push `codex/state-machine-hardening` to GitHub.
- [ ] Open a ready-for-review PR against `main` summarizing red-green evidence and remaining live-deployment verification.
- [ ] Do not merge or deploy until the branch verification and PR diff are confirmed.
