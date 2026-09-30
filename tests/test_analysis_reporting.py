from pathlib import Path

from ai_model_watch.analysis import analyze_documents
from ai_model_watch.database import Database
from ai_model_watch.llm.heuristic import HeuristicAnalyzer
from ai_model_watch.models import Document, Source
from ai_model_watch.reporting import generate_weekly_report


def test_analysis_stores_claim_and_report_links_evidence(tmp_path: Path) -> None:
    database = Database(tmp_path / "watch.db")
    database.initialize()
    database.upsert_source(Source("Test", "reddit", "https://example.com", 3, "Test", False))
    database.insert_document(Document("Test", "New AI model", "https://example.com/post", "The model improves coding."))

    summary = analyze_documents(database, HeuristicAnalyzer())
    report = generate_weekly_report(database, week="2026-W39")

    assert summary.claims_inserted == 1
    assert "https://example.com/post" in report.content
    assert "Insufficient Evidence" not in report.content


class _ClaimsWithReliability:
    def __init__(self, reliability): self.reliability = reliability; self.source_types = []
    def classify(self, title, content):
        from ai_model_watch.llm.contracts import RelevanceResult
        return RelevanceResult(True)
    def extract(self, title, content, source_type=""):
        self.source_types.append(source_type)
        return [{"claim_text": "Claim about the model", "reliability": self.reliability}]


def test_model_cannot_raise_reliability_above_source_default(tmp_path: Path) -> None:
    database = Database(tmp_path / "watch.db")
    database.initialize()
    database.upsert_source(Source("Community", "reddit", "https://example.com/r", 3, "Test", False))
    database.upsert_source(Source("Official", "official", "https://example.com/o", 1, "Test", True))
    database.insert_document(Document("Community", "Post", "https://example.com/r/1", "body one"))
    database.insert_document(Document("Official", "Post", "https://example.com/o/1", "body two"))
    analyzer = _ClaimsWithReliability(1)
    analyze_documents(database, analyzer)
    levels = {row["source_name"]: row["reliability"] for row in database.list_claims(10)}
    assert levels == {"Community": 3, "Official": 1}
    assert sorted(analyzer.source_types) == ["official", "reddit"]
    # A model may still lower trust for an official source, and junk values fall back to the default.
    database2 = Database(tmp_path / "watch2.db")
    database2.initialize()
    database2.upsert_source(Source("Official", "official", "https://example.com/o", 1, "Test", True))
    database2.insert_document(Document("Official", "Post", "https://example.com/o/1", "body"))
    analyze_documents(database2, _ClaimsWithReliability(2))
    assert database2.list_claims(10)[0]["reliability"] == 2
