from dataclasses import dataclass, replace
from datetime import datetime


SUPPORTED_ACTIVITY_TYPES = {"cycling", "hiking", "camping"}
ALLOWED_RISK_PREFERENCES = {"conservative", "moderate", "adventurous"}
REQUIRED_FIELDS = ("activity_type", "location", "start_time", "duration_hours")
QUESTIONS = {
    "activity_type": "你计划骑行、徒步还是露营？",
    "location": "活动地点在哪里？",
    "start_time": "活动计划从什么时候开始？",
    "duration_hours": "预计持续多少小时？",
}


@dataclass(frozen=True)
class ActivityPlan:
    activity_type: str | None = None
    location: str | None = None
    start_time: datetime | None = None
    duration_hours: float | None = None
    participant_profile: str = "general_adults"
    risk_preference: str = "moderate"

    def __post_init__(self):
        if (
            self.activity_type is not None
            and self.activity_type not in SUPPORTED_ACTIVITY_TYPES
        ):
            raise ValueError("activity_type must be cycling, hiking, or camping")
        if self.duration_hours is not None and self.duration_hours <= 0:
            raise ValueError("duration_hours must be positive")
        if (
            self.risk_preference is not None
            and self.risk_preference not in ALLOWED_RISK_PREFERENCES
        ):
            raise ValueError(
                "risk_preference must be conservative, moderate, or adventurous"
            )

    def missing_fields(self):
        return tuple(field for field in REQUIRED_FIELDS if getattr(self, field) is None)

    def next_question(self):
        missing = self.missing_fields()
        return QUESTIONS[missing[0]] if missing else None

    def is_ready(self):
        return not self.missing_fields()

    def with_updates(self, updates):
        normalized = dict(updates)
        if "start_time" in normalized and isinstance(normalized["start_time"], str):
            normalized["start_time"] = datetime.fromisoformat(normalized["start_time"])
        if "duration_hours" in normalized and normalized["duration_hours"] is not None:
            normalized["duration_hours"] = float(normalized["duration_hours"])
        return replace(self, **normalized)
