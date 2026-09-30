from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .analysis import AnalysisSummary, analyze_documents
from .clustering import ClusteringSummary, cluster_claims
from .collectors.html_index import collect_html_index
from .collectors.reddit import collect_reddit
from .collectors.rss import collect_rss
from .collectors.x_api import collect_x
from .config import Settings
from .curation import CurationSummary, curate_documents
from .database import Database
from .llm.heuristic import HeuristicAnalyzer
from .llm.openai_compatible import OpenAICompatibleProvider
from .reporting import generate_weekly_report, save_report
from .sources import OFFICIAL_SOURCES, REDDIT_SOURCES, X_SOURCES
from .translation import TranslationSummary, translate_documents
from .collectors.article import collect_article_bodies


@dataclass(frozen=True)
class PipelineSummary:
    official_inserted: int
    reddit_inserted: int
    x_inserted: int
    analysis: AnalysisSummary
    clustering: ClusteringSummary
    report_week: str
    translation: TranslationSummary
    curation: CurationSummary


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _collect(database: Database, settings: Settings) -> tuple[int, int, int]:
    official_inserted = 0
    reddit_inserted = 0
    x_inserted = 0
    sources = (*OFFICIAL_SOURCES, *REDDIT_SOURCES, *X_SOURCES) if settings.x_enabled else (*OFFICIAL_SOURCES, *REDDIT_SOURCES)
    for source in sources:
        database.upsert_source(source)
        try:
            if source.collection_method == "html_index":
                documents = collect_html_index(source, settings)
            elif source.collection_method == "reddit_json":
                documents = collect_reddit(source, settings)
            elif source.collection_method == "reddit_rss":
                documents = collect_rss(source, settings)
            elif source.collection_method == "x_api":
                documents = collect_x(source, settings)
            else:
                documents = collect_rss(source, settings)
        except Exception:
            # One source must not prevent the weekly run from processing the rest.
            continue
        if settings.since is not None:
            cutoff = datetime.fromisoformat(settings.since)
            documents = [d for d in documents if d.published_at is None or _aware(d.published_at) >= cutoff]
        inserted = sum(database.insert_document(document) for document in documents)
        if source.source_type == "reddit":
            reddit_inserted += inserted
        elif source.source_type == "x":
            x_inserted += inserted
        else:
            official_inserted += inserted
    return official_inserted, reddit_inserted, x_inserted


def run_weekly_pipeline(settings: Settings, limit: int = 100) -> PipelineSummary:
    database = Database(settings.database_path)
    database.initialize()
    official_inserted, reddit_inserted, x_inserted = _collect(database, settings)
    if settings.llm_provider == "openai-compatible":
        if not settings.llm_model:
            raise ValueError("AI_MODEL_WATCH_LLM_MODEL is required for openai-compatible provider")
        analyzer = OpenAICompatibleProvider(settings.llm_endpoint, settings.llm_model, max(180, settings.request_timeout_seconds))
    else:
        analyzer = HeuristicAnalyzer()
    translation = TranslationSummary(0, 0, 0)
    curation = CurationSummary(0, 0, 0, 0)
    if settings.translation_enabled and settings.llm_provider == "openai-compatible":
        bodies = collect_article_bodies(database, settings, settings.translation_limit)
        print(f'Bodies collected={bodies.collected} failed={bodies.failed}', flush=True)
        translator = OpenAICompatibleProvider(settings.llm_endpoint, settings.translation_model or settings.llm_model, max(180, settings.request_timeout_seconds))
        curation = curate_documents(database, translator, settings.translation_limit, settings.since)
        print(f'Quality reviewed={curation.processed} selected={curation.selected} excluded={curation.rejected} failed={curation.failed}', flush=True)
        translation = translate_documents(database, translator, settings.translation_limit, require_curated=True, since=settings.since)
    analysis = analyze_documents(database, analyzer, limit)
    clustering = cluster_claims(database, limit * 10)
    report = generate_weekly_report(database, limit=limit)
    save_report(report, settings.database_path.parent / "reports")
    return PipelineSummary(official_inserted, reddit_inserted, x_inserted, analysis, clustering, report.week, translation, curation)
