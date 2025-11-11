from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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


def _payload(**overrides) -> dict:
    data = {
        "title": "Sample news",
        "summary": "Summary",
        "content": "Content",
        "source_url": "https://example.com/news",
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


