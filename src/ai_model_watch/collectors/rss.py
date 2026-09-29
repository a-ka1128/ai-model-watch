from __future__ import annotations

import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

from ..config import Settings
from ..models import Document, Source
from .article import clean_feed_html


def _text(element: ET.Element | None) -> str:
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def collect_rss(source: Source, settings: Settings) -> list[Document]:
    request = urllib.request.Request(
        source.url,
        headers={"User-Agent": settings.user_agent, "Accept": "application/rss+xml, application/xml"},
    )
    payload = b""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
                payload = response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            retry_after = exc.headers.get("Retry-After") or exc.headers.get("x-ratelimit-reset") or "10"
            try:
                delay = max(1, min(int(float(retry_after)) + 1, 60))
            except ValueError:
                delay = 11
            time.sleep(delay)

    root = ET.fromstring(payload)
    entries = [element for element in root.iter() if _local_name(element.tag) in {"item", "entry"}]
    documents: list[Document] = []
    for entry in entries:
        values: dict[str, str] = {}
        for child in entry.iter():
            name = _local_name(child.tag)
            if name not in values or not values[name]:
                value = _text(child)
                if name == "link" and not value:
                    value = child.attrib.get("href", "")
                values[name] = value
        url = values.get("link", "").strip()
        title = values.get("title", "Untitled").strip()
        description = values.get("encoded", "") or values.get("content", "") or values.get("description", "") or values.get("summary", "")
        content = clean_feed_html(description) or title
        if not url:
            continue
        author_element = next((child for child in entry if _local_name(child.tag) == 'author'), None)
        author = values.get('creator') or values.get('author') or None
        if author_element is not None:
            author = next((_text(child) for child in author_element if _local_name(child.tag) == 'name'), author)
        documents.append(
            Document(
                source_name=source.name,
                title=title,
                url=url,
                content=content,
                author=author,
                published_at=_parse_date(values.get("pubdate", "") or values.get("published", "") or values.get("updated", "")),
                language=values.get("language") or None,
            )
        )
    return documents
