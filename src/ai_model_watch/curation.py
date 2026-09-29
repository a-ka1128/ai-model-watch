from __future__ import annotations

from dataclasses import dataclass
import logging

from .database import Database
from .llm.contracts import ArticleCurator


MINIMUM_QUALITY_SCORE = 65


@dataclass(frozen=True)
class CurationSummary:
    processed: int
    selected: int
    rejected: int
    failed: int


def curate_documents(database: Database, curator: ArticleCurator, limit: int = 100, since: str | None = None) -> CurationSummary:
    processed = selected = rejected = failed = 0
    for document in database.list_documents_for_curation(limit, since):
        processed += 1
        document_id = int(document['id'])
        try:
            assessment = curator.assess_quality(
                str(document['title']),
                str(document['article_content'] or document['content']),
                str(document['source_name']),
                int(document['reliability_default']),
            )
            status = 'selected' if assessment.score >= MINIMUM_QUALITY_SCORE else 'rejected'
            database.update_document_curation(document_id, status, assessment.score, assessment.reason)
            if status == 'selected':
                selected += 1
            else:
                rejected += 1
            logging.getLogger(__name__).info(
                'Article %s %s by quality filter (score=%d): %s',
                document_id, status, assessment.score, assessment.reason,
            )
        except Exception as exc:
            database.update_document_curation(document_id, 'error', None, str(exc)[:500])
            failed += 1
            logging.getLogger(__name__).warning('Quality review failed for document %s: %s', document_id, exc)
    return CurationSummary(processed, selected, rejected, failed)
