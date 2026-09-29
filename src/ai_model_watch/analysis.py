from __future__ import annotations

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
        result = analyzer.classify(document["title"], content)
        if not result.relevant:
            continue
        relevant += 1
        for raw_claim in analyzer.extract(document["title"], content):
            reliability = raw_claim.get("reliability", document["reliability_default"])
            if not isinstance(reliability, int) or reliability not in (1, 2, 3):
                reliability = int(document["reliability_default"])
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
