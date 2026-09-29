from __future__ import annotations

import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

from ..config import Settings
from ..models import Document, Source


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
        if url in seen_urls or "/news/" not in url:
            continue
        seen_urls.add(url)
        documents.append(Document(source_name=source.name, title=title, url=url, content=title))
    return documents
