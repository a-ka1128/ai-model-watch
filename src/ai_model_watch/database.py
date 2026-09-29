from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Claim, Document, EvidenceCluster, Source, WeeklyReport


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    url TEXT NOT NULL,
    reliability_default INTEGER NOT NULL CHECK (reliability_default BETWEEN 1 AND 3),
    company TEXT NOT NULL,
    is_official INTEGER NOT NULL CHECK (is_official IN (0, 1))
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    author TEXT,
    published_at TEXT,
    collected_at TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    language TEXT,
    translated_title TEXT,
    translated_content TEXT,
    translated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_published_at ON documents(published_at);
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    company TEXT,
    product TEXT,
    model TEXT,
    topic TEXT,
    task TEXT,
    effort TEXT,
    claim_text TEXT NOT NULL,
    reliability INTEGER NOT NULL CHECK (reliability BETWEEN 1 AND 3),
    created_at TEXT NOT NULL,
    UNIQUE(document_id, claim_text)
);

CREATE INDEX IF NOT EXISTS idx_claims_document_id ON claims(document_id);
CREATE INDEX IF NOT EXISTS idx_claims_topic ON claims(topic);

CREATE TABLE IF NOT EXISTS weekly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    published_at TEXT
);

CREATE TABLE IF NOT EXISTS evidence_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    summary TEXT NOT NULL,
    confidence REAL,
    reliability INTEGER NOT NULL CHECK (reliability BETWEEN 1 AND 3),
    first_seen TEXT NOT NULL,
    last_verified TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_links (
    cluster_id INTEGER NOT NULL REFERENCES evidence_clusters(id) ON DELETE CASCADE,
    claim_id INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    stance TEXT NOT NULL CHECK (stance IN ('support', 'contradict', 'neutral')),
    PRIMARY KEY (cluster_id, claim_id)
);

