from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .database import Database
from .models import EvidenceCluster


TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]+")
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "has", "are",
    "was", "will", "into", "about", "model", "ai", "llm", "있는", "하는", "대한",
}
NEGATIVE_MARKERS = {
    "not", "no", "never", "worse", "slower", "fails", "failed", "problem", "issue",
    "broken", "less", "불가", "실패", "문제", "느리", "나쁘", "안됨", "않",
}


def tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOPWORDS}


def similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def classify_stance(claim_text: str, representative: str, threshold: float = 0.18) -> str:
    if claim_text.strip() == representative.strip():
        return "support"
    left = tokens(claim_text)
    right = tokens(representative)
    if similarity(left, right) < threshold:
        return "neutral"
    if left & NEGATIVE_MARKERS:
        return "contradict"
    return "support"


@dataclass
class _Draft:
    representative: str
    token_set: set[str]
    claims: list[object] = field(default_factory=list)


@dataclass(frozen=True)
class ClusteringSummary:
    claims_processed: int
    clusters_created: int
    links_created: int


def cluster_claims(database: Database, limit: int = 500, threshold: float = 0.22) -> ClusteringSummary:
    claims = database.list_claims(limit)
    database.clear_clusters()
    drafts: list[_Draft] = []
    for claim in claims:
        claim_text = str(claim["claim_text"])
        claim_tokens = tokens(f"{claim['topic'] or ''} {claim_text}")
        matching = next((draft for draft in drafts if similarity(claim_tokens, draft.token_set) >= threshold), None)
        if matching is None:
            matching = _Draft(claim_text, claim_tokens)
            drafts.append(matching)
        matching.claims.append(claim)
        matching.token_set |= claim_tokens

    links_created = 0
    for draft in drafts:
        topics = [str(claim["topic"]) for claim in draft.claims if claim["topic"]]
        topic = Counter(topics).most_common(1)[0][0] if topics else "general"
        reliability = min(int(claim["reliability"]) for claim in draft.claims)
        source_names = {str(claim["source_name"]) for claim in draft.claims}
        support_count = 0
        for claim in draft.claims:
            stance = classify_stance(str(claim["claim_text"]), draft.representative)
            if stance == "support":
                support_count += 1
        confidence = None
        if len(draft.claims) >= 3 and len(source_names) >= 2:
            confidence = round(support_count / len(draft.claims), 2)
        cluster_id = database.create_cluster(EvidenceCluster(topic, draft.representative, reliability, confidence))
        for claim in draft.claims:
            stance = classify_stance(str(claim["claim_text"]), draft.representative)
            database.link_evidence(cluster_id, int(claim["id"]), stance)
            links_created += 1
    return ClusteringSummary(len(claims), len(drafts), links_created)
