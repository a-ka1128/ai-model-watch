from __future__ import annotations

import argparse
import sys

from .analysis import analyze_documents
from .collectors.reddit import collect_reddit
from .collectors.rss import collect_rss
from .collectors.html_index import collect_html_index
from .collectors.x_api import collect_x
from .clustering import cluster_claims
from .config import Settings
from .curation import curate_documents
from .database import Database
from .llm.heuristic import HeuristicAnalyzer
from .llm.openai_compatible import OpenAICompatibleProvider
from .reporting import generate_weekly_report
from .pipeline import run_weekly_pipeline
from .sources import OFFICIAL_SOURCES, REDDIT_SOURCES, X_SOURCES
from .translation import translate_documents
from .collectors.article import collect_article_bodies


def init_database(settings: Settings) -> None:
    database = Database(settings.database_path)
    database.initialize()
    sources = (*OFFICIAL_SOURCES, *REDDIT_SOURCES, *X_SOURCES) if settings.x_enabled else (*OFFICIAL_SOURCES, *REDDIT_SOURCES)
    for source in sources:
        database.upsert_source(source)
    print(f"Initialized {settings.database_path} with {len(sources)} sources.")


def collect_official(settings: Settings) -> None:
    database = Database(settings.database_path)
    database.initialize()
    for source in OFFICIAL_SOURCES:
        database.upsert_source(source)
        try:
            collector = collect_html_index if source.collection_method == "html_index" else collect_rss
            documents = collector(source, settings)
        except Exception as exc:  # CLI should continue collecting other sources.
            print(f"[error] {source.name}: {exc}")
            continue
        inserted = sum(database.insert_document(document) for document in documents)
        print(f"{source.name}: fetched={len(documents)} inserted={inserted}")
    print(f"Total documents: {database.count_documents()}")


def collect_reddit_sources(settings: Settings) -> None:
    database = Database(settings.database_path)
    database.initialize()
    for source in REDDIT_SOURCES:
        database.upsert_source(source)
        try:
            collector = collect_rss if source.collection_method == "reddit_rss" else collect_reddit
            documents = collector(source, settings)
        except Exception as exc:
            print(f"[error] {source.name}: {exc}")
            continue
        inserted = sum(database.insert_document(document) for document in documents)
        print(f"{source.name}: fetched={len(documents)} inserted={inserted}")
    print(f"Total documents: {database.count_documents()}")


def collect_x_sources(settings: Settings) -> None:
    if not settings.x_enabled:
        print("X collection is disabled. Set AI_MODEL_WATCH_ENABLE_X=true only when an appropriate X API plan is active.")
        return
    database = Database(settings.database_path)
    database.initialize()
    for source in X_SOURCES:
        database.upsert_source(source)
        try:
            documents = collect_x(source, settings)
        except Exception as exc:
            print(f"[error] {source.name}: {exc}")
            continue
        inserted = sum(database.insert_document(document) for document in documents)
        print(f"{source.name}: fetched={len(documents)} inserted={inserted}")
    print(f"Total documents: {database.count_documents()}")


def analyze(settings: Settings, limit: int, provider_name: str | None) -> None:
    database = Database(settings.database_path)
    database.initialize()
    provider = provider_name or settings.llm_provider
    if provider == "heuristic":
        analyzer = HeuristicAnalyzer()
    elif provider == "openai-compatible":
        if not settings.llm_model:
            raise SystemExit("AI_MODEL_WATCH_LLM_MODEL is required for openai-compatible provider")
        analyzer = OpenAICompatibleProvider(settings.llm_endpoint, settings.llm_model, settings.request_timeout_seconds)
    else:
        raise SystemExit(f"Unknown provider: {provider}")
    summary = analyze_documents(database, analyzer, limit)
    print(f"Analyzed={summary.processed} relevant={summary.relevant} claims_inserted={summary.claims_inserted}")


def translate(settings: Settings, limit: int, force: bool = False) -> None:
    if settings.llm_provider != "openai-compatible":
        raise SystemExit(
            "Translation requires AI_MODEL_WATCH_LLM=openai-compatible and a local compatible LLM endpoint."
        )
    if not settings.llm_model:
        raise SystemExit("AI_MODEL_WATCH_LLM_MODEL is required for translation")
    database = Database(settings.database_path)
    database.initialize()
    if not force:
        bodies = collect_article_bodies(database, settings, limit)
        print(f'Bodies collected={bodies.collected} failed={bodies.failed}', flush=True)
    translator = OpenAICompatibleProvider(settings.llm_endpoint, settings.translation_model or settings.llm_model, max(180, settings.request_timeout_seconds))
    curation = curate_documents(database, translator, limit, settings.since)
    print(f'Quality reviewed={curation.processed} selected={curation.selected} excluded={curation.rejected} failed={curation.failed}', flush=True)
    summary = translate_documents(database, translator, limit, force, require_curated=True, since=settings.since)
    print(f"Translation processed={summary.processed} translated={summary.translated} failed={summary.failed}")


def report(settings: Settings, limit: int) -> None:
    database = Database(settings.database_path)
    database.initialize()
    generated = generate_weekly_report(database, limit=limit)
    report_path = settings.database_path.parent / "reports"
    report_path.mkdir(parents=True, exist_ok=True)
    from .reporting import save_report

    saved_path = save_report(generated, report_path)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    print(f"Saved report: {saved_path}")
    print(generated.content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-model-watch")
    parser.add_argument(
        "command",
        choices=("init-db", "collect-official", "collect-reddit", "collect-x", "analyze", "translate", "cluster-claims", "generate-report", "run-weekly"),
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--provider", choices=("heuristic", "openai-compatible"))
    parser.add_argument('--force', action='store_true', help='Re-translate stored article bodies with the current translation model')
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_environment()
    if args.command == "init-db":
        init_database(settings)
    elif args.command == "collect-official":
        collect_official(settings)
    elif args.command == "collect-reddit":
        collect_reddit_sources(settings)
    elif args.command == "collect-x":
        collect_x_sources(settings)
    elif args.command == "analyze":
        analyze(settings, args.limit, args.provider)
    elif args.command == "translate":
        translate(settings, args.limit, args.force)
    elif args.command == "cluster-claims":
        database = Database(settings.database_path)
        database.initialize()
        summary = cluster_claims(database, args.limit)
        print(f"Claims={summary.claims_processed} clusters={summary.clusters_created} links={summary.links_created}")
    elif args.command == "run-weekly":
        summary = run_weekly_pipeline(settings, args.limit)
        print(
            f"Official={summary.official_inserted} Reddit={summary.reddit_inserted} X={summary.x_inserted} "
            f"Documents={summary.analysis.processed} Claims={summary.analysis.claims_inserted} "
            f"Clusters={summary.clustering.clusters_created} Week={summary.report_week} "
            f"QualityReviewed={summary.curation.processed} QualitySelected={summary.curation.selected} "
            f"QualityExcluded={summary.curation.rejected} Translated={summary.translation.translated}"
        )
    else:
        report(settings, args.limit)
