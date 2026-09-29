from __future__ import annotations

import json
import re
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from ..config import Settings
from ..models import Document, Source


_QUESTION_PREFIX = re.compile(
    r"^(?:how|what|why|when|where|who|which|is|are|am|was|were|can|could|would|should|do|does|did|has|have|had|anyone|anybody|any|help|looking for)\b",
    re.IGNORECASE,
)


def is_reddit_question(title: str) -> bool:
    """Recognize common question-style Reddit titles, including titles without '?'."""
    normalized = title.strip()
    return "?" in normalized or "？" in normalized or bool(_QUESTION_PREFIX.match(normalized))


def fetch_reddit_question_details(
    url: str, settings: Settings, *, max_comments: int = 6, max_comment_chars: int = 8_000
) -> tuple[str, str]:
    """Fetch a Reddit question's self-text and its highest-ranked non-empty comments."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname not in {"reddit.com", "www.reddit.com", "old.reddit.com"}:
        raise ValueError("Expected a Reddit post URL")
    path = urllib.parse.quote(parsed.path.rstrip("/"), safe="/%:@!$&'()*+,;=-._~")
    if not path.endswith(".json"):
        path += ".json"
    query = urllib.parse.urlencode({"sort": "top", "limit": 50, "depth": 2, "raw_json": 1})
    hosts = [parsed.netloc]
    if parsed.netloc == "www.reddit.com":
        hosts.append("old.reddit.com")
    elif parsed.netloc == "old.reddit.com":
        hosts.append("www.reddit.com")
    last_forbidden: urllib.error.HTTPError | None = None
    payload = b""
    for host in hosts:
        json_url = urllib.parse.urlunsplit(("https", host, path, query, ""))
        request = urllib.request.Request(
            json_url,
            headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
                payload = response.read(5_000_001)
            if len(payload) > 5_000_000:
                raise ValueError("Reddit discussion exceeds the download size limit")
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 403 or host == hosts[-1]:
                raise
            last_forbidden = exc
    if not payload and last_forbidden is not None:
        raise last_forbidden
    data = json.loads(payload)
    if not isinstance(data, list) or len(data) < 2:
        raise ValueError("Reddit did not return a post and comment listing")
    post_children = data[0].get("data", {}).get("children", [])
    if not post_children:
        raise ValueError("Reddit response contains no post")
    post = post_children[0].get("data", {})
    selftext = str(post.get("selftext") or "").strip()

    comments: list[tuple[int, str, str]] = []

    def collect(children: list[dict], depth: int = 0) -> None:
        if depth > 2:
            return
        for child in children:
            if child.get("kind") != "t1":
                continue
            comment = child.get("data", {})
            body = str(comment.get("body") or "").strip()
            author = str(comment.get("author") or "[deleted]").strip()
            if body and body not in {"[deleted]", "[removed]"} and author.lower() != "automoderator":
                score = comment.get("score", 0)
                comments.append((score if isinstance(score, int) else 0, author, body))
            replies = comment.get("replies")
            if isinstance(replies, dict):
                collect(replies.get("data", {}).get("children", []), depth + 1)

    comment_children = data[1].get("data", {}).get("children", [])
    collect(comment_children)
    comments.sort(key=lambda item: item[0], reverse=True)

    rendered: list[str] = []
    used_chars = 0
    seen: set[str] = set()
    for score, author, body in comments:
        normalized_body = " ".join(body.split())
        if normalized_body in seen:
            continue
        seen.add(normalized_body)
        remaining = max_comment_chars - used_chars
        if remaining <= 0:
            break
        excerpt = normalized_body[: min(3_000, remaining)].rstrip()
        if len(normalized_body) > len(excerpt):
            excerpt += "…"
        block = f"u/{author} · score {score}\n{excerpt}"
        rendered.append(block)
        used_chars += len(excerpt)
        if len(rendered) >= max_comments:
            break

    answer_text = "\n\n".join(rendered)
    return selftext, answer_text


def parse_reddit_listing(payload: str | bytes, source: Source) -> list[Document]:
    data: dict[str, Any] = json.loads(payload)
    children = data.get("data", {}).get("children", [])
    documents: list[Document] = []
    for child in children:
        post = child.get("data", {})
        if post.get("stickied") or post.get("over_18"):
            continue
        title = str(post.get("title") or "").strip()
        permalink = str(post.get("permalink") or "").strip()
        if not title or not permalink:
            continue
        url = "https://www.reddit.com" + permalink if permalink.startswith("/") else permalink
        body = str(post.get("selftext") or "").strip()
        content = f"{title}\n\n{body}".strip()
        created = post.get("created_utc")
        published_at = None
        if isinstance(created, (int, float)):
            published_at = datetime.fromtimestamp(created, tz=timezone.utc)
        documents.append(
            Document(
                source_name=source.name,
                title=title,
                url=url,
                content=content,
                author=post.get("author") or None,
                published_at=published_at,
            )
        )
    return documents


def collect_reddit(source: Source, settings: Settings) -> list[Document]:
    parsed = urllib.parse.urlsplit(source.url)
    candidate_urls = [source.url]
    if parsed.netloc == "www.reddit.com":
        candidate_urls.append(urllib.parse.urlunsplit(parsed._replace(netloc="old.reddit.com")))

    last_error: Exception | None = None
    for url in candidate_urls:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
                return parse_reddit_listing(response.read(), source)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code != 403:
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"No Reddit endpoint available for {source.url}")
