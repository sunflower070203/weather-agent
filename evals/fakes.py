"""Scripted doubles used by the deterministic evaluation scenarios."""

from weather_agent.activity import ActivityPlan
from weather_agent.geocoding import GeocodingError, LocationCandidate
from weather_agent.tjweather import TJWeatherError


class ScriptedExtractor:
    """Applies one plan update per call, in scenario order."""

    def __init__(self, updates):
        self.updates = list(updates)
        self.calls = 0

    def update_plan(self, plan, user_message, *, now):
        self.calls += 1
        if self.calls - 1 >= len(self.updates):
            return plan
        return plan.with_updates(self.updates[self.calls - 1])


class FakeGeocoder:
    """Returns the next configured result set for each search."""

    def __init__(self, result_sets, error=None):
        self.result_sets = [tuple(items) for items in result_sets]
        self.error = error
        self.queries = []
        self.calls = 0

    def search(self, query):
        self.queries.append(query)
        self.calls += 1
        if self.error:
            raise self.error
        if not self.result_sets:
            return ()
        index = min(self.calls - 1, len(self.result_sets) - 1)
        return self.result_sets[index]


class FakeWeather:
    """Returns a fixed payload or raises a configured service error."""

    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    def fetch(self, *, longitude, latitude):
        self.calls.append((longitude, latitude))
        if self.error:
            raise self.error
        return self.payload


def candidate_from_dict(data):
    return LocationCandidate(
        name=data["name"],
        latitude=float(data["latitude"]),
        longitude=float(data["longitude"]),
        country=data.get("country", "中国"),
        admin1=data.get("admin1"),
        timezone=data.get("timezone", "Asia/Shanghai"),
        resolved_query=data.get("resolved_query"),
        is_approximate=bool(data.get("is_approximate", False)),
    )


def geocoding_error(name):
    return {"GeocodingError": GeocodingError("simulated geocoding failure")}.get(name)


def weather_error(name):
    return {"TJWeatherError": TJWeatherError("simulated weather failure")}.get(name)


def empty_plan():
    return ActivityPlan()

