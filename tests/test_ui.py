import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from weather_agent.activity import ActivityPlan


NOW = datetime(2026, 8, 4, 14, 0, tzinfo=timezone(timedelta(hours=8)))


class UIAdapterTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
