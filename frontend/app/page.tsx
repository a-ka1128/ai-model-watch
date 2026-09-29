"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

type Article = { id: number; translated_title: string; summary_ko: string; key_points: string[]; source_name: string; source_type: string; company: string; published_at: string | null; collected_at: string; };
type Feed = { items: Article[]; total: number; stats: { collected: number; ready: number; failed: number; awaiting_body: number; awaiting_curation: number; selected_waiting: number; excluded: number; curation_failed: number } };
const pageSize = 12;

export default function Dashboard() {
  const [feed, setFeed] = useState<Feed | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [company, setCompany] = useState("");
  const [page, setPage] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const params = new URLSearchParams({ limit: String(pageSize), offset: String(page * pageSize), q: search, source, company });
    fetch("/api/articles?" + params, { cache: "no-store", signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error("응답 오류 (" + response.status + ")"); return response.json(); })
      .then((nextFeed: Feed) => { setFeed(nextFeed); setError(""); })
      .catch(reason => { if (reason.name !== "AbortError") setError(reason.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [search, source, company, page, refresh]);
  useEffect(() => {
    const timer = window.setInterval(() => setRefresh(value => value + 1), 30000);
    return () => window.clearInterval(timer);
  }, []);
  return <main className="shell">
    <header className="topbar"><Link href="/" className="brand"><span className="brand-mark">≋</span>AI MODEL WATCH</Link><div className="status"><span className="status-dot" /> 한글 정보 모음</div></header>
    <section className="intro"><div><p className="eyebrow">AI INTELLIGENCE / 한국어로 읽기</p><h1>AI 소식, 한곳에서 읽다.</h1><p className="lede">공식 발표와 커뮤니티 글을 수집해 핵심 내용과 한글 본문으로 정리합니다. 글을 누르면 여기서 바로 읽을 수 있습니다.</p></div><div className="run-note"><span>읽는 순서</span><strong>핵심 요약 → 주요 내용 → 한글 본문</strong></div></section>
    {error && <div role="alert" className="error-banner">자료를 불러오지 못했습니다. {error} <button onClick={() => setRefresh(value => value + 1)}>다시 시도</button></div>}
    <section className="metrics" aria-label="수집 현황">
      <div className="metric"><span>한글 정리 완료</span><strong>{feed?.stats.ready ?? "—"}</strong><small>본문 번역과 요약이 끝난 글</small></div>
      <div className="metric"><span>수집된 자료</span><strong>{feed?.stats.collected ?? "—"}</strong><small>정리 대기 중인 글 포함</small></div>
      <div className="metric"><span>본문 수집 실패</span><strong>{feed?.stats.failed ?? "—"}</strong><small>접근 제한 또는 텍스트 본문 없음</small></div>
    </section>
    <p className="feed-note" aria-live="polite">본문 수집 대기 {feed?.stats.awaiting_body ?? "—"}건 · 정보 선별 대기 {feed?.stats.awaiting_curation ?? "—"}건 · 선별 통과 후 번역 대기 {feed?.stats.selected_waiting ?? "—"}건 · 선별 제외 {feed?.stats.excluded ?? "—"}건{(feed?.stats.curation_failed ?? 0) > 0 ? ` · 선별 오류 ${feed?.stats.curation_failed}건` : ""}</p>
    <section className="panel article-feed">
      <div className="panel-heading"><div><p className="eyebrow">정리된 정보</p><h2>한글로 읽는 최신 글</h2></div><span className="count">{feed?.total ?? 0}개</span></div>
      <div className="feed-tools">
        <div className="feed-filters">
          <div className="filter-set"><span className="filter-label">출처</span><div className="source-filters" aria-label="출처 필터">{[["", "전체"], ["official", "공식 발표"], ["reddit", "Reddit"], ["x", "X"]].map(([value, label]) => <button key={value} className={source === value ? "selected" : ""} aria-pressed={source === value} onClick={() => { setSource(value); setPage(0); }}>{label}</button>)}</div></div>
          <div className="filter-set"><span className="filter-label">AI 기업</span><div className="source-filters" aria-label="AI 기업 필터">{[["", "전체"], ["OpenAI", "OpenAI"], ["Anthropic", "Anthropic"], ["Google", "Google (Gemini)"], ["other", "기타"]].map(([value, label]) => <button key={value} className={company === value ? "selected" : ""} aria-pressed={company === value} onClick={() => { setCompany(value); setPage(0); }}>{label}</button>)}</div></div>
        </div>
        <form className="article-search" onSubmit={event => { event.preventDefault(); setSearch(query.trim()); setPage(0); }}><input aria-label="글 검색" placeholder="모델 이름, 주제 검색" value={query} onChange={event => setQuery(event.target.value)} /><button type="submit">검색</button></form>
      </div>
      {loading && <p role="status" className="muted">자료를 불러오는 중입니다.</p>}
      {!loading && feed?.items.length === 0 && <div className="empty"><span>○</span><p>{search || source || company ? "조건에 맞는 한글 글이 없습니다." : "한글로 정리된 글을 준비 중입니다. 컨트롤 패널의 ‘수집 실행’으로 수집·번역을 시작할 수 있습니다."}</p></div>}
      <div className="article-cards">{feed?.items.map(article => <Link href={"/articles/" + article.id} className="article-card" key={article.id}>
        <div className="article-meta"><span className="tag">{article.company === "Google" ? "Google (Gemini)" : article.company}</span><span>{article.source_type === "official" ? "공식 발표" : "커뮤니티 경험"}</span></div>
        <h3>{article.translated_title}</h3><p className="card-summary">{article.summary_ko}</p>
        <ul className="card-points">{article.key_points.slice(0, 2).map((point, index) => <li key={index}>{point}</li>)}</ul>
        <div className="card-footer"><span>{article.source_name} · {new Date(article.published_at || article.collected_at).toLocaleDateString("ko-KR")}</span><strong>글 읽기 →</strong></div>
      </Link>)}</div>
      {(feed?.total ?? 0) > pageSize && <nav className="pagination" aria-label="글 목록 페이지"><button disabled={page === 0 || loading} onClick={() => setPage(value => value - 1)}>이전</button><span>{page + 1} / {Math.ceil((feed?.total ?? 0) / pageSize)}</span><button disabled={(page + 1) * pageSize >= (feed?.total ?? 0) || loading} onClick={() => setPage(value => value + 1)}>다음</button></nav>}
      <p className="feed-note">원문의 주장과 개인 경험을 바탕으로 자동 정리한 내용입니다. X 수집은 현재 비활성화되어 있습니다.</p>
    </section>
    <footer>AI Model Watch · 본문 수집 · 한글 번역 · 기업 및 출처별 정리</footer>
  </main>;
}
