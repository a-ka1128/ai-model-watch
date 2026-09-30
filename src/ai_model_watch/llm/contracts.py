from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RelevanceResult:
    relevant: bool
    company: str | None = None
    topics: tuple[str, ...] = ()
    summary_ko: str = ""


@dataclass(frozen=True)
class TranslationResult:
    title_ko: str
    content_ko: str


@dataclass(frozen=True)
class ArticleBrief:
    summary_ko: str
    key_points: tuple[str, ...]
    cautions: tuple[str, ...]


@dataclass(frozen=True)
class ArticleQuality:
    score: int
    reason: str


class Translator(Protocol):
    def translate(self, title: str, content: str) -> TranslationResult:
        """Translate a stored document into Korean without changing its meaning."""

    def summarize_article(self, title: str, content: str) -> ArticleBrief:
        """Organize an article into source-supported Korean notes."""


class ArticleCurator(Protocol):
    def assess_quality(self, title: str, content: str, source_name: str, reliability: int) -> ArticleQuality:
        """Assess whether an AI news article is useful enough to translate."""


class RelevanceFilter(Protocol):
    def classify(self, title: str, content: str) -> RelevanceResult:
        """Return structured relevance metadata for a stored document."""


class ClaimExtractor(Protocol):
    def extract(self, title: str, content: str, source_type: str = "") -> list[dict[str, object]]:
        """Return evidence-backed claim objects; never invent missing fields."""


class StructuredAnalyzer(RelevanceFilter, ClaimExtractor, Protocol):
    """Combined contract used by the document analysis pipeline."""
