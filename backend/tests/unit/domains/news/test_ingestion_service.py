from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.domains.news.services.ingestion_service import NewsIngestionService
from app.models import Company, NewsItem
from app.models.news import SourceType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _create_company(session: AsyncSession, name: str) -> Company:
    company = Company(name=name)
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


@pytest.fixture(autouse=True)
def patch_search_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(self: NewsIngestionService, news_item: NewsItem) -> None:
        news_item.search_vector = None

    monkeypatch.setattr(NewsIngestionService, "_update_search_vector", _noop)


@pytest.fixture(autouse=True)
def disable_detail_enrichment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings,
        "SCRAPER_DETAIL_ENRICHMENT_ENABLED",
        False,
        raising=False,
    )


def _payload(**overrides) -> dict:
    data = {
        "title": "Sample news",
        "summary": "Summary",
        "content": "Content",
        "source_url": f"https://example.com/news/{uuid4()}",
        "source_type": SourceType.BLOG.value,
        "published_at": _utc_now().isoformat(),
        "priority_score": 0.6,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_news_item_persists_record(async_session: AsyncSession) -> None:
    service = NewsIngestionService(async_session)
    payload = _payload()

    news_item = await service.create_news_item(payload)

    assert news_item.id is not None
    assert news_item.title == payload["title"]


@pytest.mark.asyncio
async def test_create_news_item_normalizes_published_at(async_session: AsyncSession) -> None:
    service = NewsIngestionService(async_session)
    aware_timestamp = datetime(2024, 3, 14, 9, 26, tzinfo=timezone.utc)
    payload = _payload(published_at=aware_timestamp.isoformat())

    news_item = await service.create_news_item(payload)

    assert news_item.published_at.tzinfo is None
    assert news_item.published_at == aware_timestamp.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_create_news_item_returns_existing_on_duplicate(async_session: AsyncSession) -> None:
    service = NewsIngestionService(async_session)
    payload = _payload()

    first = await service.create_news_item(payload)
    second = await service.create_news_item(payload)

    assert first.id == second.id


@pytest.mark.asyncio
async def test_create_news_item_assigns_company(async_session: AsyncSession) -> None:
    service = NewsIngestionService(async_session)
    company = await _create_company(async_session, "OpenAI")
    payload = _payload(company_id="OpenAI")

    news_item = await service.create_news_item(payload)

    assert news_item.company_id == company.id


@pytest.mark.asyncio
async def test_update_news_item_modifies_fields(async_session: AsyncSession) -> None:
    service = NewsIngestionService(async_session)
    news_item = await service.create_news_item(_payload())

    updated = await service.update_news_item(news_item.id, {"summary": "Updated"})

    assert updated is not None
    assert updated.summary == "Updated"


@pytest.mark.asyncio
async def test_delete_news_item_removes_record(async_session: AsyncSession) -> None:
    service = NewsIngestionService(async_session)
    news_item = await service.create_news_item(_payload())

    deleted = await service.delete_news_item(news_item.id)

    assert deleted is True
    # ensure subsequent fetch returns False
    deleted_again = await service.delete_news_item(news_item.id)
    assert deleted_again is False


@pytest.mark.asyncio
async def test_create_news_item_invalid_payload_raises(async_session: AsyncSession) -> None:
    service = NewsIngestionService(async_session)
    payload = _payload()
    payload.pop("title")

    with pytest.raises(ValidationError):
        await service.create_news_item(payload)


@pytest.mark.asyncio
async def test_create_news_item_enriches_from_detail_page(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = NewsIngestionService(async_session)

    detail_html = """
    <html>
        <head>
            <meta property="og:title" content="Canonical Detail Title" />
            <meta name="description" content="Detailed summary pulled from meta description." />
        </head>
        <body><h1>Fallback H1</h1></body>
    </html>
    """.strip()

    class _StubResponse:
        status_code = 200
        text = detail_html

    class _StubAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "_StubAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
            return False

        async def get(self, url: str) -> _StubResponse:
            return _StubResponse()

    monkeypatch.setattr(
        "app.domains.news.services.ingestion_service.httpx.AsyncClient",
        _StubAsyncClient,
    )
    monkeypatch.setattr(
        settings,
        "SCRAPER_DETAIL_ENRICHMENT_ENABLED",
        True,
        raising=False,
    )

    payload = _payload(
        title="List Title",
        summary="short",
        source_url="https://example.com/detail",
    )

    news_item = await service.create_news_item(payload)

    assert news_item.title == "Canonical Detail Title"
    assert news_item.summary.startswith("Detailed summary pulled from meta description.")



