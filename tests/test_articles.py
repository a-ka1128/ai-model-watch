from pathlib import Path
from unittest.mock import patch

from ai_model_watch.collectors.rss import collect_rss
from ai_model_watch.config import Settings
from ai_model_watch.database import Database
from ai_model_watch.models import Document, Source
from ai_model_watch.llm.openai_compatible import preserve_product_names


def test_atom_content_is_collected_as_readable_post_body(tmp_path: Path):
    payload = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>New model</title>
    <link href="https://www.reddit.com/r/test/comments/abc/post/"/>
    <content type="html">&lt;p&gt;Actual post body, not just the title.&lt;/p&gt;&lt;p&gt;Second paragraph.&lt;/p&gt;</content>
    </entry></feed>'''
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return payload
    source = Source('Reddit test', 'reddit', 'https://www.reddit.com/r/test/.rss', 3, 'Test', False)
    with patch('urllib.request.urlopen', return_value=Response()):
        documents = collect_rss(source, Settings(tmp_path / 'test.db'))
    assert 'Actual post body' in documents[0].content
    assert 'Second paragraph.' in documents[0].content
    assert '<p>' not in documents[0].content


def test_uncollected_and_untranslated_docs_are_not_published(tmp_path: Path):
    database = Database(tmp_path / 'test.db')
    database.initialize()
    database.upsert_source(Source('Test', 'official', 'https://example.com', 1, 'Test', True))
    database.insert_document(Document('Test', 'Title', 'https://example.com/a', 'RSS teaser'))
    document_id = database.list_documents()[0]['id']
    database.update_document_translation(document_id, '제목', '소개문 번역')
    assert database.list_articles()[1] == 0
    database.update_article_body(document_id, 'Full original body')
    assert database.get_document(document_id)['translated_content'] is None
    database.update_document_translation(document_id, '제목', '한글 본문')
    assert database.list_articles()[1] == 0
    database.update_article_brief(document_id, '요약', ('요점',), ())
    assert database.list_articles()[1] == 0  # not curated yet
    database.update_document_curation(document_id, 'selected', 80, 'relevant')
    assert database.list_articles(query='요약', source='official')[1] == 1
    assert database.list_articles(source='reddit')[1] == 0
    database.update_article_body(document_id, None, '403 Forbidden')
    assert database.list_articles()[1] == 0
    assert database.article_stats()['failed'] == 1
    assert database.list_body_candidates() == []


def test_updated_feed_body_does_not_duplicate_the_same_post(tmp_path: Path):
    database = Database(tmp_path / 'test.db')
    database.initialize()
    database.upsert_source(Source('Test', 'reddit', 'https://example.com', 3, 'Test', False))
    assert database.insert_document(Document('Test', 'Title', 'https://example.com/a', 'RSS teaser'))
    assert not database.insert_document(Document('Test', 'Title', 'https://example.com/a', 'Actual post body'))
    assert database.count_documents() == 1
    assert database.list_documents()[0]['content'] == 'Actual post body'


def test_claude_brand_is_not_translated_as_cloud():
    assert preserve_product_names('Are we praising Claude?', '클라우드를 칭찬하는가?') == 'Claude를 칭찬하는가?'
    assert preserve_product_names('Claude uses cloud services', '클라우드 서비스') == '클라우드 서비스'


def test_recency_filter_skips_old_documents(tmp_path: Path):
    from datetime import datetime, timedelta, timezone
    database = Database(tmp_path / 'test.db')
    database.initialize()
    database.upsert_source(Source('Test', 'official', 'https://example.com', 1, 'Test', True))
    now = datetime.now(timezone.utc)
    database.insert_document(Document('Test', 'Old', 'https://example.com/old', 'old body', published_at=now - timedelta(weeks=10)))
    database.insert_document(Document('Test', 'New', 'https://example.com/new', 'new body', published_at=now - timedelta(days=2)))
    database.insert_document(Document('Test', 'Undated', 'https://example.com/undated', 'undated body'))
    settings = Settings(tmp_path / 'test.db', max_age_days=28)
    titles = lambda rows: {row['title'] for row in rows}
    assert titles(database.list_body_candidates(since=settings.since)) == {'New', 'Undated'}
    assert titles(database.list_body_candidates(since=Settings(tmp_path / 'x.db', max_age_days=0).since)) == {'Old', 'New', 'Undated'}
    for doc in database.list_documents():
        database.update_article_body(int(doc['id']), 'body')
    assert titles(database.list_documents_for_curation(since=settings.since)) == {'New', 'Undated'}
    for doc in database.list_documents():
        database.update_document_curation(int(doc['id']), 'selected', 80, 'ok')
    assert titles(database.list_documents_for_translation(curated_only=True, since=settings.since)) == {'New', 'Undated'}


def test_backlog_is_processed_round_robin_across_sources(tmp_path: Path):
    from datetime import datetime, timedelta, timezone
    database = Database(tmp_path / 'test.db')
    database.initialize()
    now = datetime.now(timezone.utc)
    for name, count in (('Big', 6), ('Small', 2)):
        database.upsert_source(Source(name, 'official', f'https://{name}.example', 1, name, True))
        for i in range(count):
            # Every Big document is newer than every Small one.
            age = timedelta(hours=i) if name == 'Big' else timedelta(days=1, hours=i)
            database.insert_document(Document(name, f'{name}{i}', f'https://{name}.example/{i}', f'{name} body {i}', published_at=now - age))
    for doc in database.list_documents(100):
        database.update_article_body(int(doc['id']), 'body')
    sources = lambda rows: [row['source_name'] for row in rows]
    assert sources(database.list_documents_for_curation(4)) == ['Big', 'Small', 'Big', 'Small']
    for doc in database.list_documents(100):
        database.update_document_curation(int(doc['id']), 'selected', 80, 'ok')
    assert sources(database.list_documents_for_translation(4, curated_only=True)) == ['Big', 'Small', 'Big', 'Small']
    assert database.list_documents_for_translation(1, curated_only=True)[0]['title'] == 'Big0'


def test_translation_rejects_stray_han_characters():
    import pytest
    from ai_model_watch.llm.openai_compatible import validate_korean_translation
    with pytest.raises(ValueError):
        validate_korean_translation('Weekly report', '주간 報告')
    validate_korean_translation('中文 source', '중국어 원문 中文')


def test_official_scope_skips_reddit_sources(tmp_path: Path):
    from ai_model_watch import pipeline
    database = Database(tmp_path / 'test.db')
    database.initialize()
    seen = []
    with patch.object(pipeline, 'collect_rss', side_effect=lambda source, settings: seen.append(source.name) or []), \
         patch.object(pipeline, 'collect_html_index', side_effect=lambda source, settings: seen.append(source.name) or []):
        pipeline._collect(database, Settings(tmp_path / 'test.db'), 'official')
    assert seen and not any('Reddit' in name for name in seen)
