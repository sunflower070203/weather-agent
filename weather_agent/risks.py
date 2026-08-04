from dataclasses import dataclass
from datetime import datetime

from weather_agent.forecast import WeatherPoint


LEVEL_ORDER = {"low": 1, "medium": 2, "high": 3}


@dataclass(frozen=True)
class RiskAssessment:
    kind: str
    level: str
    time: datetime
    value: float
    unit: str
    threshold: float


def _level_at_or_above(value, thresholds):
    level = None
    threshold = None
    for candidate_level, candidate_threshold in thresholds:
        if value >= candidate_threshold:
            level = candidate_level
            threshold = candidate_threshold
    return level, threshold


def _level_at_or_below(value, thresholds):
    level = None
    threshold = None
    for candidate_level, candidate_threshold in thresholds:
        if value <= candidate_threshold:
            level = candidate_level
            threshold = candidate_threshold
    return level, threshold


def assess_weather_risks(points: list[WeatherPoint] | tuple[WeatherPoint, ...]):
    assessments = []
    for point in points:
        candidates = (
            (
                "precipitation",
                point.precipitation_mm_h,
                "mm/hr",
                _level_at_or_above(
                    point.precipitation_mm_h,
                    (("low", 0.1), ("medium", 2.5), ("high", 8.0)),
                ),
            ),
            (
                "wind",
                point.wind_speed_m_s,
                "m/s",
                _level_at_or_above(
                    point.wind_speed_m_s,
                    (("low", 5.5), ("medium", 8.0), ("high", 10.8)),
                ),
            ),
            (
                "high_temperature",
                point.temperature_c,
                "°C",
                _level_at_or_above(
                    point.temperature_c,
                    (("medium", 35.0), ("high", 37.0)),
                ),
            ),
            (
                "low_temperature",
                point.temperature_c,
                "°C",
                _level_at_or_below(
                    point.temperature_c,
                    (("medium", 5.0), ("high", 0.0)),
                ),
            ),
        )
        for kind, value, unit, (level, threshold) in candidates:
            if level is None:
                continue
            assessments.append(
                RiskAssessment(
                    kind=kind,
                    level=level,
                    time=point.time,
                    value=value,
                    unit=unit,
                    threshold=threshold,
                )
            )

    highest_by_kind = {}
    for assessment in assessments:
        current = highest_by_kind.get(assessment.kind)
        if current is None or LEVEL_ORDER[assessment.level] > LEVEL_ORDER[current.level]:
            highest_by_kind[assessment.kind] = assessment
    return list(highest_by_kind.values())
