import unittest
from datetime import datetime

from weather_agent.activity import ActivityPlan


class ActivityPlanTests(unittest.TestCase):
    def test_reports_required_fields_in_question_order(self):
        plan = ActivityPlan()

        self.assertEqual(
            plan.missing_fields(),
            ("activity_type", "location", "start_time", "duration_hours"),
        )

    def test_asks_only_the_next_missing_question(self):
        plan = ActivityPlan(activity_type="cycling", location="北京奥森公园")

        self.assertEqual(plan.next_question(), "活动计划从什么时候开始？")

    def test_updates_one_field_without_losing_existing_state(self):
        plan = ActivityPlan(
            activity_type="hiking",
            location="香山",
            start_time=datetime.fromisoformat("2026-08-06T08:00+08:00"),
            duration_hours=3.0,
        )

        updated = plan.with_updates(
            {"start_time": "2026-08-07T09:00+08:00", "duration_hours": 2}
        )

        self.assertEqual(updated.activity_type, "hiking")
        self.assertEqual(updated.location, "香山")
        self.assertEqual(
            updated.start_time,
            datetime.fromisoformat("2026-08-07T09:00+08:00"),
        )
        self.assertEqual(updated.duration_hours, 2.0)

    def test_rejects_unsupported_activity_type(self):
        with self.assertRaisesRegex(ValueError, "activity_type"):
            ActivityPlan(activity_type="swimming")

    def test_rejects_non_positive_duration(self):
        with self.assertRaisesRegex(ValueError, "duration_hours"):
            ActivityPlan(duration_hours=0)

    def test_is_ready_when_all_required_fields_are_present(self):
        plan = ActivityPlan(
            activity_type="camping",
            location="海坨山谷",
            start_time=datetime.fromisoformat("2026-08-06T14:00+08:00"),
            duration_hours=18.0,
        )

        self.assertTrue(plan.is_ready())
        self.assertIsNone(plan.next_question())
        self.assertEqual(plan.participant_profile, "general_adults")
        self.assertEqual(plan.risk_preference, "moderate")


if __name__ == "__main__":
    unittest.main()
