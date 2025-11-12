"""
Service orchestrating news scraping and ingestion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.scrapers import CompanyContext, NewsScraperRegistry

from .ingestion_service import NewsIngestionService


class NewsScraperService:
    """Coordinates scraper providers and ingestion pipeline."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        registry: Optional[NewsScraperRegistry] = None,
        ingestion_service: Optional[NewsIngestionService] = None,
    ) -> None:
        self._session = session
        self._registry = registry or NewsScraperRegistry()
        self._ingestion_service = ingestion_service or NewsIngestionService(session)

    async def ingest_company_news(
        self,
        company: CompanyContext,
        *,
        max_articles: int = 10,
    ) -> int:
        """
        Fetch news for a company via registered provider and persist them.

        Returns number of successfully ingested items.
        """
        provider = self._registry.get_provider(company)
        items = await provider.scrape_company(company, max_articles=max_articles)

        ingested = 0
        for item in items:
            payload = {
                "title": item.title,
                "summary": item.summary,
                "content": item.content,
                "source_url": item.source_url,
                "source_type": item.source_type,
                "category": item.category,
                "published_at": _coerce_published_at(item.published_at),
                "company_id": str(company.id) if company.id else company.name,
            }
            try:
                news_item = await self._ingestion_service.create_news_item(payload)
            except Exception as exc:  # pragma: no cover - best-effort logging
                logger.warning(
                    "Failed to ingest scraped news for %s (%s): %s",
                    company.name,
                    item.source_url,
                    exc,
                )
            else:
                if getattr(news_item, "_was_created", False):
                    ingested += 1

        try:
            await provider.close()
        except Exception:  # pragma: no cover - best-effort logging
            logger.debug("Scraper provider close() raised", exc_info=True)
        return ingested


def _coerce_published_at(value: Optional[datetime]) -> str:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()

