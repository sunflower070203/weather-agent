"""Data-driven alternative-window planning for activity weather decisions."""

import math
from datetime import timedelta

from weather_agent.risks import LEVEL_ORDER, assess_weather_risks


def _window_is_clear(points):
    return all(
        assessment.level not in ("medium", "high")
        for assessment in assess_weather_risks(points)
    )


def find_clear_window(points, start_time, duration_hours, *, search_radius_hours=48):
    """Return the nearest duration-sized window without medium/high risks.

    The window length is the ceiling of the duration in whole hours, so a
    three-hour activity covers three hourly points. Returns ``(start, end)``
    or ``None`` when no clear window exists inside the search radius.
    """
    if not points:
        return None
    size = max(1, math.ceil(duration_hours))
    ordered = sorted(points, key=lambda point: point.time)
    if size > len(ordered):
        return None

    lower = start_time - timedelta(hours=search_radius_hours)
    upper = start_time + timedelta(hours=search_radius_hours)
    best = None
    for index in range(0, len(ordered) - size + 1):
        window = ordered[index : index + size]
        if window[0].time < lower or window[-1].time > upper:
            continue
        if not _window_is_clear(window):
            continue
        start = window[0].time
        end = start + timedelta(hours=size)
        distance = abs((start - start_time).total_seconds())
        if best is None or distance < best[0] or (
            distance == best[0] and start < best[1][0]
        ):
            best = (distance, (start, end))
    return best[1] if best else None


def peak_risks(risks):
    """Highest-level risk per kind, preserving the assessment detail."""
    peaks = {}
    for risk in risks:
        current = peaks.get(risk.kind)
        if current is None or LEVEL_ORDER[risk.level] > LEVEL_ORDER[current.level]:
            peaks[risk.kind] = risk
    return tuple(peaks.values())

