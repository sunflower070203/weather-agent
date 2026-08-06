import json
from dataclasses import asdict


ALLOWED_UPDATE_FIELDS = {
    "activity_type",
    "location",
    "start_time",
    "duration_hours",
    "participant_profile",
    "risk_preference",
}


class ActivityExtractionError(ValueError):
    """Raised when model output cannot safely update an activity plan."""


class ActivityExtractor:
    def __init__(self, model):
        self.model = model

    def update_plan(self, plan, user_message, *, now):
        current_plan = asdict(plan)
        if current_plan["start_time"] is not None:
            current_plan["start_time"] = current_plan["start_time"].isoformat()
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract activity-plan updates as one JSON object. "
                    "Allowed activity_type values: cycling, hiking, camping. "
                    "Allowed fields: activity_type, location, start_time, "
                    "duration_hours, participant_profile, risk_preference. "
                    "Use an ISO-8601 timestamp with timezone for start_time. "
                    "Omit fields not stated or changed by the user."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "now": now.isoformat(),
                        "current_plan": current_plan,
                        "message": user_message,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        extracted = self.model.complete_json(messages)
        if not isinstance(extracted, dict):
            raise ActivityExtractionError("model response must be a JSON object")
        updates = {
            key: value
            for key, value in extracted.items()
            if key in ALLOWED_UPDATE_FIELDS and value is not None
        }
        try:
            return plan.with_updates(updates)
        except (TypeError, ValueError) as exc:
            raise ActivityExtractionError("model returned an invalid update") from exc