CREATE INDEX IF NOT EXISTS idx_evidence_links_claim_id ON evidence_links(claim_id);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(documents)").fetchall()}
            for name, sql_type in (
                ("translated_title", "TEXT"),
                ("translated_content", "TEXT"),
                ("translated_at", "TEXT"),
                ("article_content", "TEXT"),
                ("body_status", "TEXT"),
                ("body_error", "TEXT"),
                ("body_fetched_at", "TEXT"),
                ("summary_ko", "TEXT"),
                ("key_points", "TEXT"),
                ("cautions", "TEXT"),
                ("curation_status", "TEXT"),
                ("curation_score", "INTEGER"),
                ("curation_reason", "TEXT"),
                ("curated_at", "TEXT"),
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE documents ADD COLUMN {name} {sql_type}")

    def upsert_source(self, source: Source) -> int:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO sources (name, source_type, url, reliability_default, company, is_official)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    source_type=excluded.source_type,
                    url=excluded.url,
                    reliability_default=excluded.reliability_default,
                    company=excluded.company,
                    is_official=excluded.is_official
                """,
                (
                    source.name,
                    source.source_type,
                    source.url,
                    source.reliability_default,
                    source.company,
                    int(source.is_official),
                ),
            )
            row = connection.execute(
                "SELECT id FROM sources WHERE name = ?", (source.name,)
            ).fetchone()
            assert row is not None
            return int(row["id"])

    def insert_document(self, document: Document) -> bool:
        content_hash = hashlib.sha256(document.content.encode("utf-8")).hexdigest()
        collected_at = datetime.now(timezone.utc).isoformat()
        published_at = document.published_at.isoformat() if document.published_at else None
        with self.connect() as connection:
            source = connection.execute(
                "SELECT id FROM sources WHERE name = ?", (document.source_name,)
            ).fetchone()
            if source is None:
                raise ValueError(f"Unknown source: {document.source_name}")
            existing = connection.execute(
                'SELECT id, content, body_status FROM documents WHERE source_id = ? AND url = ? ORDER BY id DESC LIMIT 1',
                (source['id'], document.url),
            ).fetchone()
            if existing is not None:
                if document.content != existing['content'] and existing['body_status'] != 'complete':
                    # A feed can replace a teaser with the actual post body. Keep one document per URL.
                    connection.execute('UPDATE OR IGNORE documents SET content = ?, content_hash = ?, body_status = NULL, body_error = NULL WHERE id = ?',
                                       (document.content, content_hash, existing['id']))
                if document.author:
                    connection.execute('UPDATE documents SET author = ? WHERE id = ?', (document.author, existing['id']))
                return False
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO documents
                (source_id, title, url, author, published_at, collected_at, content, content_hash, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source["id"],
                    document.title,
                    document.url,
                    document.author,
                    published_at,
                    collected_at,
                    document.content,
                    content_hash,
                    document.language,
                ),
            )
            return cursor.rowcount == 1

    def list_documents(self, limit: int = 50) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT d.*, s.company, s.reliability_default, s.name AS source_name
                    FROM documents d
                    JOIN sources s ON s.id = d.source_id
                    ORDER BY COALESCE(d.published_at, d.collected_at) DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            )

    def get_document(self, document_id: int) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT d.*, s.company, s.reliability_default, s.name AS source_name
                FROM documents d
                JOIN sources s ON s.id = d.source_id
                WHERE d.id = ?
                """,
                (document_id,),
            ).fetchone()

    def list_documents_for_translation(self, limit: int = 100, force: bool = False, curated_only: bool = False, since: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT * FROM (
                        SELECT d.*, s.company, s.reliability_default, s.name AS source_name,
                               ROW_NUMBER() OVER (PARTITION BY d.source_id ORDER BY COALESCE(d.published_at, d.collected_at) DESC) AS source_rank
                        FROM documents d
                        JOIN sources s ON s.id = d.source_id
                        WHERE (? OR d.translated_content IS NULL OR d.translated_content = ''
                               OR d.summary_ko IS NULL OR d.summary_ko = '')
                          AND d.body_status = 'complete'
                          AND (? = 0 OR d.curation_status = 'selected')
                          AND (? IS NULL OR datetime(COALESCE(d.published_at, d.collected_at)) >= datetime(?))
                    ) ORDER BY source_rank, COALESCE(published_at, collected_at) DESC
                    LIMIT ?
                    """,
                    (int(force), int(curated_only), since, since, limit),
                ).fetchall()
            )

    def list_documents_for_curation(self, limit: int = 100, since: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute("""
                SELECT * FROM (
                    SELECT d.*, s.name AS source_name, s.source_type, s.reliability_default,
                           ROW_NUMBER() OVER (PARTITION BY d.source_id ORDER BY COALESCE(d.published_at, d.collected_at) DESC) AS source_rank
                    FROM documents d JOIN sources s ON s.id = d.source_id
                    WHERE d.body_status = 'complete'
                      AND (d.translated_content IS NULL OR d.translated_content = ''
                           OR d.summary_ko IS NULL OR d.summary_ko = '')
                      AND (d.curation_status IS NULL
                           OR (d.curation_status = 'error' AND datetime(d.curated_at) < datetime('now', '-1 day')))
                      AND (? IS NULL OR datetime(COALESCE(d.published_at, d.collected_at)) >= datetime(?))
                ) ORDER BY source_rank, COALESCE(published_at, collected_at) DESC
                LIMIT ?
            """, (since, since, limit)).fetchall())

    def update_document_curation(self, document_id: int, status: str, score: int | None, reason: str) -> None:
        if status not in {'selected', 'rejected', 'error'}:
            raise ValueError(f'Invalid curation status: {status}')
        with self.connect() as connection:
            connection.execute("""
                UPDATE documents SET curation_status = ?, curation_score = ?, curation_reason = ?, curated_at = ?
                WHERE id = ?
            """, (status, score, reason, datetime.now(timezone.utc).isoformat(), document_id))

    def list_body_candidates(self, limit: int = 100, since: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute("""
                SELECT * FROM (
                    SELECT d.*, s.name AS source_name, s.source_type,
                           ROW_NUMBER() OVER (
                               PARTITION BY d.source_id
                               ORDER BY COALESCE(d.published_at, d.collected_at) DESC
                           ) AS source_rank
                    FROM documents d JOIN sources s ON s.id = d.source_id
                    WHERE (d.body_status IS NULL OR
                          (d.body_status = 'failed' AND datetime(d.body_fetched_at) < datetime('now', '-1 day')))
                    AND (? IS NULL OR datetime(COALESCE(d.published_at, d.collected_at)) >= datetime(?))
                ) ORDER BY source_rank, COALESCE(published_at, collected_at) DESC LIMIT ?
            """, (since, since, limit)).fetchall())

    def update_article_body(self, document_id: int, content: str | None, error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute("""
                UPDATE documents SET article_content = ?, body_status = ?, body_error = ?,
                    body_fetched_at = ?, translated_title = NULL, translated_content = NULL,
                    translated_at = NULL, summary_ko = NULL, key_points = NULL, cautions = NULL
                WHERE id = ?
            """, (content, 'complete' if content else 'failed', error,
                  datetime.now(timezone.utc).isoformat(), document_id))

    def update_article_brief(self, document_id: int, summary: str, points: tuple[str, ...], cautions: tuple[str, ...]) -> None:
        with self.connect() as connection:
            connection.execute("UPDATE documents SET summary_ko = ?, key_points = ?, cautions = ? WHERE id = ?",
                (summary, json.dumps(points, ensure_ascii=False), json.dumps(cautions, ensure_ascii=False), document_id))

    def list_articles(self, limit: int = 24, offset: int = 0, query: str = '', source: str = '', company: str = '') -> tuple[list[sqlite3.Row], int]:
        clauses = ["d.body_status = 'complete'", "d.curation_status = 'selected'", "d.translated_content IS NOT NULL", "COALESCE(d.summary_ko, '') != ''"]
        params: list[object] = []
        if query:
            clauses.append("(d.translated_title LIKE ? OR d.summary_ko LIKE ? OR d.translated_content LIKE ?)")
            params.extend([f'%{query}%'] * 3)
        if source:
            clauses.append("s.source_type = ?")
            params.append(source)
        if company == 'other':
            clauses.append("s.company NOT IN (?, ?, ?)")
            params.extend(['OpenAI', 'Anthropic', 'Google'])
        elif company:
            clauses.append("s.company = ?")
            params.append(company)
        where = ' AND '.join(clauses)
        with self.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM documents d JOIN sources s ON s.id = d.source_id WHERE {where}", params).fetchone()[0]
            rows = connection.execute(f"""
                SELECT d.id, d.translated_title, d.summary_ko, d.key_points, d.cautions,
                       d.published_at, d.collected_at, s.name AS source_name, s.source_type,
                       s.company, s.reliability_default
                FROM documents d JOIN sources s ON s.id = d.source_id WHERE {where}
                ORDER BY COALESCE(d.published_at, d.collected_at) DESC LIMIT ? OFFSET ?
            """, [*params, limit, offset]).fetchall()
            return list(rows), int(total)

    def article_stats(self) -> dict[str, int]:
        with self.connect() as connection:
            row = connection.execute("""SELECT COUNT(*) AS collected,
                SUM(CASE WHEN body_status = 'complete' AND curation_status = 'selected' AND COALESCE(summary_ko, '') != '' AND translated_content IS NOT NULL THEN 1 ELSE 0 END) AS ready,
                SUM(CASE WHEN body_status = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN body_status IS NULL THEN 1 ELSE 0 END) AS awaiting_body,
                SUM(CASE WHEN body_status = 'complete' AND curation_status IS NULL
                    AND (translated_content IS NULL OR translated_content = '' OR COALESCE(summary_ko, '') = '') THEN 1 ELSE 0 END) AS awaiting_curation,
                SUM(CASE WHEN curation_status = 'selected' AND (translated_content IS NULL OR translated_content = '' OR COALESCE(summary_ko, '') = '') THEN 1 ELSE 0 END) AS selected_waiting,
                SUM(CASE WHEN curation_status = 'rejected' THEN 1 ELSE 0 END) AS excluded,
                SUM(CASE WHEN curation_status = 'error' THEN 1 ELSE 0 END) AS curation_failed
                FROM documents""").fetchone()
            return {key: int(row[key] or 0) for key in row.keys()}

    def update_document_translation(self, document_id: int, title_ko: str, content_ko: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE documents
                SET translated_title = ?, translated_content = ?, translated_at = ?
                WHERE id = ?
                """,
                (title_ko, content_ko, datetime.now(timezone.utc).isoformat(), document_id),
            )

    def insert_claim(self, claim: Claim) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO claims
                (document_id, company, product, model, topic, task, effort,
                 claim_text, reliability, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.document_id,
                    claim.company,
                    claim.product,
                    claim.model,
                    claim.topic,
                    claim.task,
                    claim.effort,
                    claim.claim_text,
                    claim.reliability,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return cursor.rowcount == 1

    def list_claims(self, limit: int = 100) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT c.*, d.title, d.url, s.name AS source_name, s.company AS source_company
                    FROM claims c
                    JOIN documents d ON d.id = c.document_id
                    JOIN sources s ON s.id = d.source_id
                    ORDER BY c.created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            )

    def create_cluster(self, cluster: EvidenceCluster) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO evidence_clusters
                (topic, summary, confidence, reliability, first_seen, last_verified)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cluster.topic,
                    cluster.summary,
                    cluster.confidence,
                    cluster.reliability,
                    now,
                    now,
                ),
            )
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    def clear_clusters(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM evidence_links")
            connection.execute("DELETE FROM evidence_clusters")

    def link_evidence(self, cluster_id: int, claim_id: int, stance: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_links (cluster_id, claim_id, stance)
                VALUES (?, ?, ?)
                ON CONFLICT(cluster_id, claim_id) DO UPDATE SET stance=excluded.stance
                """,
                (cluster_id, claim_id, stance),
            )

    def list_clusters(self, limit: int = 50) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT
                        ec.*,
                        COUNT(el.claim_id) AS evidence_count,
                        SUM(CASE WHEN el.stance = 'support' THEN 1 ELSE 0 END) AS supporting_count,
                        SUM(CASE WHEN el.stance = 'contradict' THEN 1 ELSE 0 END) AS contradicting_count,
                        SUM(CASE WHEN el.stance = 'neutral' THEN 1 ELSE 0 END) AS neutral_count
                    FROM evidence_clusters ec
                    LEFT JOIN evidence_links el ON el.cluster_id = ec.id
                    GROUP BY ec.id
                    ORDER BY ec.last_verified DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            )

    def upsert_weekly_report(self, report: WeeklyReport) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO weekly_reports
                (week, title, summary, content, generated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(week) DO UPDATE SET
                    title=excluded.title,
                    summary=excluded.summary,
                    content=excluded.content,
                    generated_at=excluded.generated_at
                """,
                (
                    report.week,
                    report.title,
                    report.summary,
                    report.content,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def latest_report(self) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM weekly_reports ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()

    def count_documents(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
            assert row is not None
            return int(row["count"])
