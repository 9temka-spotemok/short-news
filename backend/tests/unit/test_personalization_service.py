"""
Unit tests for PersonalizationService.

Tests for:
- get_filter_company_ids()
- should_return_empty()
- parse_company_ids_from_query()
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.personalization import PersonalizationService
from app.models import Company, User


@pytest.mark.asyncio
async def test_get_filter_company_ids_with_provided_ids(
    async_session: AsyncSession,
) -> None:
    """Test that provided IDs are used when explicitly given."""
    service = PersonalizationService(async_session)
    
    # Create some UUIDs
    provided_ids = [uuid4(), uuid4()]
    
    # Create user (but we should use provided_ids)
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    result = await service.get_filter_company_ids(user, provided_ids=provided_ids)
    
    assert result == provided_ids


@pytest.mark.asyncio
async def test_get_filter_company_ids_user_with_companies(
    async_session: AsyncSession,
) -> None:
    """Test that user's companies are returned when no IDs provided."""
    service = PersonalizationService(async_session)
    
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Create companies for user
    company1 = Company(
        name="Company 1",
        website="https://company1.com",
        user_id=user.id,
    )
    company2 = Company(
        name="Company 2",
        website="https://company2.com",
        user_id=user.id,
    )
    async_session.add(company1)
    async_session.add(company2)
    await async_session.commit()
    await async_session.refresh(company1)
    await async_session.refresh(company2)
    
    result = await service.get_filter_company_ids(user, provided_ids=None)
    
    assert result is not None
    assert len(result) == 2
    assert company1.id in result
    assert company2.id in result


@pytest.mark.asyncio
async def test_get_filter_company_ids_user_without_companies(
    async_session: AsyncSession,
) -> None:
    """Test that empty list is returned for user with no companies."""
    service = PersonalizationService(async_session)
    
    # Create user without companies
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    result = await service.get_filter_company_ids(user, provided_ids=None)
    
    assert result == []


@pytest.mark.asyncio
async def test_get_filter_company_ids_anonymous_user(
    async_session: AsyncSession,
) -> None:
    """Test that None is returned for anonymous user."""
    service = PersonalizationService(async_session)
    
    result = await service.get_filter_company_ids(None, provided_ids=None)
    
    assert result is None


@pytest.mark.asyncio
async def test_get_filter_company_ids_anonymous_with_provided_ids(
    async_session: AsyncSession,
) -> None:
    """Test that provided IDs are used even for anonymous user."""
    service = PersonalizationService(async_session)
    
    provided_ids = [uuid4(), uuid4()]
    
    result = await service.get_filter_company_ids(None, provided_ids=provided_ids)
    
    assert result == provided_ids


@pytest.mark.asyncio
async def test_get_filter_company_ids_error_handling(
    async_session: AsyncSession,
) -> None:
    """Test that errors return empty list to prevent showing all news."""
    service = PersonalizationService(async_session)
    
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Close session to cause error
    await async_session.close()
    
    # Should return empty list on error
    result = await service.get_filter_company_ids(user, provided_ids=None)
    
    assert result == []


@pytest.mark.asyncio
async def test_should_return_empty_with_empty_list(
    async_session: AsyncSession,
) -> None:
    """Test that should_return_empty returns True for empty list."""
    service = PersonalizationService(async_session)
    
    assert service.should_return_empty([]) is True


@pytest.mark.asyncio
async def test_should_return_empty_with_non_empty_list(
    async_session: AsyncSession,
) -> None:
    """Test that should_return_empty returns False for non-empty list."""
    service = PersonalizationService(async_session)
    
    company_ids = [uuid4(), uuid4()]
    assert service.should_return_empty(company_ids) is False


@pytest.mark.asyncio
async def test_should_return_empty_with_none(
    async_session: AsyncSession,
) -> None:
    """Test that should_return_empty returns False for None."""
    service = PersonalizationService(async_session)
    
    assert service.should_return_empty(None) is False


@pytest.mark.asyncio
async def test_parse_company_ids_from_query_with_company_ids(
    async_session: AsyncSession,
) -> None:
    """Test parsing comma-separated company IDs."""
    service = PersonalizationService(async_session)
    
    id1 = uuid4()
    id2 = uuid4()
    company_ids_str = f"{id1},{id2}"
    
    parsed_ids, single_id = await service.parse_company_ids_from_query(
        company_ids=company_ids_str
    )
    
    assert parsed_ids is not None
    assert len(parsed_ids) == 2
    assert id1 in parsed_ids
    assert id2 in parsed_ids
    assert single_id is None  # Multiple IDs, no single ID


@pytest.mark.asyncio
async def test_parse_company_ids_from_query_with_single_company_id(
    async_session: AsyncSession,
) -> None:
    """Test parsing single company ID."""
    service = PersonalizationService(async_session)
    
    id1 = uuid4()
    
    parsed_ids, single_id = await service.parse_company_ids_from_query(
        company_id=str(id1)
    )
    
    assert parsed_ids is not None
    assert len(parsed_ids) == 1
    assert id1 in parsed_ids
    assert single_id == id1


@pytest.mark.asyncio
async def test_parse_company_ids_from_query_with_invalid_uuid(
    async_session: AsyncSession,
) -> None:
    """Test that invalid UUIDs are skipped."""
    service = PersonalizationService(async_session)
    
    id1 = uuid4()
    company_ids_str = f"{id1},invalid-uuid,another-invalid"
    
    parsed_ids, single_id = await service.parse_company_ids_from_query(
        company_ids=company_ids_str
    )
    
    assert parsed_ids is not None
    assert len(parsed_ids) == 1
    assert id1 in parsed_ids
    assert single_id == id1


@pytest.mark.asyncio
async def test_parse_company_ids_from_query_with_all_invalid(
    async_session: AsyncSession,
) -> None:
    """Test that all invalid UUIDs result in None."""
    service = PersonalizationService(async_session)
    
    parsed_ids, single_id = await service.parse_company_ids_from_query(
        company_ids="invalid-uuid,another-invalid"
    )
    
    assert parsed_ids is None
    assert single_id is None


@pytest.mark.asyncio
async def test_parse_company_ids_from_query_with_none(
    async_session: AsyncSession,
) -> None:
    """Test that None parameters return None."""
    service = PersonalizationService(async_session)
    
    parsed_ids, single_id = await service.parse_company_ids_from_query()
    
    assert parsed_ids is None
    assert single_id is None


@pytest.mark.asyncio
async def test_parse_company_ids_from_query_with_empty_string(
    async_session: AsyncSession,
) -> None:
    """Test that empty string returns None."""
    service = PersonalizationService(async_session)
    
    parsed_ids, single_id = await service.parse_company_ids_from_query(
        company_ids=""
    )
    
    assert parsed_ids is None
    assert single_id is None


@pytest.mark.asyncio
async def test_parse_company_ids_from_query_with_whitespace(
    async_session: AsyncSession,
) -> None:
    """Test that whitespace is trimmed."""
    service = PersonalizationService(async_session)
    
    id1 = uuid4()
    id2 = uuid4()
    company_ids_str = f" {id1} , {id2} "
    
    parsed_ids, single_id = await service.parse_company_ids_from_query(
        company_ids=company_ids_str
    )
    
    assert parsed_ids is not None
    assert len(parsed_ids) == 2
    assert id1 in parsed_ids
    assert id2 in parsed_ids




