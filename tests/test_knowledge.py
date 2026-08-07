import unittest

from weather_agent.knowledge import AdviceEntry, KnowledgeBase


ENTRIES = [
    AdviceEntry("heat-camping", "camping", ("high_temperature",), "高温露营注意通风。"),
    AdviceEntry("heat-any", "any", ("high_temperature",), "高温注意补水。"),
    AdviceEntry("rain-camping", "camping", ("precipitation",), "降雨露营防潮。"),
    AdviceEntry("general-any", "any", ("general",), "出发前核对临近预报。"),
]


class KnowledgeBaseTests(unittest.TestCase):
    def test_matches_activity_and_topic(self):
        entries = KnowledgeBase(ENTRIES).advice_for("camping", ["high_temperature"])
        self.assertEqual(entries[0].id, "heat-camping")
        self.assertIn("heat-any", {entry.id for entry in entries})

    def test_general_fallback_without_topics(self):
        entries = KnowledgeBase(ENTRIES).advice_for("hiking", [])
        self.assertEqual([entry.id for entry in entries], ["general-any"])

    def test_limits_results_and_orders_by_score(self):
        entries = KnowledgeBase(ENTRIES).advice_for(
            "camping", ["high_temperature"], limit=2
        )
        self.assertLessEqual(len(entries), 2)
        self.assertEqual(entries[0].id, "heat-camping")

    def test_loads_corpus_from_disk(self):
        knowledge = KnowledgeBase.default()
        self.assertGreaterEqual(len(knowledge.entries), 12)


if __name__ == "__main__":
    unittest.main()

