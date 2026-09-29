from __future__ import annotations

from dataclasses import dataclass
import logging

from .database import Database
from .llm.contracts import ArticleBrief, Translator


@dataclass(frozen=True)
class TranslationSummary:
    processed: int
    translated: int
    failed: int


def translate_documents(database: Database, translator: Translator, limit: int = 100, force: bool = False, require_curated: bool = False) -> TranslationSummary:
    processed = 0
    translated = 0
    failed = 0
    for document in database.list_documents_for_translation(limit, force, require_curated):
        processed += 1
        try:
            content = str(document['article_content'] or document['content'])
            if document['translated_content'] and not force:
                title_ko = str(document['translated_title'])
                content_ko = str(document['translated_content'])
            else:
                result = translator.translate(str(document["title"]), content)
                title_ko, content_ko = result.title_ko, result.content_ko
            if len(content) < 400:
                brief = ArticleBrief(content_ko, (title_ko,), ())
            else:
                brief = translator.summarize_article(str(document['title']), f"출처: {document['source_name']}\n\n{content}")
            database.update_document_translation(int(document["id"]), title_ko, content_ko)
            database.update_article_brief(int(document['id']), brief.summary_ko, brief.key_points, brief.cautions)
            translated += 1
            print(f"[article] id={document['id']} ready", flush=True)
        except Exception as exc:
            logging.getLogger(__name__).warning('Translation failed for document %s: %s', document['id'], exc)
            failed += 1
    return TranslationSummary(processed, translated, failed)
