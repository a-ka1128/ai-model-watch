from __future__ import annotations

from .models import Source


# Phase 1 deliberately uses stable public feeds. Provider APIs can be added
# later without changing the Source/Document persistence contract.
OFFICIAL_SOURCES: tuple[Source, ...] = (
    Source(
        name="OpenAI News",
        source_type="official",
        url="https://openai.com/news/rss.xml",
        reliability_default=1,
        company="OpenAI",
        is_official=True,
    ),
    Source(
        name="Anthropic News",
        source_type="official",
        url="https://www.anthropic.com/news",
        reliability_default=1,
        company="Anthropic",
        is_official=True,
        collection_method="html_index",
    ),
    Source(
        name="Google AI Blog",
        source_type="official",
        url="https://blog.google/technology/ai/rss/",
        reliability_default=1,
        company="Google",
        is_official=True,
    ),
    # Gemini model launches are posted here and on DeepMind, not under the general AI feed.
    Source(
        name="Google Gemini Blog",
        source_type="official",
        url="https://blog.google/products/gemini/rss/",
        reliability_default=1,
        company="Google",
        is_official=True,
    ),
    Source(
        name="Google DeepMind Blog",
        source_type="official",
        url="https://deepmind.google/blog/rss.xml",
        reliability_default=1,
        company="Google",
        is_official=True,
    ),
)


REDDIT_SOURCES: tuple[Source, ...] = (
    Source(
        name="Reddit r/ChatGPT",
        source_type="reddit",
        url="https://www.reddit.com/r/ChatGPT/new/.rss",
        reliability_default=3,
        company="OpenAI",
        is_official=False,
        collection_method="reddit_rss",
    ),
    Source(
        name="Reddit r/ClaudeAI",
        source_type="reddit",
        url="https://www.reddit.com/r/ClaudeAI/new/.rss",
        reliability_default=3,
        company="Anthropic",
        is_official=False,
        collection_method="reddit_rss",
    ),
    Source(
        name="Reddit r/LocalLLaMA",
        source_type="reddit",
        url="https://www.reddit.com/r/LocalLLaMA/new/.rss",
        reliability_default=3,
        company="Local LLM",
        is_official=False,
        collection_method="reddit_rss",
    ),
)


X_SOURCES: tuple[Source, ...] = (
    Source(
        name="X AI Model Search",
        source_type="x",
        url="https://api.x.com/2/tweets/search/recent",
        reliability_default=2,
        company="AI ecosystem",
        is_official=False,
        collection_method="x_api",
    ),
)
