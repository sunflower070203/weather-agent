import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from weather_agent.activity import ActivityPlan


NOW = datetime(2026, 8, 4, 14, 0, tzinfo=timezone(timedelta(hours=8)))


class UIAdapterTests(unittest.TestCase):
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

    def test_build_app_returns_gradio_blocks(self):
        import gradio as gr

        from weather_agent.ui import build_app

        self.assertIsInstance(build_app(), gr.Blocks)

    def test_blank_message_does_not_call_agent(self):
        from weather_agent.ui import respond

        agent = Mock()
        agent.plan = ActivityPlan()

        cleared, history, returned_agent, summary = respond(
            "  ", [], agent, now=NOW
        )

        self.assertEqual(cleared, "")
        self.assertIn("请输入", history[-1]["content"])
        self.assertIs(returned_agent, agent)
        self.assertEqual(summary, "尚未填写活动计划。")
        agent.handle_message.assert_not_called()

    def test_response_appends_both_messages_and_formats_plan(self):
        from weather_agent.agent import AgentResult
        from weather_agent.ui import respond

        plan = ActivityPlan("cycling", "北京", NOW, 3)
        agent = Mock()
        agent.handle_message.return_value = AgentResult(
            "question", "请确认地点", plan
        )

        _, history, returned_agent, summary = respond(
            "去骑行", [], agent, now=NOW
        )

        self.assertEqual(
            [item["role"] for item in history], ["user", "assistant"]
        )
        self.assertEqual(history[-1]["content"], "请确认地点")
        self.assertIs(returned_agent, agent)
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

    @patch("weather_agent.ui.new_session")
    def test_reset_then_response_creates_agent_without_old_plan(self, new_session):
        from weather_agent.agent import AgentResult
        from weather_agent.ui import respond, reset_session

        fresh_agent = Mock()
        fresh_agent.plan = ActivityPlan()
        fresh_agent.handle_message.return_value = AgentResult(
            "question", "活动地点在哪里？", ActivityPlan(activity_type="cycling")
        )
        new_session.return_value = fresh_agent

        history, agent, summary = reset_session()
        _, next_history, returned_agent, next_summary = respond(
            "我想骑行", history, agent, now=NOW
        )

        self.assertEqual(summary, "尚未填写活动计划。")
        self.assertIs(returned_agent, fresh_agent)
        self.assertEqual([item["role"] for item in next_history], ["user", "assistant"])
        self.assertIn("骑行", next_summary)
        new_session.assert_called_once_with()

    def test_extraction_error_reply_preserves_plan_summary(self):
        from weather_agent.extraction import ActivityExtractionError
        from weather_agent.ui import respond

        agent = Mock()
        agent.plan = ActivityPlan("cycling", "北京", NOW, 3)
        agent.handle_message.side_effect = ActivityExtractionError("bad output")

        _, history, returned_agent, summary = respond(
            "改时间", [], agent, now=NOW
        )

        self.assertIn("换一种说法", history[-1]["content"])
        self.assertIn("北京", summary)
        self.assertIs(returned_agent, agent)


if __name__ == "__main__":
    unittest.main()
