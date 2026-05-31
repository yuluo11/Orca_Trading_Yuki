"""Collector for single web-page knowledge snippets."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
from typing import Callable
from urllib import request
from urllib.parse import urlparse

from .base import CollectedKnowledgeItem, compact_text, metadata_without_none
from ..repository import DatasetName

HtmlFetcher = Callable[[str], str]

DEFAULT_MAX_HTML_BYTES = 1_000_000
ALLOWED_WEB_SCHEMES = {"http", "https"}
TEXTUAL_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}


class WebPageCollectionError(ValueError):
    """Raised when a page is unsafe or unsuitable for knowledge collection."""


@dataclass(slots=True)
class WebPageCollector:
    """Collect a single URL as a dynamic knowledge item."""

    url: str
    dataset: DatasetName = "dynamic"
    category: str = "web_page"
    symbol: str | None = None
    topic: str | None = None
    title: str | None = None
    fetcher: HtmlFetcher | None = None

    def collect(self) -> list[CollectedKnowledgeItem]:
        """Fetch, clean, and normalize a web page into one knowledge item."""
        validate_collectable_url(self.url)
        html = (self.fetcher or fetch_html)(self.url)
        extracted = extract_web_page_text(html)
        if not extracted.text:
            raise WebPageCollectionError("Collected web page did not contain readable text.")

        title = self.title or extracted.title or self.url
        return [
            CollectedKnowledgeItem(
                name=_record_name(title, self.url),
                text=extracted.text,
                metadata=metadata_without_none(
                    {
                        "dataset": self.dataset,
                        "source": "web_page",
                        "source_url": self.url,
                        "title": title,
                        "category": self.category,
                        "symbol": self.symbol,
                        "topic": self.topic,
                        "summary": extracted.description,
                        "author": extracted.author,
                        "published_at": extracted.published_at,
                        "extraction_method": extracted.extraction_method,
                        "reliability": "medium",
                        "time_sensitivity": "high",
                    }
                ),
                dataset=self.dataset,
            )
        ]


@dataclass(slots=True)
class ExtractedWebPageText:
    """Cleaned web-page content and optional page title."""

    text: str
    title: str | None = None
    description: str | None = None
    author: str | None = None
    published_at: str | None = None
    extraction_method: str = "body"


class _ReadableHTMLParser(HTMLParser):
    """Small stdlib HTML text extractor for collector tests and fallback usage."""

    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.primary_parts: list[str] = []
        self.description_parts: list[str] = []
        self.author_parts: list[str] = []
        self.published_at_parts: list[str] = []
        self.json_ld_parts: list[str] = []
        self._capture_title = False
        self._capture_json_ld = False
        self._primary_tags: list[str] = []
        self._primary_depth = 0
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if tag == "meta":
            self._capture_meta(attr_map)
            return
        if tag == "script" and attr_map.get("type", "").lower() == "application/ld+json":
            self._capture_json_ld = True
            return

        if tag in {
            "script",
            "style",
            "noscript",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
            "button",
            "svg",
            "canvas",
            "iframe",
        }:
            self._skip_depth += 1
        elif tag == "title":
            self._capture_title = True
        elif tag in {"article", "main"} or _looks_like_primary_content(attr_map):
            self._primary_depth += 1
            self._primary_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in {
            "script",
            "style",
            "noscript",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
            "button",
            "svg",
            "canvas",
            "iframe",
        } and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "script" and self._capture_json_ld:
            self._capture_json_ld = False
        elif tag == "title":
            self._capture_title = False
        elif self._primary_tags and self._primary_tags[-1] == tag:
            self._primary_tags.pop()
            self._primary_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._capture_json_ld:
            self.json_ld_parts.append(data)
            return
        cleaned = compact_text(data)
        if not cleaned:
            return
        if self._capture_title:
            _append_unique(self.title_parts, cleaned)
        else:
            _append_unique(self.body_parts, cleaned)
            if self._primary_depth:
                _append_unique(self.primary_parts, cleaned)

    def _capture_meta(self, attr_map: dict[str, str]) -> None:
        key = (attr_map.get("name") or attr_map.get("property") or "").lower()
        content = compact_text(attr_map.get("content", ""))
        if not content:
            return
        if key in {"description", "og:description", "twitter:description"}:
            _append_unique(self.description_parts, content)
        elif key in {"og:title", "twitter:title"} and not self.title_parts:
            _append_unique(self.title_parts, content)
        elif key in {"author", "article:author"}:
            _append_unique(self.author_parts, content)
        elif key in {
            "article:published_time",
            "article:modified_time",
            "date",
            "dc.date",
            "dc.date.issued",
            "pubdate",
        }:
            _append_unique(self.published_at_parts, content)


def validate_collectable_url(url: str) -> None:
    """Allow only network HTTP(S) URLs for dynamic collection."""
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_WEB_SCHEMES:
        raise WebPageCollectionError("Only http and https URLs can be collected.")
    if not parsed.netloc:
        raise WebPageCollectionError("URL must include a network host.")


def fetch_html(
    url: str,
    *,
    timeout_seconds: float = 15.0,
    max_bytes: int = DEFAULT_MAX_HTML_BYTES,
) -> str:
    """Fetch textual web content with basic safety guards."""
    validate_collectable_url(url)
    req = request.Request(url, headers={"User-Agent": "OrcaTradingYuki/0.1"})
    with request.urlopen(req, timeout=timeout_seconds) as response:
        content_type = response.headers.get_content_type()
        if content_type not in TEXTUAL_CONTENT_TYPES:
            raise WebPageCollectionError(f"Unsupported content type: {content_type}")

        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise WebPageCollectionError("Web page response exceeded the maximum allowed size.")

        charset = response.headers.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")


def extract_web_page_text(html: str) -> ExtractedWebPageText:
    """Extract readable title and body text from a small HTML document."""
    parser = _ReadableHTMLParser()
    parser.feed(html)
    title = compact_text(" ".join(parser.title_parts)) or None
    description = compact_text(" ".join(parser.description_parts)) or None
    json_ld_metadata = _extract_json_ld_metadata(parser.json_ld_parts)
    title = title or json_ld_metadata.get("title")
    description = description or json_ld_metadata.get("description")
    author = compact_text(" ".join(parser.author_parts)) or json_ld_metadata.get("author")
    published_at = (
        compact_text(" ".join(parser.published_at_parts))
        or json_ld_metadata.get("published_at")
    )
    primary_text = compact_text(" ".join(parser.primary_parts))
    body_text = compact_text(" ".join(parser.body_parts))
    if _is_better_primary_text(primary_text, body_text):
        return ExtractedWebPageText(
            text=primary_text,
            title=title,
            description=description,
            author=author,
            published_at=published_at,
            extraction_method="primary_content",
        )
    return ExtractedWebPageText(
        text=body_text,
        title=title,
        description=description,
        author=author,
        published_at=published_at,
        extraction_method="body",
    )


def _record_name(title: str, url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "_")
    slug = compact_text(title).lower().replace(" ", "_")
    slug = "".join(char for char in slug if char.isalnum() or char == "_").strip("_")
    return f"{host}_{slug}" if slug else host


def _looks_like_primary_content(attr_map: dict[str, str]) -> bool:
    marker = " ".join(
        attr_map.get(key, "")
        for key in ("id", "class", "role", "itemprop")
    ).lower()
    return any(
        token in marker
        for token in (
            "article",
            "content",
            "main",
            "post",
            "story",
            "entry",
            "body",
        )
    )


def _is_better_primary_text(primary_text: str, body_text: str) -> bool:
    if len(primary_text) < 40:
        return False
    if len(body_text) == 0:
        return True
    return len(primary_text) >= min(80, len(body_text) * 0.25)


def _append_unique(parts: list[str], value: str) -> None:
    if not value:
        return
    if parts and parts[-1] == value:
        return
    if len(value) >= 20 and value in parts:
        return
    parts.append(value)


def _extract_json_ld_metadata(parts: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for part in parts:
        try:
            payload = json.loads(part)
        except json.JSONDecodeError:
            continue
        for candidate in _json_ld_candidates(payload):
            _merge_json_ld_candidate(metadata, candidate)
    return metadata


def _json_ld_candidates(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        candidates: list[dict[str, object]] = []
        for item in payload:
            candidates.extend(_json_ld_candidates(item))
        return candidates
    if not isinstance(payload, dict):
        return []
    candidates = [payload]
    graph = payload.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            candidates.extend(_json_ld_candidates(item))
    return candidates


def _merge_json_ld_candidate(metadata: dict[str, str], candidate: dict[str, object]) -> None:
    if "title" not in metadata:
        title = _json_string(candidate.get("headline") or candidate.get("name"))
        if title:
            metadata["title"] = title
    if "description" not in metadata:
        description = _json_string(candidate.get("description"))
        if description:
            metadata["description"] = description
    if "author" not in metadata:
        author = candidate.get("author")
        if isinstance(author, dict):
            author = author.get("name")
        elif isinstance(author, list) and author:
            first_author = author[0]
            author = first_author.get("name") if isinstance(first_author, dict) else first_author
        author_text = _json_string(author)
        if author_text:
            metadata["author"] = author_text
    if "published_at" not in metadata:
        published_at = _json_string(
            candidate.get("datePublished")
            or candidate.get("dateModified")
            or candidate.get("uploadDate")
        )
        if published_at:
            metadata["published_at"] = published_at


def _json_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return compact_text(value) or None
