from pathlib import Path

from ai_model_watch.database import Database
from ai_model_watch.models import Document, Source


def test_document_insert_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    database.initialize()
    database.upsert_source(
        Source("Test", "official", "https://example.com", 1, "TestCo", True)
    )
    document = Document("Test", "Title", "https://example.com/1", "Same evidence")

    assert database.insert_document(document) is True
    assert database.insert_document(document) is False
    assert database.count_documents() == 1
