"""Optional HTTP API adapters for backend services."""

from .knowledge_api import create_app, create_knowledge_api

__all__ = ["create_app", "create_knowledge_api"]
