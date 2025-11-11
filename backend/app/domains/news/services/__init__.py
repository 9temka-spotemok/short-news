"""
Service layer for the news domain.

Contains orchestration/business logic modules (ingestion, querying, scrapers).
"""

from .ingestion_service import NewsIngestionService
from .query_service import NewsQueryService
from .scraper_service import NewsScraperService

__all__ = [
    "NewsIngestionService",
    "NewsQueryService",
    "NewsScraperService",
]
