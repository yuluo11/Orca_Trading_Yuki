"""Collectors for turning external or manual inputs into dynamic knowledge."""

from .base import CollectedKnowledgeItem, KnowledgeCollector, ingest_collected_items
from .manual import ManualKnowledgeCollector
from .web_page import WebPageCollector, extract_web_page_text, fetch_html

__all__ = [
    "CollectedKnowledgeItem",
    "KnowledgeCollector",
    "ManualKnowledgeCollector",
    "WebPageCollector",
    "extract_web_page_text",
    "fetch_html",
    "ingest_collected_items",
]
