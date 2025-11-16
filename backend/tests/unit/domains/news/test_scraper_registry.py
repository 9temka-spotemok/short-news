from __future__ import annotations

import pytest

from app.domains.news.scrapers import CompanyContext, NewsScraperRegistry
from app.domains.news.scrapers.interfaces import ScraperProvider


class DummyProvider(ScraperProvider):
    async def scrape_company(self, company, *, max_articles: int = 10):
        return []

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_registry_returns_registered_provider():
    registry = NewsScraperRegistry()

    def predicate(company: CompanyContext) -> bool:
        return company.name == "Target"

    registry.register_provider(predicate, lambda: DummyProvider())

    provider = registry.get_provider(CompanyContext(id=None, name="Target", website=None))
    assert isinstance(provider, DummyProvider)


@pytest.mark.asyncio
async def test_registry_falls_back_to_default():
    registry = NewsScraperRegistry()
    provider = registry.get_provider(CompanyContext(id=None, name="Other", website=None))
    # Default provider is UniversalScraperProvider
    assert provider.__class__.__name__ == "UniversalScraperProvider"


@pytest.mark.asyncio
async def test_registry_builtin_providers():
    registry = NewsScraperRegistry()
    provider = registry.get_provider(CompanyContext(id=None, name="OpenAI", website=None))
    assert provider.__class__.__name__ == "AINewsScraperProvider"

