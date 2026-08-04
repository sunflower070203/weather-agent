from dataclasses import dataclass
from datetime import datetime


REQUIRED_POINT_FIELDS = (
    "time",
    "wd10m",
    "ws10m",
    "t2m",
    "rh2m",
    "psz",
    "tp",
)


class ForecastDataError(ValueError):
    """Raised when the weather API returns incomplete forecast data."""


@dataclass(frozen=True)
class WeatherPoint:
    time: datetime
    wind_direction_deg: float
    wind_speed_m_s: float
    temperature_c: float
    relative_humidity_pct: float
    surface_pressure_pa: float
    precipitation_mm_h: float


@dataclass(frozen=True)
class WeatherForecast:
    time_init: datetime
    points: tuple[WeatherPoint, ...]

    @classmethod
    def from_api(cls, payload):
        try:
            time_init = datetime.fromisoformat(payload["time_init"])
            raw_points = payload["data"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ForecastDataError("forecast metadata is invalid") from exc

        points = []
        for raw_point in raw_points:
            for field in REQUIRED_POINT_FIELDS:
                if field not in raw_point or raw_point[field] is None:
                    raise ForecastDataError(f"forecast point is missing {field}")
            try:
                points.append(
                    WeatherPoint(
                        time=datetime.fromisoformat(raw_point["time"]),
                        wind_direction_deg=float(raw_point["wd10m"]),
                        wind_speed_m_s=float(raw_point["ws10m"]),
                        temperature_c=float(raw_point["t2m"]),
                        relative_humidity_pct=float(raw_point["rh2m"]),
                        surface_pressure_pa=float(raw_point["psz"]),
                        precipitation_mm_h=float(raw_point["tp"]),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ForecastDataError("forecast point contains an invalid value") from exc

        return cls(time_init=time_init, points=tuple(points))

    def between(self, start, end):
        if end <= start:
            raise ValueError("activity end must be later than start")
        return tuple(point for point in self.points if start <= point.time < end)
