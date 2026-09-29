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
