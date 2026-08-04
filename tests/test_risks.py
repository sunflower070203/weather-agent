import unittest
from datetime import datetime

from weather_agent.forecast import WeatherPoint
from weather_agent.risks import assess_weather_risks


class WeatherRiskTests(unittest.TestCase):
    def test_reports_highest_level_for_each_triggered_risk(self):
        points = [
            self._point(hour=8, temperature=38.0),
            self._point(hour=9, precipitation=9.0),
            self._point(hour=10, wind_speed=11.0),
            self._point(hour=11, temperature=-1.0),
        ]

        risks = assess_weather_risks(points)

        self.assertEqual(
            {(risk.kind, risk.level) for risk in risks},
            {
                ("high_temperature", "high"),
                ("precipitation", "high"),
                ("wind", "high"),
                ("low_temperature", "high"),
            },
        )
        rain = next(risk for risk in risks if risk.kind == "precipitation")
        self.assertEqual(rain.value, 9.0)
        self.assertEqual(rain.time.hour, 9)
        self.assertEqual(rain.unit, "mm/hr")

    def test_returns_no_risks_for_mild_dry_calm_weather(self):
        points = [self._point(hour=8)]

        self.assertEqual(assess_weather_risks(points), [])

    @staticmethod
    def _point(
        *,
        hour,
        temperature=24.0,
        precipitation=0.0,
        wind_speed=3.0,
    ):
        return WeatherPoint(
            time=datetime.fromisoformat(f"2026-08-04T{hour:02d}:00+08:00"),
            wind_direction_deg=180.0,
            wind_speed_m_s=wind_speed,
            temperature_c=temperature,
            relative_humidity_pct=60.0,
            surface_pressure_pa=100000.0,
            precipitation_mm_h=precipitation,
        )


if __name__ == "__main__":
    unittest.main()
