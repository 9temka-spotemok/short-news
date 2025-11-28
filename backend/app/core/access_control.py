"""
Centralized access control functions for personalization.

КРИТИЧЕСКИ ВАЖНО: Персонализация основана на user_id компаний, 
а НЕ на subscribed_companies!
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models import User, Company, NewsItem

# In-memory cache for user company IDs
# Format: {user_id: (company_ids, expiry_time)}
_user_company_cache: dict[UUID, tuple[list[UUID], datetime]] = {}
_cache_ttl_seconds = 300  # 5 minutes


def invalidate_user_cache(user_id: UUID) -> None:
    """
    Invalidate cache for a specific user.
    
    Should be called when user's companies are modified (created, updated, deleted).
    
    Args:
        user_id: User UUID whose cache should be invalidated
    """
    # КРИТИЧЕСКИ ВАЖНО: Конвертируем в стандартный UUID для работы с кешем
    try:
        user_id_uuid = UUID(str(user_id))
        _user_company_cache.pop(user_id_uuid, None)
    except (ValueError, TypeError):
        pass  # Игнорируем невалидные UUID


def _clean_expired_cache() -> None:
    """Remove expired entries from cache."""
    now = datetime.now()
    expired_keys = []
    for user_id, (_, expiry) in _user_company_cache.items():
        if expiry < now:
            expired_keys.append(user_id)
    for key in expired_keys:
        _user_company_cache.pop(key, None)


async def check_company_access(
    company_id: UUID | str,
    user: Optional[User],
    db: AsyncSession
) -> Optional[Company]:
    """
    Check if user has access to company and return it.
    Проверяет доступ по user_id компании (НЕ по subscribed_companies!).
    
    Args:
        company_id: Company UUID or string
        user: Current user (None for anonymous)
        db: Database session
        
    Returns:
        Company if accessible, None otherwise
    """
    if isinstance(company_id, str):
        try:
            company_id = UUID(company_id)
        except ValueError:
            return None
    
    query = select(Company).where(Company.id == company_id)
    
    if user:
        # КРИТИЧЕСКИ ВАЖНО: Конвертируем user.id в стандартный UUID
        try:
            user_id_uuid = UUID(str(user.id))
        except (ValueError, TypeError):
            # Если не удалось конвертировать, разрешаем только глобальные компании
            query = query.where(Company.user_id.is_(None))
        else:
            query = query.where(
                or_(
                    Company.user_id == user_id_uuid,
                    Company.user_id.is_(None)  # Global companies
                )
            )
    else:
        query = query.where(Company.user_id.is_(None))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def check_news_access(
    news_id: UUID | str,
    user: Optional[User],
    db: AsyncSession
) -> Optional[NewsItem]:
    """
    Check if user has access to news item and return it.
    Проверяет доступ по user_id компании новости (НЕ по subscribed_companies!).
    
    Оптимизированная версия с одним запросом через join вместо двух запросов.
    
    Args:
        news_id: News UUID or string
        user: Current user (None for anonymous)
        db: Database session
        
    Returns:
        NewsItem if accessible, None otherwise
    """
    if isinstance(news_id, str):
        try:
            news_id = UUID(news_id)
        except ValueError:
            return None
    
    # Single query with join instead of two separate queries
    query = select(NewsItem).join(Company).where(NewsItem.id == news_id)
    
    if user:
        # КРИТИЧЕСКИ ВАЖНО: Конвертируем user.id в стандартный UUID
        try:
            user_id_uuid = UUID(str(user.id))
        except (ValueError, TypeError):
            # Если не удалось конвертировать, разрешаем только глобальные компании
            query = query.where(Company.user_id.is_(None))
        else:
            # Filter by user's companies or global companies
            query = query.where(
                or_(
                    Company.user_id == user_id_uuid,
                    Company.user_id.is_(None)  # Global companies
                )
            )
    else:
        # Anonymous users can only access global companies
        query = query.where(Company.user_id.is_(None))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_company_ids(
    user: User,
    db: AsyncSession
) -> list[UUID]:
    """
    Get all company IDs that belong to user.
    Получает все ID компаний, принадлежащих пользователю (user_id = user.id).
    
    Uses in-memory cache with TTL (5 minutes) to reduce database queries.
    
    Args:
        user: Current user
        db: Database session
        
    Returns:
        List of company UUIDs
    """
    # КРИТИЧЕСКИ ВАЖНО: Конвертируем user.id в стандартный UUID
    # чтобы избежать проблем с asyncpg.pgproto.UUID
    try:
        user_id_uuid = UUID(str(user.id))
    except (ValueError, TypeError):
        # Если не удалось конвертировать, возвращаем пустой список
        return []
    
    # Clean expired cache entries periodically
    _clean_expired_cache()
    
    # Check cache
    now = datetime.now()
    if user_id_uuid in _user_company_cache:
        company_ids, expiry = _user_company_cache[user_id_uuid]
        if expiry > now:
            return company_ids
        # Cache expired, remove it
        _user_company_cache.pop(user_id_uuid)
    
    # Fetch from database
    result = await db.execute(
        select(Company.id).where(Company.user_id == user_id_uuid)
    )
    
    # КРИТИЧЕСКИ ВАЖНО: Конвертируем все company IDs в стандартные UUID
    # чтобы избежать проблем с asyncpg.pgproto.UUID
    company_ids = []
    for c in result.scalars().all():
        try:
            company_id_uuid = UUID(str(c.id)) if hasattr(c, 'id') else UUID(str(c))
            company_ids.append(company_id_uuid)
        except (ValueError, TypeError):
            continue  # Пропускаем невалидные UUID
    
    # Store in cache
    expiry_time = now + timedelta(seconds=_cache_ttl_seconds)
    _user_company_cache[user_id_uuid] = (company_ids, expiry_time)
    
    return company_ids

