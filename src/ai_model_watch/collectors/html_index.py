from __future__ import annotations

import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from ..config import Settings
from ..models import Document, Source


_DATE_PREFIX = re.compile(r"^([A-Z][a-z]{2} \d{1,2}, \d{4})\s*")


_DATE = r"[A-Z][a-z]{2} \d{1,2}, \d{4}"
_DATE_PREFIX = re.compile(rf"^({_DATE})\s*")
_FEATURED_CARD = re.compile(rf"^(.+?)(?:Announcements|Product|Research|Policy|Society|Interpretability|Alignment|Economic Research|Customer stories|Education)?({_DATE})")


def _split_listing_date(title: str) -> tuple[str, datetime | None]:
    """Anthropic's index renders 'Sep 23, 2026Science Title' (or 'TitleAnnouncementsSep 28, 2026Blurb') as one link text."""
    featured = _FEATURED_CARD.match(title)
    match = _DATE_PREFIX.match(title)
    if match:
        date_text, clean = match.group(1), title[match.end():].strip()
    elif featured:
        date_text, clean = featured.group(2), featured.group(1).strip()
    else:
        return title, None
    try:
        published = datetime.strptime(date_text, "%b %d, %Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return title, None
    return clean or title, published

class _ArticleLinkParser(HTMLParser):
    """Small dependency-free parser for official news index pages."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        self._href = attributes.get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        title = " ".join("".join(self._text).split())
        if title and self._href:
            self.links.append((title, self._href))
        self._href = None
        self._text = []


def collect_html_index(source: Source, settings: Settings) -> list[Document]:
    request = urllib.request.Request(source.url, headers={"User-Agent": settings.user_agent})
    with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
        html = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")

    parser = _ArticleLinkParser()
    parser.feed(html)
    documents: list[Document] = []
    seen_urls: set[str] = set()
    for title, relative_url in parser.links:
        url = urljoin(source.url, relative_url)
        path = urlsplit(url).path
        # Model launches such as /claude-sonnet-5-5 live outside /news/.
        if url in seen_urls or not (path.startswith("/news/") or path.startswith("/claude-")):
            continue
        seen_urls.add(url)
        title, published_at = _split_listing_date(title)
        documents.append(Document(source_name=source.name, title=title, url=url, content=title, published_at=published_at))
    return documents
