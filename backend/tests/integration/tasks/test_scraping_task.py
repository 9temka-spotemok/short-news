from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains.news.scrapers import registry as scraper_registry_module
from app.domains.news.scrapers.interfaces import ScrapedNewsItem
from app.models import Company, NewsItem
from app.tasks import scraping


class FakeProvider:
    def __init__(self):
        self.closed = False

    async def scrape_company(self, company, *, max_articles: int = 10):
        return [
            ScrapedNewsItem(
                title="AI Launches GPT-X",
                summary="New release summary",
                content="Full article content",
                source_url="https://example.com/gpt-x",
                source_type="blog",
                category="product_update",
                published_at=datetime.now(timezone.utc),
            )
        ]

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_scrape_ai_blogs_async_ingests_news(
    async_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
):
    async with async_session_factory() as session:
        unique_suffix = uuid4().hex[:8]
        company = Company(name=f"OpenAI-{unique_suffix}", website=f"https://openai.com/{unique_suffix}")
        session.add(company)
        await session.commit()
        await session.refresh(company)
        company_id = company.id

    monkeypatch.setattr(scraping, "AsyncSessionLocal", async_session_factory)
    monkeypatch.setattr(
        scraper_registry_module.NewsScraperRegistry,
        "get_provider",
        lambda self, company=None: FakeProvider(),
    )

    result = await scraping._scrape_ai_blogs_async()

    assert result["status"] == "success"
    assert result["scraped_count"] == 1

    async with async_session_factory() as session:
        items = await session.execute(
            select(NewsItem).where(NewsItem.source_url == "https://example.com/gpt-x")
        )
        news = items.scalar_one_or_none()
        assert news is not None
        assert str(news.company_id) == str(company_id)

