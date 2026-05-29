"""Single-page web collector for user-provided URLs."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from typing import Callable
from urllib import request
from urllib.parse import urlparse

from ..repository import DatasetName
from .base import CollectedKnowledgeItem


HtmlFetcher = Callable[[str], str]


@dataclass(slots=True)
class WebPageCollector:
    """Collect one user-provided web page into a normalized knowledge item."""

    url: str
    dataset: DatasetName = "dynamic"
    category: str = "web_page"
    symbol: str | None = None
    topic: str | None = None
    fetcher: HtmlFetcher | None = None

    def collect(self) -> list[CollectedKnowledgeItem]:
        """Fetch and extract a single web page."""
        html = (self.fetcher or fetch_html)(self.url)
        extracted = extract_web_page_text(html)
        if not extracted.text:
            raise ValueError(f"No readable page text extracted from URL: {self.url}")

        title = extracted.title or self._fallback_title()
        return [
            CollectedKnowledgeItem(
                name=self._record_name(title),
                text=extracted.text,
                dataset=self.dataset,
                metadata={
                    "source": self.url,
                    "source_url": self.url,
                    "title": title,
                    "category": self.category,
                    "topic": self.topic or self._fallback_topic(title),
                    "reliability": "medium",
                    "time_sensitivity": "high",
                    **({"symbol": self.symbol.strip().upper()} if self.symbol else {}),
                },
            )
        ]

    def _fallback_title(self) -> str:
        parsed = urlparse(self.url)
        path_name = parsed.path.rstrip("/").split("/")[-1]
        return path_name.replace("-", " ").replace("_", " ").title() or parsed.netloc

    def _fallback_topic(self, title: str) -> str:
        return title.strip().lower()[:80] or "web page"

    def _record_name(self, title: str) -> str:
        parsed = urlparse(self.url)
        host = re.sub(r"[^a-z0-9]+", "_", parsed.netloc.lower()).strip("_")
        title_part = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        return "_".join(part for part in ("web", host, title_part) if part)[:120] or "web_page"


@dataclass(slots=True)
class ExtractedWebPage:
    """Readable web-page extraction result."""

    title: str
    text: str


def fetch_html(url: str, *, timeout_seconds: float = 15.0) -> str:
    """Fetch HTML from a user-provided URL."""
    req = request.Request(
        url,
        headers={"User-Agent": "OrcaTradingYuki/0.1 knowledge collector"},
    )
    with request.urlopen(req, timeout=timeout_seconds) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def extract_web_page_text(html: str) -> ExtractedWebPage:
    """Extract a title and readable text from a small HTML document."""
    parser = _ReadableTextHTMLParser()
    parser.feed(html)
    return ExtractedWebPage(
        title=_clean_inline_text(parser.title),
        text=_clean_block_text("\n".join(parser.text_blocks)),
    )


class _ReadableTextHTMLParser(HTMLParser):
    """Small HTML text extractor that ignores scripts, styles, and navigation noise."""

    ignored_tags = {"script", "style", "noscript", "svg", "canvas", "nav", "footer", "header"}
    block_tags = {"p", "article", "section", "div", "li", "h1", "h2", "h3", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self._in_title = False
        self._current_parts: list[str] = []
        self.title = ""
        self.text_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in self.ignored_tags:
            self._ignored_depth += 1
        if normalized_tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in self.ignored_tags and self._ignored_depth > 0:
            self._ignored_depth -= 1
        if normalized_tag == "title":
            self._in_title = False
        if normalized_tag in self.block_tags:
            self._flush_current_block()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        text = _clean_inline_text(data)
        if not text:
            return
        if self._in_title:
            self.title = f"{self.title} {text}".strip()
            return
        self._current_parts.append(text)

    def close(self) -> None:
        self._flush_current_block()
        super().close()

    def _flush_current_block(self) -> None:
        block = _clean_inline_text(" ".join(self._current_parts))
        self._current_parts = []
        if len(block) >= 20:
            self.text_blocks.append(block)


def _clean_inline_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_block_text(text: str) -> str:
    lines = [_clean_inline_text(line) for line in text.splitlines()]
    return "\n\n".join(line for line in lines if line)
