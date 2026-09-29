from __future__ import annotations

from .contracts import RelevanceResult


class KeywordRelevanceFilter:
    """Deterministic fallback used before a local LLM is configured."""

    KEYWORDS = {
        "model", "ai", "llm", "reasoning", "thinking", "coding", "agent",
        "gemini", "claude", "gpt", "openai", "anthropic", "deepseek", "qwen",
    }

    def classify(self, title: str, content: str) -> RelevanceResult:
        text = f"{title} {content}".lower()
        hits = sorted(keyword for keyword in self.KEYWORDS if keyword in text)
        return RelevanceResult(
            relevant=bool(hits),
            topics=tuple(hits[:5]),
            summary_ko="키워드 기반 사전 분류 결과입니다.",
        )
