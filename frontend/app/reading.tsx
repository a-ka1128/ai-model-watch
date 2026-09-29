import { Fragment } from "react";
import { annotate, GlossaryTerm } from "./glossary";

export function AnnotatedText({ text, terms, onTerm }: { text: string; terms: GlossaryTerm[]; onTerm: (term: GlossaryTerm) => void }) {
  const seen = new Set<string>();
  return <>{annotate(text).map((part, index) => {
    if (!part.term || seen.has(part.term.id)) return <Fragment key={index}>{part.text}</Fragment>;
    seen.add(part.term.id);
    const term = part.term;
    const number = terms.findIndex(item => item.id === term.id) + 1;
    return <button className="term-link" key={index} onClick={() => onTerm(term)} aria-label={`${part.text}: 용어 설명 ${number} 보기`} aria-haspopup="dialog" title={term.explanation}>{part.text}<sup>{number}</sup></button>;
  })}</>;
}

export function splitArticleTitle(title: string): { title: string; subtitle: string } {
  if (title.length < 85) return { title, subtitle: "" };
  const firstSentence = title.match(/^(.{18,100}?[.!?])\s+(.+)$/);
  return firstSentence ? { title: firstSentence[1], subtitle: firstSentence[2] } : { title, subtitle: "" };
}

export function readingParagraphs(text: string): string[] {
  return text.split(/\n+/).filter(part => part.trim()).flatMap(paragraph => {
    if (paragraph.length < 360) return [paragraph];
    const sentences = paragraph.split(/(?<=[.!?])\s+/);
    const paragraphs: string[] = [];
    let current = "";
    for (const sentence of sentences) {
      if (current.length > 220) { paragraphs.push(current); current = ""; }
      current += (current ? " " : "") + sentence;
    }
    if (current) paragraphs.push(current);
    return paragraphs;
  });
}
