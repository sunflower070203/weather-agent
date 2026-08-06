import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
MUNICIPALITIES = ("北京", "天津", "上海", "重庆")


class GeocodingError(RuntimeError):
    """Raised when a place name cannot be sent to the geocoding service."""


@dataclass(frozen=True)
class LocationCandidate:
    name: str
    latitude: float
    longitude: float
    country: str | None
    admin1: str | None
    timezone: str | None
    resolved_query: str | None = None
    is_approximate: bool = False

    @property
    def display_name(self):
        parts = (self.name, self.admin1, self.country)
        return ", ".join(part for part in parts if part)


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
            raise GeocodingError(f"geocoding service HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise GeocodingError("geocoding service request failed") from exc


class GeocodingClient:
    def __init__(self, *, session=None):
        self.session = session or _UrlLibSession()

    def search(self, query):
        normalized_query = query.strip()
        if not normalized_query:
            raise GeocodingError("location query cannot be blank")

        results = self._request(normalized_query)
        resolved_query = normalized_query
        is_approximate = False
        if not results:
            municipality = next(
                (city for city in MUNICIPALITIES if normalized_query.startswith(city)),
                None,
            )
            if municipality and municipality != normalized_query:
                results = self._request(municipality)
                resolved_query = municipality
                is_approximate = bool(results)

        normalized_city = normalized_query.removesuffix("市")
        if normalized_city in MUNICIPALITIES:
            municipality_results = [
                result
                for result in results
                if result.get("name", "").removesuffix("市") == normalized_city
                and result.get("admin1", "").removesuffix("市") == normalized_city
            ]
            if municipality_results:
                results = municipality_results[:1]

        return tuple(
            LocationCandidate(
                name=result["name"],
                latitude=float(result["latitude"]),
                longitude=float(result["longitude"]),
                country=result.get("country"),
                admin1=result.get("admin1"),
                timezone=result.get("timezone"),
                resolved_query=resolved_query,
                is_approximate=is_approximate,
            )
            for result in results
        )

    def _request(self, query):
        response = self.session.get(
            GEOCODING_URL,
            params={
                "name": query,
                "count": 5,
                "language": "zh",
                "format": "json",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("results", [])
