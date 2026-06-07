"""HTTP API entrypoints and optional adapters for backend services."""

from .knowledge_api import create_knowledge_api
from .server import app, create_app

__all__ = ["app", "create_app", "create_knowledge_api"]
