import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


BASE_URL = "https://api.tjweather.com/v2"
DEFAULT_FIELDS = ("wd10m", "ws10m", "t2m", "rh2m", "psz", "tp")


class TJWeatherError(RuntimeError):
    """Raised when the weather service cannot return usable data."""


@dataclass(frozen=True)
class TJWeatherConfig:
    api_key: str
    subscription_id: str

    @classmethod
    def from_environment(cls):
        api_key = os.environ.get("TJWEATHER_API_KEY")
        subscription_id = os.environ.get("TJWEATHER_SUBSCRIPTION_ID")
        if not api_key or not subscription_id:
            raise TJWeatherError(
                "TJWEATHER_API_KEY and TJWEATHER_SUBSCRIPTION_ID are required"
            )
        return cls(api_key=api_key, subscription_id=subscription_id)


class _UrlLibResponse:
    def __init__(self, response):
        self._response = response

    def raise_for_status(self):
        return None

    def json(self):
        return json.loads(self._response.read().decode("utf-8"))


class _UrlLibSession:
    def get(self, url, *, params, timeout):
        request_url = f"{url}?{urlencode(params)}"
        try:
            return _UrlLibResponse(urlopen(request_url, timeout=timeout))
        except HTTPError as exc:
            raise TJWeatherError(f"weather service HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise TJWeatherError("weather service request failed") from exc


class TJWeatherClient:
    def __init__(self, config, *, session=None, time_resolution="1h"):
        self.config = config
        self.session = session or _UrlLibSession()
        self.time_resolution = time_resolution

    def build_params(self, *, longitude, latitude):
        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return {
            "fields": ",".join(DEFAULT_FIELDS),
            "loc": f"{longitude},{latitude}",
            "t_res": self.time_resolution,
            "fcst_days": 10,
            "fcst_hours": 0,
            "tz": 8,
            "key": self.config.api_key,
            "subscriptionId": self.config.subscription_id,
        }

    def fetch(self, *, longitude, latitude):
        response = self.session.get(
            BASE_URL,
            params=self.build_params(longitude=longitude, latitude=latitude),
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 200:
            raise TJWeatherError(
                f"weather service error {payload.get('code')}: "
                f"{payload.get('message', 'unknown error')}"
            )
        return payload["data"]
