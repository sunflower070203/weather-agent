import os
import unittest
from unittest.mock import Mock

from weather_agent.modelscope import ModelScopeClient, ModelScopeError


class ModelScopeClientTests(unittest.TestCase):
    def test_loads_token_from_environment(self):
        old_token = os.environ.get("MODELSCOPE_ACCESS_TOKEN")
        try:
            os.environ["MODELSCOPE_ACCESS_TOKEN"] = "env-token"

            client = ModelScopeClient.from_environment(session=Mock())

            self.assertEqual(client.access_token, "env-token")
        finally:
            if old_token is None:
                os.environ.pop("MODELSCOPE_ACCESS_TOKEN", None)
            else:
                os.environ["MODELSCOPE_ACCESS_TOKEN"] = old_token

    def test_requests_and_parses_json_object_response(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"activity_type":"cycling","location":"北京"}'
                    }
                }
            ]
        }
        session = Mock()
        session.post.return_value = response
        client = ModelScopeClient("token", session=session)

        result = client.complete_json([{"role": "user", "content": "测试"}])

        self.assertEqual(result["activity_type"], "cycling")
        _, call_kwargs = session.post.call_args
        self.assertEqual(call_kwargs["json"]["model"], "Qwen/Qwen3.5-27B")
        self.assertEqual(
            call_kwargs["json"]["response_format"], {"type": "json_object"}
        )
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer token")

    def test_raises_domain_error_when_model_content_is_not_json(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "不是 JSON"}}]
        }
        session = Mock()
        session.post.return_value = response

        with self.assertRaisesRegex(ModelScopeError, "valid JSON"):
            ModelScopeClient("token", session=session).complete_json([])


if __name__ == "__main__":
    unittest.main()
