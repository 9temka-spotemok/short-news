from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domains.news.scrapers.adapters import UniversalScraperProvider
from app.domains.news.scrapers.interfaces import CompanyContext


class FakeUniversalScraper:
    def __init__(self, payload):
        self._payload = payload
        class Session:
            async def aclose(self):
                return None

        self.session = Session()

    async def scrape_company_blog(
        self,
        company_name: str,
        website: str,
        news_page_url: str | None = None,
        max_articles: int = 10,
    ):
        return self._payload


@pytest.mark.asyncio
async def test_universal_scraper_provider_normalizes_data():
    published_at = datetime.now(timezone.utc)
    payload = [
        {
            "title": "Sample",
            "summary": "Short summary",
            "content": "Full content",
            "source_url": "https://example.com/sample",
            "source_type": "blog",
            "category": "product_update",
            "published_at": published_at.isoformat(),
        }
    ]
    provider = UniversalScraperProvider(FakeUniversalScraper(payload))
    context = CompanyContext(id=None, name="TestCo", website="https://test.co")

    items = await provider.scrape_company(context, max_articles=5)

    assert len(items) == 1
    item = items[0]
    assert item.title == "Sample"
    assert item.source_url == "https://example.com/sample"
    assert item.category == "product_update"
    assert item.published_at == published_at


@pytest.mark.asyncio
async def test_universal_scraper_provider_handles_missing_fields():
    payload = [
        {
            "title": "Without optional fields",
            "source_url": "https://example.com/optional",
            "source_type": None,
            "category": None,
        }
    ]
    provider = UniversalScraperProvider(FakeUniversalScraper(payload))
    context = CompanyContext(id=None, name="TestCo", website="https://test.co")

    items = await provider.scrape_company(context)

    assert len(items) == 1
    item = items[0]
    assert item.summary is None
    assert item.source_type == "blog"  # default when None supplied

