from pathlib import Path

from ai_model_watch.analysis import analyze_documents
from ai_model_watch.clustering import cluster_claims
from ai_model_watch.database import Database
from ai_model_watch.llm.heuristic import HeuristicAnalyzer
from ai_model_watch.models import Document, Source


def test_clustering_creates_evidence_links(tmp_path: Path) -> None:
    database = Database(tmp_path / "cluster.db")
    database.initialize()
    database.upsert_source(Source("Test", "reddit", "https://example.com", 3, "Test", False))
    database.insert_document(Document("Test", "AI coding model", "https://example.com/1", "The AI model improves coding."))
    database.insert_document(Document("Test", "AI coding model issue", "https://example.com/2", "The AI model has a coding problem."))
    analyze_documents(database, HeuristicAnalyzer())

    summary = cluster_claims(database)
    clusters = database.list_clusters()

    assert summary.claims_processed == 2
    assert summary.clusters_created >= 1
    assert sum(int(cluster["evidence_count"]) for cluster in clusters) == 2
