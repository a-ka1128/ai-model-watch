"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { GlossaryTerm, termsIn } from "../../glossary";
import { AnnotatedText, readingParagraphs, splitArticleTitle } from "../../reading";

type Article = { id: number; title: string; translated_title: string; translated_content: string; article_content: string; summary_ko: string; key_points: string[]; cautions: string[]; source_name: string; company: string; reliability_default: number; url: string; author: string | null; published_at: string | null; collected_at: string; };

export default function ArticlePage({ params }: { params: { id: string } }) {
  const [article, setArticle] = useState<Article | null>(null);
  const [error, setError] = useState("");
  const [activeTerm, setActiveTerm] = useState<GlossaryTerm | null>(null);
  const [largeText, setLargeText] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (activeTerm && dialogRef.current && !dialogRef.current.open) dialogRef.current.showModal();
  }, [activeTerm]);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/articles/${encodeURIComponent(params.id)}`, { cache: "no-store", signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error(response.status === 404 ? "아직 한글로 정리되지 않았거나 존재하지 않는 글입니다." : "글을 불러오지 못했습니다."); return response.json(); })
      .then(setArticle).catch(reason => { if (reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [params.id]);
  const terms = article ? termsIn([article.translated_title, article.summary_ko, ...article.key_points, ...article.cautions, article.translated_content].join("\n")) : [];
  const heading = splitArticleTitle(article?.translated_title || "");
  const explained = (text: string) => <AnnotatedText text={text} terms={terms} onTerm={setActiveTerm} />;
  return <main className="shell reader-shell">
    <header className="topbar"><Link href="/" className="brand"><span className="brand-mark">≋</span>AI MODEL WATCH</Link><Link href="/" className="back-link">← 글 목록</Link></header>
    {error ? <div className="error-banner reader-loading" role="alert">{error}</div> : !article ? <p className="reader-loading" role="status">한글 글을 불러오는 중입니다.</p> : <article className={`reader${largeText ? " reader-large" : ""}`}>
      <header className="reader-header"><p className="eyebrow">{article.company === "Google" ? "Google (Gemini)" : article.company} / {article.reliability_default === 1 ? "공식 발표" : "커뮤니티 경험"}</p><h1>{explained(heading.title)}</h1>{heading.subtitle && <p className="reader-subtitle">{explained(heading.subtitle)}</p>}<p className="reader-byline">{article.source_name} · {new Date(article.published_at || article.collected_at).toLocaleDateString("ko-KR")}{article.author ? ` · ${article.author}` : ""}</p></header>
      <div className="reader-tools"><nav aria-label="글 목차"><a href="#brief">요약</a><a href="#points">주요 내용</a><a href="#body">본문</a>{terms.length > 0 && <a href="#glossary">용어 설명</a>}</nav><button className="font-control" aria-pressed={largeText} onClick={() => setLargeText(value => !value)}>{largeText ? "기본 글자" : "글자 크게"}</button></div>
      <section id="brief" className="reader-summary"><h2>핵심 요약</h2>{readingParagraphs(article.summary_ko).map((paragraph, index) => <p key={index}>{explained(paragraph)}</p>)}</section>
      {terms.length > 0 && <details id="glossary" className="glossary-details"><summary>이 글의 용어 {terms.length}개 <span>밑줄 친 단어를 눌러도 뜻을 볼 수 있어요</span></summary><dl>{terms.map((term, index) => <div className="glossary-entry" key={term.id}><dt><span className="note-number">{index + 1}</span>{term.name}</dt><dd>{term.explanation}{term.source && <a href={term.source} target="_blank" rel="noreferrer" className="definition-source">설명 출처 ↗</a>}</dd></div>)}</dl></details>}
      <section id="points" className="reader-section"><h2>주요 내용</h2><ul className="reader-points" role="list">{article.key_points.map((point, index) => <li key={index}>{explained(point)}</li>)}</ul></section>
      {article.cautions.length > 0 && <section className="reader-cautions"><h2>주의할 점과 한계</h2><ul>{article.cautions.map((point, index) => <li key={index}>{explained(point)}</li>)}</ul></section>}
      <section id="body" className="reader-section"><div className="panel-heading"><h2>한글 본문</h2><a className="body-jump" href="#source-info">출처 확인 ↓</a></div><div className="article-body">{readingParagraphs(article.translated_content).map((paragraph, index) => <p key={index}>{explained(paragraph)}</p>)}</div></section>
      <p className="feed-note">자동 번역·요약한 글입니다. 공식 발표는 발표자의 주장, 커뮤니티 글은 작성자의 경험을 전달합니다.</p>
      <details className="original-details"><summary>수집한 원문 보기</summary><h3>{article.title}</h3><div className="article-body">{article.article_content}</div></details>
      <aside id="source-info" className="source-attribution"><h2>출처</h2><p>{article.source_name}</p><a href={article.url} target="_blank" rel="noreferrer">원문 사이트 확인 ↗</a></aside>
      <Link href="/" className="back-link">← 다른 한글 글 읽기</Link>
      <dialog ref={dialogRef} className="term-dialog" aria-labelledby="term-dialog-title" onClose={() => setActiveTerm(null)} onClick={event => { if (event.target === event.currentTarget) dialogRef.current?.close(); }}><div className="term-dialog-heading"><p className="eyebrow">쉽게 이해하기</p><form method="dialog"><button aria-label="용어 설명 닫기">닫기 ×</button></form></div><h2 id="term-dialog-title">{activeTerm?.name}</h2><p className="term-explanation">{activeTerm?.explanation}</p>{activeTerm?.source && <a href={activeTerm.source} target="_blank" rel="noreferrer" className="definition-source">설명 출처 확인 ↗</a>}<p className="term-note">읽기를 돕는 용어 설명입니다. 글쓴이의 본문과는 별도로 제공됩니다.</p></dialog>
    </article>}
  </main>;
}
