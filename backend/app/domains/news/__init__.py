"""
News domain package.

Provides access to domain-specific services, repositories and facade helpers for
working with news items.  Concrete implementations live in subpackages.
"""

from .facade import NewsFacade  # noqa: F401
from .services.query_service import NewsQueryService  # noqa: F401
from .services.ingestion_service import NewsIngestionService  # noqa: F401
from .repositories import NewsRepository  # noqa: F401


