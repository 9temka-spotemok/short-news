"""
Service orchestrating news scraping and ingestion.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.scrapers import CompanyContext, NewsScraperRegistry

from .ingestion_service import NewsIngestionService
from .source_health_service import SourceHealthService
from app.utils.datetime_utils import parse_iso_datetime, to_naive_utc, utc_now_naive


class NewsScraperService:
    """Coordinates scraper providers and ingestion pipeline."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        registry: Optional[NewsScraperRegistry] = None,
        ingestion_service: Optional[NewsIngestionService] = None,
        health_service: Optional[SourceHealthService] = None,
    ) -> None:
        self._session = session
        self._registry = registry or NewsScraperRegistry()
        self._ingestion_service = ingestion_service or NewsIngestionService(session)
        self._health_service = health_service or SourceHealthService(session)

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
        # Получаем список отключенных URL для компании
        skip_urls: Optional[set[str]] = None
        if company.id:
            skip_urls = await self._health_service.get_dead_urls(company.id)
            if skip_urls:
                logger.debug(
                    f"Found {len(skip_urls)} disabled URLs for company {company.id}, "
                    f"will skip them during scraping"
                )
        
        # Передаем health_service в provider для записи результатов
        provider = self._registry.get_provider(company)
        
        # Если provider - UniversalScraperProvider, передаем health_service
        from app.domains.news.scrapers.adapters import UniversalScraperProvider
        if isinstance(provider, UniversalScraperProvider):
            # Создаем новый provider с health_service
            provider = UniversalScraperProvider(
                scraper=provider._scraper,
                health_service=self._health_service,
            )
        
        items = await provider.scrape_company(
            company, 
            max_articles=max_articles,
            skip_urls=skip_urls,
        )

        ingested = 0
        for item in items:
            # Проверяем, что company.id существует перед созданием новости
            if not company.id:
                logger.warning(
                    "Skipping news item %s: company %s has no ID",
                    item.source_url,
                    company.name
                )
                continue
                
            payload = {
                "title": item.title,
                "summary": item.summary,
                "content": item.content,
                "source_url": item.source_url,
                "source_type": item.source_type,
                "category": item.category,
                "published_at": _coerce_published_at(item.published_at),
                "company_id": str(company.id),  # Всегда передаем UUID, не имя компании
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


def _coerce_published_at(value: Optional[datetime]) -> datetime:
    dt: Optional[datetime]
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = parse_iso_datetime(value)
    else:
        dt = None

    if dt is None:
        dt = utc_now_naive()
    normalized = to_naive_utc(dt)
    if normalized is None:  # Fallback for defensive path
        normalized = utc_now_naive()
    return normalized

