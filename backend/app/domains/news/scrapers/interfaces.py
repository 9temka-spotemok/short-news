"""
Shared interfaces for news scrapers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol
from uuid import UUID


@dataclass(slots=True)
class CompanyContext:
    """Lightweight company descriptor passed to scraper providers."""

    id: Optional[UUID]
    name: str
    website: Optional[str]
    news_page_url: Optional[str] = None


@dataclass(slots=True)
class ScrapedNewsItem:
    """Normalized structure produced by scraper providers."""

    title: str
    summary: Optional[str]
    content: Optional[str]
    source_url: str
    source_type: str
    category: Optional[str]
    published_at: Optional[datetime]


class ScraperProvider(Protocol):
    """Interface for scraping providers used by the news domain."""

    async def scrape_company(
        self,
        company: CompanyContext,
        *,
        max_articles: int = 10,
        skip_urls: Optional[set[str]] = None,
    ) -> List[ScrapedNewsItem]:
        ...

    async def close(self) -> None:
        ...




