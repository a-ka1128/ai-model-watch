from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from ..config import Settings
from ..models import Document, Source


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _post_url(post_id: str, username: str | None) -> str:
    if username:
        return f"https://x.com/{username}/status/{post_id}"
    return f"https://x.com/i/web/status/{post_id}"


def parse_x_search_response(payload: str | bytes, source: Source) -> list[Document]:
    data: dict[str, Any] = json.loads(payload)
    users = {
        str(user.get("id")): user
        for user in data.get("includes", {}).get("users", [])
        if user.get("id")
    }
    documents: list[Document] = []
    seen_ids: set[str] = set()
    for post in data.get("data", []):
        post_id = str(post.get("id") or "").strip()
        text = str(post.get("text") or "").strip()
        if not post_id or not text or post_id in seen_ids:
            continue
        seen_ids.add(post_id)
        user = users.get(str(post.get("author_id") or ""), {})
        username = str(user.get("username") or "").strip() or None
        compact_title = " ".join(text.split())
        if len(compact_title) > 120:
            compact_title = compact_title[:117].rstrip() + "..."
        title = f"X / @{username}: {compact_title}" if username else f"X: {compact_title}"
        documents.append(
            Document(
                source_name=source.name,
                title=title,
                url=_post_url(post_id, username),
                content=text,
                author=username or str(user.get("name") or "").strip() or None,
                published_at=_parse_datetime(post.get("created_at")),
                language=post.get("lang") or None,
            )
        )
    return documents


def collect_x(source: Source, settings: Settings) -> list[Document]:
    token = settings.x_bearer_token.strip()
    if not token:
        raise RuntimeError(
            "X API token is missing. Set AI_MODEL_WATCH_X_BEARER_TOKEN in .env or the environment."
        )

    documents: list[Document] = []
    seen_urls: set[str] = set()
    for query in settings.x_queries:
        params = urllib.parse.urlencode(
            {
                "query": query,
                "max_results": settings.x_max_results,
                "tweet.fields": "created_at,author_id,lang",
                "expansions": "author_id",
                "user.fields": "username,name",
            }
        )
        request = urllib.request.Request(
            f"{source.url}?{params}",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": settings.user_agent,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
            batch = parse_x_search_response(response.read(), source)
        for document in batch:
            if document.url not in seen_urls:
                seen_urls.add(document.url)
                documents.append(document)
    return documents
