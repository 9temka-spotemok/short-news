from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.repositories.company_repository import CompanyRepository
from app.models import Company


@pytest.mark.asyncio
async def test_fetch_by_name_returns_company(async_session: AsyncSession) -> None:
    repo = CompanyRepository(async_session)
    company = Company(name="OpenAI", website="https://openai.com")
    async_session.add(company)
    await async_session.commit()

    result = await repo.fetch_by_name("OpenAI")

    assert result is not None
    assert result.id == company.id


@pytest.mark.asyncio
async def test_fetch_by_name_supports_partial_match(async_session: AsyncSession) -> None:
    repo = CompanyRepository(async_session)
    openai = Company(name="OpenAI Research")
    other = Company(name="Anthropic")
    async_session.add_all([openai, other])
    await async_session.commit()

    result = await repo.fetch_by_name("research")

    assert result is not None
    assert result.id == openai.id


@pytest.mark.asyncio
async def test_fetch_by_name_returns_none_for_unknown(async_session: AsyncSession) -> None:
    repo = CompanyRepository(async_session)
    async_session.add(Company(name="Existing"))
    await async_session.commit()

    result = await repo.fetch_by_name("missing")

    assert result is None




