import os
import unittest
from unittest.mock import Mock

from weather_agent.tjweather import (
    DEFAULT_FIELDS,
    TJWeatherClient,
    TJWeatherConfig,
    TJWeatherError,
)


class TJWeatherClientTests(unittest.TestCase):
    def setUp(self):
        self.config = TJWeatherConfig(
            api_key="secret-key",
            subscription_id="subscription-id",
        )

    def test_builds_request_for_all_subscribed_fields(self):
        client = TJWeatherClient(self.config)

        params = client.build_params(longitude=116.39, latitude=39.90)

        self.assertEqual(params["fields"], ",".join(DEFAULT_FIELDS))
        self.assertEqual(params["loc"], "116.39,39.9")
        self.assertEqual(params["t_res"], "1h")
        self.assertEqual(params["fcst_days"], 10)
        self.assertEqual(params["tz"], 8)
        self.assertEqual(params["key"], "secret-key")
        self.assertEqual(params["subscriptionId"], "subscription-id")

    def test_rejects_coordinates_outside_supported_range(self):
        client = TJWeatherClient(self.config)

        with self.assertRaisesRegex(ValueError, "longitude"):
            client.build_params(longitude=181, latitude=39.90)

        with self.assertRaisesRegex(ValueError, "latitude"):
            client.build_params(longitude=116.39, latitude=91)

    def test_raises_domain_error_for_non_success_api_code(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 20004, "message": "参数值非法"}
        session = Mock()
        session.get.return_value = response
        client = TJWeatherClient(self.config, session=session)

        with self.assertRaisesRegex(TJWeatherError, "20004"):
            client.fetch(longitude=116.39, latitude=39.90)

    def test_loads_credentials_from_environment(self):
        old_key = os.environ.get("TJWEATHER_API_KEY")
        old_subscription = os.environ.get("TJWEATHER_SUBSCRIPTION_ID")
        try:
            os.environ["TJWEATHER_API_KEY"] = "env-key"
            os.environ["TJWEATHER_SUBSCRIPTION_ID"] = "env-subscription"

            config = TJWeatherConfig.from_environment()

            self.assertEqual(config.api_key, "env-key")
            self.assertEqual(config.subscription_id, "env-subscription")
        finally:
            if old_key is None:
                os.environ.pop("TJWEATHER_API_KEY", None)
            else:
                os.environ["TJWEATHER_API_KEY"] = old_key
            if old_subscription is None:
                os.environ.pop("TJWEATHER_SUBSCRIPTION_ID", None)
            else:
                os.environ["TJWEATHER_SUBSCRIPTION_ID"] = old_subscription


if __name__ == "__main__":
    unittest.main()
