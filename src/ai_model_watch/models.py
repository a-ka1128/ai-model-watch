from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Source:
    name: str
    source_type: str
    url: str
    reliability_default: int
    company: str
    is_official: bool
    collection_method: str = "rss"


@dataclass(frozen=True)
class Document:
    source_name: str
    title: str
    url: str
    content: str
    author: str | None = None
    published_at: datetime | None = None
    language: str | None = None


@dataclass(frozen=True)
class Claim:
    document_id: int
    company: str | None
    product: str | None
    model: str | None
    topic: str | None
    task: str | None
    effort: str | None
    claim_text: str
    reliability: int


@dataclass(frozen=True)
class WeeklyReport:
    week: str
    title: str
    summary: str
    content: str


@dataclass(frozen=True)
class EvidenceCluster:
    topic: str
    summary: str
    reliability: int
    confidence: float | None = None
