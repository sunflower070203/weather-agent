import unittest
from datetime import datetime

from weather_agent.forecast import ForecastDataError, WeatherForecast


class WeatherForecastTests(unittest.TestCase):
    def test_parses_api_points_into_typed_forecast(self):
        payload = {
            "time_init": "2026-08-03T20:00+08:00",
            "units": {
                "wd10m": "deg",
                "ws10m": "m/s",
                "t2m": "C",
                "rh2m": "%",
                "psz": "Pa",
                "tp": "mm/hr",
            },
            "data": [
                {
                    "time": "2026-08-04T08:00+08:00",
                    "wd10m": 180.0,
                    "ws10m": 3.2,
                    "t2m": 26.5,
                    "rh2m": 70.0,
                    "psz": 100200.0,
                    "tp": 0.0,
                }
            ],
        }

        forecast = WeatherForecast.from_api(payload)

        self.assertEqual(
            forecast.time_init,
            datetime.fromisoformat("2026-08-03T20:00+08:00"),
        )
        self.assertEqual(len(forecast.points), 1)
        self.assertEqual(forecast.points[0].temperature_c, 26.5)
        self.assertEqual(forecast.points[0].precipitation_mm_h, 0.0)

    def test_rejects_point_with_missing_required_weather_field(self):
        payload = {
            "time_init": "2026-08-03T20:00+08:00",
            "units": {},
            "data": [
                {
                    "time": "2026-08-04T08:00+08:00",
                    "wd10m": 180.0,
                    "t2m": 26.5,
                }
            ],
        }

        with self.assertRaisesRegex(ForecastDataError, "ws10m"):
            WeatherForecast.from_api(payload)

    def test_selects_only_points_inside_activity_window(self):
        payload = {
            "time_init": "2026-08-03T20:00+08:00",
            "units": {},
            "data": [
                self._point("2026-08-04T07:00+08:00"),
                self._point("2026-08-04T08:00+08:00"),
                self._point("2026-08-04T09:00+08:00"),
                self._point("2026-08-04T10:00+08:00"),
            ],
        }
        forecast = WeatherForecast.from_api(payload)

        selected = forecast.between(
            datetime.fromisoformat("2026-08-04T08:00+08:00"),
            datetime.fromisoformat("2026-08-04T10:00+08:00"),
        )

        self.assertEqual([point.time.hour for point in selected], [8, 9])

    @staticmethod
    def _point(time):
        return {
            "time": time,
            "wd10m": 180.0,
            "ws10m": 3.2,
            "t2m": 26.5,
            "rh2m": 70.0,
            "psz": 100200.0,
            "tp": 0.0,
        }


if __name__ == "__main__":
    unittest.main()
