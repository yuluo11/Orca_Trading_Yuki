"""Collector for single web-page knowledge snippets."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
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


class _ReadableHTMLParser(HTMLParser):
    """Small stdlib HTML text extractor for collector tests and fallback usage."""

    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self._capture_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "nav", "header", "footer"}:
            self._skip_depth += 1
        elif tag == "title":
            self._capture_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "nav", "header", "footer"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._capture_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._capture_title:
            self.title_parts.append(data)
        else:
            self.body_parts.append(data)


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
    text = compact_text(" ".join(parser.body_parts))
    return ExtractedWebPageText(text=text, title=title)


def _record_name(title: str, url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "_")
    slug = compact_text(title).lower().replace(" ", "_")
    slug = "".join(char for char in slug if char.isalnum() or char == "_").strip("_")
    return f"{host}_{slug}" if slug else host
