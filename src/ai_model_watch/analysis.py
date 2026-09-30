from __future__ import annotations

import logging
from dataclasses import dataclass

from .database import Database
from .llm.contracts import StructuredAnalyzer
from .models import Claim


@dataclass(frozen=True)
class AnalysisSummary:
    processed: int
    relevant: int
    claims_inserted: int


def analyze_documents(database: Database, analyzer: StructuredAnalyzer, limit: int = 50) -> AnalysisSummary:
    processed = 0
    relevant = 0
    claims_inserted = 0
    for document in database.list_documents(limit):
        processed += 1
        content = document['article_content'] or document['content']
        try:
            result = analyzer.classify(document["title"], content)
            if not result.relevant:
                continue
            extracted = analyzer.extract(document["title"], content, document["source_type"])
        except Exception as exc:
            # One malformed model response must not abort the whole run.
            logging.getLogger(__name__).warning("Analysis failed for document %s: %s", document["id"], exc)
            continue
        relevant += 1
        for raw_claim in extracted:
            # The source sets the ceiling: a model may lower trust (higher number) but never raise it.
            default_reliability = int(document["reliability_default"])
            reliability = raw_claim.get("reliability")
            if isinstance(reliability, bool) or not isinstance(reliability, int) or reliability not in (1, 2, 3):
                reliability = default_reliability
            reliability = max(reliability, default_reliability)
            claim_text = str(raw_claim.get("claim_text", "")).strip()
            if not claim_text:
                continue
            claims_inserted += int(database.insert_claim(Claim(
                document_id=int(document["id"]),
                company=raw_claim.get("company") if isinstance(raw_claim.get("company"), str) else document["company"],
                product=raw_claim.get("product") if isinstance(raw_claim.get("product"), str) else None,
                model=raw_claim.get("model") if isinstance(raw_claim.get("model"), str) else None,
                topic=raw_claim.get("topic") if isinstance(raw_claim.get("topic"), str) else None,
                task=raw_claim.get("task") if isinstance(raw_claim.get("task"), str) else None,
                effort=raw_claim.get("effort") if isinstance(raw_claim.get("effort"), str) else None,
                claim_text=claim_text,
                reliability=reliability,
            )))
    return AnalysisSummary(processed, relevant, claims_inserted)
