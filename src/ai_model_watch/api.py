from __future__ import annotations

from .config import Settings
from .database import Database


def create_app():
    """Create the optional read-only API.

    FastAPI remains an optional dependency so collection and report generation
    work in a minimal local environment.
    """
    from fastapi import FastAPI, HTTPException, Query
    import json
    from fastapi.middleware.cors import CORSMiddleware

    settings = Settings.from_environment()
    database = Database(settings.database_path)
    database.initialize()
    app = FastAPI(title="AI Model Watch API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/documents")
    def documents(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, object]]:
        return [dict(row) for row in database.list_documents(limit)]

    @app.get("/claims")
    def claims(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict[str, object]]:
        return [dict(row) for row in database.list_claims(limit)]

    @app.get('/articles')
    def articles(limit: int = Query(default=24, ge=1, le=100), offset: int = Query(default=0, ge=0),
                 q: str = Query(default='', max_length=200), source: str = '', company: str = ''):
        rows, total = database.list_articles(limit, offset, q, source, company)
        items = []
        for row in rows:
            item = dict(row)
            item['key_points'] = json.loads(item['key_points'] or '[]')
            item['cautions'] = json.loads(item['cautions'] or '[]')
            items.append(item)
        return {'items': items, 'total': total, 'stats': database.article_stats()}

    @app.get('/articles/{document_id}')
    def article(document_id: int):
        row = database.get_document(document_id)
        if row is None or row['body_status'] != 'complete' or row['curation_status'] != 'selected' or not row['summary_ko'] or not row['translated_content']:
            raise HTTPException(status_code=404, detail='Korean article is not ready')
        item = dict(row)
        if isinstance(item.get('author'), str):
            item['author'] = item['author'].split('https://', 1)[0]
        item['key_points'] = json.loads(item['key_points'] or '[]')
        item['cautions'] = json.loads(item['cautions'] or '[]')
        return item

    @app.get("/clusters")
    def clusters(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, object]]:
        return [dict(row) for row in database.list_clusters(limit)]

    @app.get("/reports/latest")
    def latest_report() -> dict[str, object]:
        row = database.latest_report()
        if row is None:
            return {"status": "not_found", "content": "Insufficient Evidence"}
        return dict(row)

    return app
