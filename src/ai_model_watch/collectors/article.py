from __future__ import annotations

import logging
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import quote, urlsplit, urlunsplit

import trafilatura

from ..config import Settings
from ..database import Database
from .reddit import fetch_reddit_question_details, is_reddit_question

logger = logging.getLogger(__name__)


def clean_feed_html(value: str) -> str:
    """Turn embedded feed HTML into paragraphs, without executing markup."""
    if '<' not in value:
        return value.strip()
    return trafilatura.html2txt('<html><body>' + value + '</body></html>').strip()


def fetch_article_body(url: str, source_type: str, settings: Settings, title: str = '') -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {'http', 'https'}:
        raise ValueError('Unsupported article URL')
    if source_type == 'reddit':
        if parsed.hostname not in {'reddit.com', 'www.reddit.com', 'old.reddit.com'}:
            raise ValueError('Expected a Reddit post URL')
        if is_reddit_question(title):
            try:
                post_body, answers = fetch_reddit_question_details(url, settings)
                sections = [post_body] if post_body else []
                if answers:
                    sections.append('[Reddit discussion answers]\n' + answers)
                combined = '\n\n'.join(sections).strip()
                if answers or len(combined) >= 80:
                    return combined
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    raise
                logger.warning('Reddit comment retrieval failed for %s: %s', url, exc)
            except Exception as exc:
                logger.warning('Reddit comment retrieval failed for %s: %s', url, exc)
        rss_path = quote(parsed.path.rstrip('/') + '/.rss', safe="/%:@!$&'()*+,;=-._~")
        hosts = [parsed.netloc]
        if parsed.netloc == 'www.reddit.com':
            hosts.append('old.reddit.com')
        elif parsed.netloc == 'old.reddit.com':
            hosts.append('www.reddit.com')
        last_forbidden: urllib.error.HTTPError | None = None
        html = ''
        for host in hosts:
            rss_url = urlunsplit((parsed.scheme, host, rss_path, '', ''))
            request = urllib.request.Request(
                rss_url,
                headers={
                    'User-Agent': settings.user_agent,
                    'Accept': 'application/atom+xml, application/rss+xml, application/xml;q=0.9, */*',
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
                    payload = response.read(5_000_001)
                    if len(payload) > 5_000_000:
                        raise ValueError('Article exceeds the download size limit')
                    html = payload.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 403 or host == hosts[-1]:
                    raise
                last_forbidden = exc
        if not html and last_forbidden is not None:
            raise last_forbidden
    else:
        request = urllib.request.Request(url, headers={'User-Agent': settings.user_agent})
        with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
            payload = response.read(5_000_001)
            if len(payload) > 5_000_000:
                raise ValueError('Article exceeds the download size limit')
            html = payload.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
    if source_type == 'reddit':
        root = ET.fromstring(html)
        entries = [node for node in root if node.tag.rsplit('}', 1)[-1] == 'entry']
        if not entries:
            raise ValueError('Reddit feed contains no post')
        raw = next((''.join(node.itertext()) for node in entries[0] if node.tag.rsplit('}', 1)[-1] == 'content'), '')
        body = clean_feed_html(raw)
        body = body.split('submitted by', 1)[0].strip()
        if is_reddit_question(title):
            rendered_comments: list[str] = []
            used_chars = 0
            for entry in entries[1:]:
                raw_comment = next((''.join(node.itertext()) for node in entry if node.tag.rsplit('}', 1)[-1] == 'content'), '')
                comment = clean_feed_html(raw_comment).strip()
                if not comment or comment in {'[deleted]', '[removed]'}:
                    continue
                author_node = next((node for node in entry if node.tag.rsplit('}', 1)[-1] == 'author'), None)
                author = next((node.text for node in author_node or () if node.tag.rsplit('}', 1)[-1] == 'name' and node.text), 'Reddit user')
                remaining = 8_000 - used_chars
                if remaining <= 0:
                    break
                excerpt = comment[:min(3_000, remaining)].rstrip()
                if len(comment) > len(excerpt):
                    excerpt += '…'
                rendered_comments.append(f'u/{author}\n{excerpt}')
                used_chars += len(excerpt)
                if len(rendered_comments) == 6:
                    break
            if rendered_comments:
                body = '\n\n'.join(part for part in (body, '[Reddit discussion answers]\n' + '\n\n'.join(rendered_comments)) if part)
    else:
        body = trafilatura.extract(html, include_comments=False, include_tables=True, favor_precision=True) or ''
    if len(body.strip()) < 80:
        raise ValueError('No readable article body (link/image-only post or blocked page)')
    return body.strip()


@dataclass(frozen=True)
class BodySummary:
    collected: int
    failed: int


def collect_article_bodies(database: Database, settings: Settings, limit: int = 100) -> BodySummary:
    collected = failed = 0
    blocked_sources: set[str] = set()
    for document in database.list_body_candidates(limit):
        try:
            source_type = str(document['source_type'])
            feed_content = clean_feed_html(str(document['content']))
            if source_type == 'x':
                body = feed_content
            elif source_type == 'reddit' and is_reddit_question(str(document['title'])):
                if source_type in blocked_sources:
                    continue
                body = fetch_article_body(
                    str(document['url']), source_type, settings, title=str(document['title'])
                )
            elif source_type == 'reddit' and len(feed_content) >= 80 and feed_content != document['title']:
                body = feed_content.split('submitted by', 1)[0].strip()
                if len(body) < 80:
                    raise ValueError('Post has no text body')
            else:
                if source_type in blocked_sources:
                    continue
                body = fetch_article_body(
                    str(document['url']), source_type, settings, title=str(document['title'])
                )
            database.update_article_body(int(document['id']), body)
            collected += 1
            print(f"[body] id={document['id']} characters={len(body)}", flush=True)
        except Exception as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                blocked_sources.add(str(document['source_type']))
            database.update_article_body(int(document['id']), None, str(exc))
            failed += 1
            logger.warning('Body collection failed for document %s: %s', document['id'], exc)
    return BodySummary(collected, failed)
