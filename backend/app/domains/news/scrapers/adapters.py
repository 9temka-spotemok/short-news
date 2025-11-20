"""
Adapters that bridge existing scraper implementations to domain interfaces.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from app.scrapers.universal_scraper import UniversalBlogScraper
from app.scrapers.real_scrapers import AINewsScraper

from .interfaces import CompanyContext, ScrapedNewsItem, ScraperProvider


class UniversalScraperProvider(ScraperProvider):
    """Adapter exposing UniversalBlogScraper via the ScraperProvider protocol."""

    def __init__(
        self, 
        scraper: Optional[UniversalBlogScraper] = None,
        health_service: Optional[Any] = None,
    ):
        self._scraper = scraper or UniversalBlogScraper()
        self._health_service = health_service

    async def scrape_company(
        self,
        company: CompanyContext,
        *,
        max_articles: int = 10,
        source_overrides: Optional[List[Dict]] = None,
        skip_urls: Optional[set[str]] = None,
    ) -> List[ScrapedNewsItem]:
        company_id_str = str(company.id) if company.id else None
        raw_items = await self._scraper.scrape_company_blog(
            company.name,
            company.website or "",
            news_page_url=company.news_page_url,
            max_articles=max_articles,
            source_overrides=source_overrides,
            skip_urls=skip_urls,
            company_id=company_id_str,
            health_service=self._health_service,
        )
        normalized: List[ScrapedNewsItem] = []
        for item in raw_items:
            published_at = item.get("published_at")
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except ValueError:
                    logger.debug("Failed to parse published_at %s", published_at)
                    published_at = None
            normalized.append(
                ScrapedNewsItem(
                    title=item.get("title", ""),
                    summary=item.get("summary"),
                    content=item.get("content"),
                    source_url=item.get("source_url", ""),
                    source_type=str(item.get("source_type") or "blog"),
                    category=item.get("category"),
                    published_at=published_at,
                )
            )
        return normalized

    async def close(self) -> None:
        await self._scraper.session.aclose()


class AINewsScraperProvider(ScraperProvider):
    """Adapter for curated AI news sources."""

    _FETCHERS: Dict[str, str] = {
        "openai": "scrape_openai_blog",
        "anthropic": "scrape_anthropic_news",
        "google": "scrape_google_ai_blog",
    }

    def __init__(
        self,
        company_name: str,
        scraper: Optional[AINewsScraper] = None,
    ) -> None:
        self._company_key = company_name.lower()
        self._scraper = scraper or AINewsScraper()

    async def scrape_company(
        self,
        company: CompanyContext,
        *,
        max_articles: int = 10,
        skip_urls: Optional[set[str]] = None,
    ) -> List[ScrapedNewsItem]:
        fetcher_name = self._FETCHERS.get(self._company_key)
        if not fetcher_name:
            return []

        fetcher: Optional[Callable[[], List[dict]]] = getattr(self._scraper, fetcher_name, None)
        if not fetcher:
            return []

        raw_items = await fetcher()
        normalized: List[ScrapedNewsItem] = []
        for item in raw_items[:max_articles]:
            published_at = item.get("published_at")
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except ValueError:
                    logger.debug("Failed to parse published_at %s", published_at)
                    published_at = None
            normalized.append(
                ScrapedNewsItem(
                    title=item.get("title", ""),
                    summary=item.get("summary"),
                    content=item.get("content"),
                    source_url=item.get("source_url", ""),
                    source_type=str(item.get("source_type") or "blog"),
                    category=item.get("category"),
                    published_at=published_at,
                )
            )
        return normalized

    async def close(self) -> None:
        await self._scraper.session.aclose()

