import unittest
from datetime import datetime, timedelta, timezone

from weather_agent.forecast import WeatherPoint
from weather_agent.planning import find_clear_window, peak_risks
from weather_agent.risks import RiskAssessment


TZ = timezone(timedelta(hours=8))


def point(hour, *, rain=0.0, wind=2.0, temperature=25.0):
    return WeatherPoint(
        time=datetime(2026, 8, 8, hour, tzinfo=TZ),
        wind_direction_deg=180,
        wind_speed_m_s=wind,
        temperature_c=temperature,
        relative_humidity_pct=60,
        surface_pressure_pa=100000,
        precipitation_mm_h=rain,
    )


class FindClearWindowTests(unittest.TestCase):
    def test_finds_nearest_clear_window(self):
        points = [
            point(8, rain=3.0),
            point(9, rain=3.0),
            point(10, rain=3.0),
            point(11),
            point(12),
            point(13),
            point(14, rain=3.0),
            point(15, rain=3.0),
            point(16, rain=3.0),
        ]
        start = datetime(2026, 8, 8, 8, 0, tzinfo=TZ)

        window = find_clear_window(points, start, 3.0)

        self.assertIsNotNone(window)
        self.assertEqual(window[0].hour, 11)
        self.assertEqual(window[1].hour, 14)

    def test_returns_none_when_no_clear_window(self):
        points = [point(hour, rain=3.0) for hour in range(8, 17)]
        start = datetime(2026, 8, 8, 8, 0, tzinfo=TZ)

        self.assertIsNone(find_clear_window(points, start, 3.0))

    def test_uses_ceiling_duration(self):
        points = [
            point(8, rain=3.0),
            point(9, rain=3.0),
            point(10),
            point(11),
            point(12),
        ]
        start = datetime(2026, 8, 8, 8, 0, tzinfo=TZ)

        window = find_clear_window(points, start, 2.5)

        self.assertIsNotNone(window)
        self.assertEqual(window[0].hour, 10)


class PeakRisksTests(unittest.TestCase):
    def test_returns_highest_level_per_kind(self):
        risks = (
            RiskAssessment(
                kind="precipitation",
                level="medium",
                time=datetime(2026, 8, 8, 8, 0, tzinfo=TZ),
                value=3.0,
                unit="mm/hr",
                threshold=2.5,
            ),
            RiskAssessment(
                kind="precipitation",
                level="high",
                time=datetime(2026, 8, 8, 9, 0, tzinfo=TZ),
                value=9.0,
                unit="mm/hr",
                threshold=8.0,
            ),
            RiskAssessment(
                kind="wind",
                level="low",
                time=datetime(2026, 8, 8, 8, 0, tzinfo=TZ),
                value=6.0,
                unit="m/s",
                threshold=5.5,
            ),
        )

        peaks = peak_risks(risks)

        by_kind = {risk.kind: risk for risk in peaks}
        self.assertEqual(by_kind["precipitation"].level, "high")
        self.assertEqual(by_kind["wind"].level, "low")


if __name__ == "__main__":
    unittest.main()

