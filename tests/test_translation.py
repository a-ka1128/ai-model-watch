from pathlib import Path

from ai_model_watch.database import Database
from ai_model_watch.models import Document, Source
from ai_model_watch.translation import translate_documents
from ai_model_watch.llm.contracts import ArticleBrief, TranslationResult


class FakeTranslator:
    summary_input: str = ''
    def translate(self, title: str, content: str) -> TranslationResult:
        return TranslationResult(f"한글 {title}", f"한글 {content}")

    def summarize_article(self, title: str, content: str) -> ArticleBrief:
        self.summary_input = content
        return ArticleBrief('핵심 요약', ('핵심 내용',), ())


def test_translation_is_stored_separately_from_original(tmp_path: Path) -> None:
    database = Database(tmp_path / "translation.db")
    database.initialize()
    database.upsert_source(Source("Test", "official", "https://example.com", 1, "TestCo", True))
    database.insert_document(Document("Test", "Original title", "https://example.com/1", "Original content"))
    document_id = database.list_documents(1)[0]['id']
    full_body = 'Full article body ' * 30
    database.update_article_body(document_id, full_body)
    database.update_document_curation(document_id, 'selected', 80, 'relevant')

    translator = FakeTranslator()
    summary = translate_documents(database, translator, limit=10)
    row = database.list_documents(1)[0]

    assert summary.translated == 1
    assert row["title"] == "Original title"
    assert row["content"] == "Original content"
    assert row["translated_title"] == "한글 Original title"
    assert row["translated_content"] == "한글 " + full_body
    assert row['summary_ko'] == '핵심 요약'
    assert full_body in translator.summary_input
    assert '한글 ' not in translator.summary_input
    articles, total = database.list_articles()
    assert total == 1
    assert articles[0]['id'] == document_id
    assert translate_documents(database, translator, limit=10).processed == 0
    assert translate_documents(database, translator, limit=10, force=True).translated == 1
