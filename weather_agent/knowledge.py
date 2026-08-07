"""Deterministic knowledge base for activity-weather advice.

This is a deliberately small capability: curated entries are retrieved by
activity and risk-topic matching, and every recommendation cites its source
entry id. No embeddings or external services are involved.
"""

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_KNOWLEDGE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "outdoor-advice.json"
)


@dataclass(frozen=True)
class AdviceEntry:
    id: str
    activity: str
    topics: tuple[str, ...]
    text: str


class KnowledgeBase:
    def __init__(self, entries):
        self.entries = tuple(entries)

    @classmethod
    def from_json(cls, path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            AdviceEntry(
                id=item["id"],
                activity=item["activity"],
                topics=tuple(item["topics"]),
                text=item["text"],
            )
            for item in raw
        )

    @classmethod
    def default(cls):
        return cls.from_json(DEFAULT_KNOWLEDGE_PATH)

    def advice_for(self, activity, topics, limit=2):
        if not topics:
            topics = ("general",)
        matches = []
        for entry in self.entries:
            activity_match = entry.activity == activity
            topic_match = any(topic in entry.topics for topic in topics)
            if not (topic_match and (activity_match or entry.activity == "any")):
                continue
            score = 0
            if activity_match:
                score += 2
            elif entry.activity == "any":
                score += 1
            if topic_match:
                score += 3
            matches.append((score, entry))
        matches.sort(key=lambda pair: (-pair[0], pair[1].id))
        return [entry for _, entry in matches[:limit]]


DEFAULT_KNOWLEDGE = KnowledgeBase.default()
