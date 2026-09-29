from __future__ import annotations

from .contracts import RelevanceResult
from .keyword import KeywordRelevanceFilter


class HeuristicAnalyzer:
    """Offline-safe fallback that never creates unsupported numeric findings."""

    def __init__(self) -> None:
        self.relevance = KeywordRelevanceFilter()

    def classify(self, title: str, content: str) -> RelevanceResult:
        return self.relevance.classify(title, content)

    def extract(self, title: str, content: str) -> list[dict[str, object]]:
        result = self.classify(title, content)
        if not result.relevant:
            return []
        return [{
            "company": None,
            "product": None,
            "model": None,
            "topic": result.topics[0] if result.topics else None,
            "task": None,
            "effort": None,
            "claim_text": content.strip() or title.strip(),
            "reliability": 3,
        }]
