"""RSS and Atom feed collector for dynamic news knowledge."""

from __future__ import annotations

from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET
from urllib import request
from urllib.parse import urlparse

from .base import CollectedKnowledgeItem, compact_text, metadata_without_none
from .web_page import HtmlFetcher, WebPageCollectionError, validate_collectable_url
from ..repository import DatasetName

DEFAULT_MAX_FEED_BYTES = 1_000_000
ATOM_NS = "{http://www.w3.org/2005/Atom}"


@dataclass(slots=True)
class RSSNewsCollector:
    """Collect a bounded set of RSS/Atom entries as dynamic knowledge records."""

    feed_url: str
    dataset: DatasetName = "dynamic"
    category: str = "news"
    symbol: str | None = None
    topic: str | None = None
    max_items: int = 10
    fetcher: HtmlFetcher | None = None

    def collect(self) -> list[CollectedKnowledgeItem]:
        """Fetch and normalize feed entries."""
        validate_collectable_url(self.feed_url)
        xml_text = (self.fetcher or fetch_feed_xml)(self.feed_url)
        parsed_items = parse_feed_items(xml_text)
        return [
            self._to_collected_item(item)
            for item in parsed_items[: max(0, self.max_items)]
        ]

    def _to_collected_item(self, item: dict[str, str]) -> CollectedKnowledgeItem:
        title = item.get("title") or "Untitled feed item"
        link = item.get("link") or self.feed_url
        summary = item.get("summary") or ""
        published_at = item.get("published_at") or ""
        text = compact_text(
            "\n".join(
                value
                for value in (
                    f"Title: {title}",
                    f"Summary: {summary}" if summary else "",
                    f"Published: {published_at}" if published_at else "",
                    f"Source URL: {link}",
                )
                if value
            )
        )

        return CollectedKnowledgeItem(
            name=_record_name(title, link),
            text=text,
            metadata=metadata_without_none(
                {
                    "dataset": self.dataset,
                    "source": "rss_feed",
                    "source_url": link,
                    "feed_url": self.feed_url,
                    "title": title,
                    "category": self.category,
                    "symbol": self.symbol,
                    "topic": self.topic,
                    "published_at": published_at,
                    "reliability": "medium",
                    "time_sensitivity": "high",
                }
            ),
            dataset=self.dataset,
        )


def fetch_feed_xml(
    url: str,
    *,
    timeout_seconds: float = 15.0,
    max_bytes: int = DEFAULT_MAX_FEED_BYTES,
) -> str:
    """Fetch an RSS/Atom feed with basic URL and response-size safeguards."""
    validate_collectable_url(url)
    req = request.Request(url, headers={"User-Agent": "OrcaTradingYuki/0.1"})
    with request.urlopen(req, timeout=timeout_seconds) as response:
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise WebPageCollectionError("Feed response exceeded the maximum allowed size.")
        charset = response.headers.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")


def parse_feed_items(xml_text: str) -> list[dict[str, str]]:
    """Parse RSS or Atom feed XML into simple dictionaries."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise ValueError("Feed XML could not be parsed.") from error

    rss_items = root.findall(".//item")
    if rss_items:
        return [_parse_rss_item(item) for item in rss_items]

    atom_entries = root.findall(f".//{ATOM_NS}entry")
    if atom_entries:
        return [_parse_atom_entry(entry) for entry in atom_entries]

    return []


def _parse_rss_item(item: ET.Element) -> dict[str, str]:
    return {
        "title": _element_text(item, "title"),
        "link": _element_text(item, "link"),
        "summary": _strip_markup(_element_text(item, "description")),
        "published_at": _element_text(item, "pubDate"),
    }


def _parse_atom_entry(entry: ET.Element) -> dict[str, str]:
    link = ""
    for element in entry.findall(f"{ATOM_NS}link"):
        href = element.attrib.get("href")
        if href:
            link = href
            break

    return {
        "title": _element_text(entry, f"{ATOM_NS}title"),
        "link": link,
        "summary": _strip_markup(
            _element_text(entry, f"{ATOM_NS}summary")
            or _element_text(entry, f"{ATOM_NS}content")
        ),
        "published_at": (
            _element_text(entry, f"{ATOM_NS}updated")
            or _element_text(entry, f"{ATOM_NS}published")
        ),
    }


def _element_text(parent: ET.Element, name: str) -> str:
    element = parent.find(name)
    if element is None or element.text is None:
        return ""
    return compact_text(element.text)


def _strip_markup(value: str) -> str:
    return compact_text(re.sub(r"<[^>]+>", " ", value))


def _record_name(title: str, link: str) -> str:
    parsed = urlparse(link)
    host = parsed.netloc.replace(":", "_") or "feed_item"
    slug = compact_text(title).lower().replace(" ", "_")
    slug = "".join(char for char in slug if char.isalnum() or char == "_").strip("_")
    return f"{host}_{slug}" if slug else host
