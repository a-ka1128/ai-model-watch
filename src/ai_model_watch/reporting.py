from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .database import Database
from .models import WeeklyReport


def current_week() -> str:
    return datetime.now(timezone.utc).strftime("%G-W%V")


def generate_weekly_report(database: Database, week: str | None = None, limit: int = 20) -> WeeklyReport:
    report_week = week or current_week()
    documents = database.list_documents(limit)
    claims = database.list_claims(limit * 3)
    clusters = database.list_clusters(limit)
    lines = [
        "# AI MODEL WATCH",
        f"## Week {report_week}",
        "",
        "## 이번 주 수집 현황",
        f"- 수집 문서: {len(documents)}개",
        f"- 구조화된 Claim: {len(claims)}개",
        f"- Evidence Cluster: {len(clusters)}개",
        "",
        "## 주요 자료",
    ]
    if not documents:
        lines.append("- 아직 수집된 문서가 없습니다. `collect-official`, `collect-reddit`, 또는 `collect-x`를 먼저 실행하세요.")
    else:
        for document in documents:
            display_title = document["translated_title"] or document["title"]
            lines.extend([
                f"- **{display_title}** ({document['source_name']})",
                f"  - 출처: [{document['url']}]({document['url']})",
            ])
            if document["translated_content"]:
                translated = str(document["translated_content"]).strip()
                if len(translated) > 800:
                    translated = translated[:797].rstrip() + "..."
                lines.append(f"  - 한글 번역: {translated}")
    lines.extend(["", "## Evidence-backed Claims"])
    if not claims:
        lines.append("근거가 연결된 Claim이 없어 추천을 생성하지 않았습니다: `Insufficient Evidence`.")
    else:
        for claim in claims:
            lines.extend([
                f"- **{claim['claim_text']}**",
                f"  - Reliability: `{int(claim['reliability'])}` · Source: [{claim['source_name']}]({claim['url']})",
            ])
    lines.extend(["", "## Evidence Clusters"])
    if not clusters:
        lines.append("클러스터가 아직 생성되지 않았습니다. `cluster-claims`를 먼저 실행하세요.")
    else:
        for cluster in clusters:
            confidence = cluster["confidence"]
            confidence_text = f"{float(confidence):.0%}" if confidence is not None else "Insufficient Evidence"
            lines.append(
                f"- **{cluster['topic']}** — {cluster['summary']} "
                f"(support {cluster['supporting_count']}, contradict {cluster['contradicting_count']}, "
                f"neutral {cluster['neutral_count']}, confidence {confidence_text})"
            )
    content = "\n".join(lines) + "\n"
    summary = f"{len(documents)}개 문서와 {len(claims)}개 Claim을 근거 링크와 함께 정리했습니다."
    report = WeeklyReport(report_week, f"AI Model Watch — {report_week}", summary, content)
    database.upsert_weekly_report(report)
    return report


def save_report(report: WeeklyReport, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report.week}.md"
    path.write_text(report.content, encoding="utf-8")
    return path
