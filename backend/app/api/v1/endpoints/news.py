"""
Enhanced News endpoints with improved error handling and validation
"""

from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_news_facade, get_current_user_optional, get_current_user
from app.domains.news import NewsFacade
from app.models.news import (
    NewsCategory,
    SourceType,
    NewsItem,
    NewsSearchSchema,
    NewsStatsSchema,
    NewsCreateSchema,
    NewsUpdateSchema,
)
from app.models.preferences import UserPreferences
from app.models import User, Company
from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.core.access_control import get_user_company_ids, check_company_access, check_news_access
from app.api.dependencies import get_personalization_service
from app.core.personalization import PersonalizationService

router = APIRouter(prefix="/news", tags=["news"])


def serialize_news_item(
    item: NewsItem,
    *,
    include_company: bool = True,
    include_keywords: bool = True,
    include_activities: bool = False,
) -> Dict[str, Any]:
    title = item.title or ""
    title_truncated = title[:100] + "..." if len(title) > 100 else title

    def serialize_company() -> Optional[Dict[str, Any]]:
        company = getattr(item, "company", None)
        if not include_company or not company:
            return None
        return {
            "id": str(company.id) if company.id else None,
            "name": company.name or "",
            "website": company.website or "",
            "description": company.description or "",
            "category": company.category or "",
            "logo_url": getattr(company, "logo_url", None),
        }

    def serialize_keywords() -> List[Dict[str, Any]]:
        if not include_keywords:
            return []
        keywords = getattr(item, "keywords", None)
        if not keywords:
            return []
        return [
            {
                "keyword": kw.keyword or "",
                "relevance": float(kw.relevance_score) if kw.relevance_score else 0.0,
            }
            for kw in keywords
        ]

    def serialize_activities() -> List[Dict[str, Any]]:
        if not include_activities:
            return []
        activities = getattr(item, "activities", None)
        if not activities:
            return []
        return [
            {
                "id": str(activity.id),
                "user_id": str(activity.user_id),
                "activity_type": activity.activity_type,
                "created_at": activity.created_at.isoformat()
                if activity.created_at
                else None,
            }
            for activity in activities
        ]

    def enum_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        return value.value if hasattr(value, "value") else str(value)

    return {
        "id": str(item.id),
        "title": item.title or "",
        "title_truncated": title_truncated,
        "summary": item.summary or "",
        "content": item.content or "",
        "source_url": item.source_url,
        "source_type": enum_value(item.source_type),
        "category": enum_value(item.category),
        "topic": enum_value(item.topic),
        "sentiment": enum_value(item.sentiment),
        "raw_snapshot_url": item.raw_snapshot_url,
        "priority_score": float(item.priority_score)
        if item.priority_score is not None
        else 0.0,
        "priority_level": getattr(item, "priority_level", None),
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "is_recent": getattr(item, "is_recent", False),
        "company": serialize_company(),
        "keywords": serialize_keywords(),
        "activities": serialize_activities(),
    }


@router.post(
    "/",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def create_news(
    payload: NewsCreateSchema,
    facade: NewsFacade = Depends(get_news_facade),
):
    logger.info("Create news request")
    try:
        news_item = await facade.create_news(payload.model_dump())
        return serialize_news_item(news_item, include_activities=True)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {exc.message}",
        )
    except Exception as exc:
        logger.error(f"Failed to create news: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create news item",
        )


@router.put(
    "/{news_id}",
    response_model=Dict[str, Any],
)
async def update_news(
    news_id: str,
    payload: NewsUpdateSchema,
    current_user: User = Depends(get_current_user),
    facade: NewsFacade = Depends(get_news_facade),
    db: AsyncSession = Depends(get_db),
):
    """
    Update news item by ID.
    
    For authenticated users, checks that the news item belongs to their companies (user_id).
    """
    logger.info(f"Update news request: {news_id}, user: {current_user.id}")
    try:
        UUID(news_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid news ID format")

    # СНАЧАЛА ПРОВЕРЯЕМ ДОСТУП (по user_id компании, НЕ по subscribed_companies!)
    news_item = await check_news_access(news_id, current_user, db)
    if not news_item:
        # Всегда возвращаем 404 для недоступных ресурсов (безопасность)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"News item with ID {news_id} not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    try:
        # ТОЛЬКО ПОСЛЕ ПРОВЕРКИ ОБНОВЛЯЕМ
        news_item = await facade.update_news(news_id, update_data)
        if not news_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"News item with ID {news_id} not found",
            )
        return serialize_news_item(news_item, include_activities=True)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update news {news_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update news item",
        )


@router.delete(
    "/{news_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_news(
    news_id: str,
    current_user: User = Depends(get_current_user),
    facade: NewsFacade = Depends(get_news_facade),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete news item by ID.
    
    For authenticated users, checks that the news item belongs to their companies (user_id).
    """
    logger.info(f"Delete news request: {news_id}, user: {current_user.id}")
    try:
        UUID(news_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid news ID format")

    # СНАЧАЛА ПРОВЕРЯЕМ ДОСТУП (по user_id компании, НЕ по subscribed_companies!)
    news_item = await check_news_access(news_id, current_user, db)
    if not news_item:
        # Всегда возвращаем 404 для недоступных ресурсов (безопасность)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"News item with ID {news_id} not found",
        )

    try:
        # ТОЛЬКО ПОСЛЕ ПРОВЕРКИ УДАЛЯЕМ
        success = await facade.delete_news(news_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"News item with ID {news_id} not found",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to delete news {news_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete news item",
        )


@router.get("/", response_model=Dict[str, Any])
@router.get("", response_model=Dict[str, Any], include_in_schema=False)
async def get_news(
    category: Optional[NewsCategory] = Query(None, description="Filter by news category"),
    company_id: Optional[str] = Query(None, description="Filter by single company ID"),
    company_ids: Optional[str] = Query(None, description="Filter by multiple company IDs (comma-separated)"),
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    search_query: Optional[str] = Query(None, description="Search query for title/content"),
    min_priority: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum priority score"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items to return"),
    offset: int = Query(0, ge=0, description="Number of news items to skip"),
    facade: NewsFacade = Depends(get_news_facade),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    personalization: PersonalizationService = Depends(get_personalization_service),
):
    """
    Get news items with enhanced filtering and search capabilities
    
    Returns paginated list of news items with comprehensive filtering options.
    Automatically filters by user's companies if authenticated and no company IDs provided.
    """
    logger.info(f"News request: category={category}, company_id={company_id}, source_type={source_type}, limit={limit}, offset={offset}")
    
    try:
        # Parse company IDs from query parameters using PersonalizationService
        parsed_company_ids, normalised_company_id = await personalization.parse_company_ids_from_query(
            company_ids=company_ids,
            company_id=company_id
        )
        
        # Get company IDs for filtering (applies personalization if needed)
        filter_company_ids = await personalization.get_filter_company_ids(
            user=current_user,
            provided_ids=parsed_company_ids
        )
        
        # Log personalization
        if current_user:
            if parsed_company_ids:
                logger.info(
                    f"User {current_user.id} explicitly specified {len(parsed_company_ids)} company IDs"
                )
            elif filter_company_ids:
                logger.info(
                    f"Auto-filtering news by {len(filter_company_ids)} user companies "
                    f"for user {current_user.id} (company_ids: {[str(cid) for cid in filter_company_ids[:5]]}...)"
                )
            elif filter_company_ids == []:
                logger.warning(
                    f"User {current_user.id} has no companies, returning empty news list"
                )
            else:
                logger.info(
                    f"User {current_user.id} - no filtering (filter_company_ids={filter_company_ids})"
                )
        
        # КРИТИЧЕСКИ ВАЖНО: если filter_company_ids пустой список (пользователь без компаний),
        # возвращаем пустой результат БЕЗ запроса к БД
        if personalization.should_return_empty(filter_company_ids):
            logger.info(f"User {current_user.id if current_user else 'anonymous'} has no companies, returning empty news list")
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "filters": {
                    "category": category.value if category and hasattr(category, 'value') else None,
                    "company_id": company_id,
                    "source_type": source_type.value if source_type and hasattr(source_type, 'value') else None,
                    "search_query": search_query,
                    "min_priority": min_priority
                }
            }
        
        # УПРОЩЕННАЯ ЛОГИКА: Всегда используем user_id для базовой персонализации
        # company_ids используется как дополнительный фильтр (пересечение)
        final_company_id = None
        final_company_ids = None
        final_user_id = None
        
        if current_user:
            # Аутентифицированный пользователь - всегда используем user_id для оптимизированного JOIN
            final_user_id = str(current_user.id)
            
            # Если передан company_ids - используем как дополнительный фильтр (пересечение)
            if filter_company_ids:
                # Валидация: проверяем что все ID валидные UUID
                valid_ids = [cid for cid in filter_company_ids if isinstance(cid, UUID)]
                if len(valid_ids) != len(filter_company_ids):
                    logger.warning(
                        f"Some company IDs are invalid. Valid: {len(valid_ids)}, Total: {len(filter_company_ids)}"
                    )
                
                if len(valid_ids) == 1:
                    # Single company ID case
                    final_company_id = str(valid_ids[0])
                    final_company_ids = None
                    logger.info(f"Using user_id={final_user_id} + company_id={final_company_id} filter")
                elif len(valid_ids) > 1:
                    # Multiple IDs - конвертируем UUID в строки
                    final_company_ids = [str(cid) for cid in valid_ids]
                    logger.info(f"Using user_id={final_user_id} + company_ids={len(final_company_ids)} companies filter")
                else:
                    # Пустой список после валидации - уже обработано выше
                    logger.warning(f"No valid company IDs after validation for user {current_user.id}")
            else:
                # Нет company_ids - показываем все компании пользователя
                logger.info(f"Using user_id={final_user_id} filter (all user companies)")
        else:
            # Анонимный пользователь - показываем только глобальные компании
            logger.info("Anonymous user - showing only global companies")
            # Не передаем user_id, будет использован стандартный запрос без фильтрации по user_id
        
        news_items, total_count = await facade.list_news(
            category=category,
            company_id=final_company_id,
            company_ids=final_company_ids,
            user_id=final_user_id,  # Передаем user_id для оптимизированного JOIN
            include_global_companies=False,  # КРИТИЧЕСКИ ВАЖНО: Персонализация - только компании пользователя, БЕЗ глобальных
            source_type=source_type,
            search_query=search_query,
            min_priority=min_priority,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format with enhanced data
        items = [
            serialize_news_item(item, include_activities=False)
            for item in news_items
        ]
        
        return {
            "items": items,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total_count,
            "filters": {
                "category": category.value if category and hasattr(category, 'value') else None,
                "company_id": company_id,
                "source_type": source_type.value if source_type and hasattr(source_type, 'value') else None,
                "search_query": search_query,
                "min_priority": min_priority
            }
        }
        
    except ValidationError as e:
        logger.warning(f"Validation error in news request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request parameters: {e.message}"
        )
    except Exception as e:
        logger.error(f"Failed to get news: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news items"
        )


@router.get("/stats", response_model=NewsStatsSchema)
async def get_news_statistics(
    facade: NewsFacade = Depends(get_news_facade),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive news statistics
    
    For authenticated users, automatically filters by user_id companies.
    For anonymous users, returns statistics for all news.
    
    Returns statistics about news items including counts by category,
    source type, recent news, and high priority items.
    """
    logger.info(f"News statistics request - user: {current_user.id if current_user else 'anonymous'}")
    
    try:
        # Automatic isolation: if user is authenticated, filter by user_id companies
        if current_user:
            try:
                # ПРАВИЛЬНО: фильтруем по user_id компаний
                user_company_ids = await get_user_company_ids(current_user, db)
                logger.info(
                    f"User {current_user.id} - Companies found: {len(user_company_ids)}"
                )
                logger.debug(
                    f"User {current_user.id} - Company IDs: {[str(cid) for cid in user_company_ids]}"
                )
                
                if user_company_ids:
                    # Валидация: проверяем что все ID валидные UUID
                    valid_ids = [cid for cid in user_company_ids if isinstance(cid, UUID)]
                    if len(valid_ids) != len(user_company_ids):
                        logger.warning(
                            f"Some company IDs are invalid for user {current_user.id}. "
                            f"Valid: {len(valid_ids)}, Total: {len(user_company_ids)}"
                        )
                    
                    if not valid_ids:
                        logger.warning(
                            f"No valid company IDs for user {current_user.id}, returning empty statistics"
                        )
                        return NewsStatsSchema(
                            total_count=0,
                            category_counts={},
                            source_type_counts={},
                            recent_count=0,
                            high_priority_count=0
                        )
                    
                    # Filter statistics by user companies for data isolation
                    company_ids_str = [str(cid) for cid in valid_ids]
                    logger.info(
                        f"Filtering stats by {len(company_ids_str)} companies: {company_ids_str[:5]}..."
                    )
                    stats = await facade.get_statistics_for_companies(company_ids_str)
                    logger.info(
                        f"Statistics result for user {current_user.id}: "
                        f"total_count={stats.total_count}, "
                        f"recent_count={stats.recent_count}, "
                        f"high_priority_count={stats.high_priority_count}, "
                        f"categories={len(stats.category_counts)}, "
                        f"sources={len(stats.source_type_counts)}"
                    )
                    return stats
                else:
                    # КРИТИЧЕСКИ ВАЖНО: если у пользователя нет компаний, возвращаем пустую статистику
                    logger.info(
                        f"User {current_user.id} has no companies, returning empty statistics"
                    )
                    # Return empty statistics structure
                    return NewsStatsSchema(
                        total_count=0,
                        category_counts={},
                        source_type_counts={},
                        recent_count=0,
                        high_priority_count=0
                    )
            except Exception as e:
                logger.warning(f"Failed to get user companies for stats filtering: {e}")
                # Return empty statistics on error to prevent showing all statistics
                return NewsStatsSchema(
                    total_count=0,
                    category_counts={},
                    source_type_counts={},
                    recent_count=0,
                    high_priority_count=0
                )
        
        # For anonymous users, return general statistics
        stats = await facade.get_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get news statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news statistics"
        )


@router.get("/stats/by-companies", response_model=NewsStatsSchema)
async def get_news_statistics_by_companies(
    company_ids: str = Query(..., description="Comma-separated company IDs"),
    facade: NewsFacade = Depends(get_news_facade),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive news statistics filtered by company IDs
    
    For authenticated users, validates that all requested companies either:
    - Belong to user (user_id = current_user.id or user_id = null for global companies), OR
    - Are in the user's subscribed_companies list
    
    Returns statistics about news items for specific companies including counts by category,
    source type, recent news, and high priority items.
    """
    logger.info(f"News statistics by companies request: {company_ids}, user: {current_user.id if current_user else 'anonymous'}")
    
    try:
        # Parse company IDs
        parsed_company_ids = [cid.strip() for cid in company_ids.split(',') if cid.strip()]
        
        if not parsed_company_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one company ID is required"
            )
        
        # For authenticated users, validate that all requested companies belong to user (user_id) OR are in subscribed_companies
        if current_user:
            try:
                # Get user preferences to check subscribed_companies
                user_prefs_result = await db.execute(
                    select(UserPreferences).where(UserPreferences.user_id == current_user.id)
                )
                user_prefs = user_prefs_result.scalar_one_or_none()
                subscribed_company_ids = set()
                if user_prefs and user_prefs.subscribed_companies:
                    # Convert to UUID strings for comparison
                    subscribed_company_ids = {str(cid) for cid in user_prefs.subscribed_companies}
                
                unauthorized_ids = []
                for cid in parsed_company_ids:
                    if cid:
                        try:
                            # Check if company belongs to user (user_id) OR is in subscribed_companies
                            company = await check_company_access(cid, current_user, db)
                            if not company:
                                # If not accessible via user_id, check if it's in subscribed_companies
                                if cid in subscribed_company_ids:
                                    # Verify the company exists (even if it doesn't belong to user)
                                    try:
                                        company_uuid = UUID(cid)
                                        company_result = await db.execute(
                                            select(Company).where(Company.id == company_uuid)
                                        )
                                        company = company_result.scalar_one_or_none()
                                        if not company:
                                            unauthorized_ids.append(cid)
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Invalid company ID format: {cid}, error: {e}")
                                        unauthorized_ids.append(cid)
                                else:
                                    unauthorized_ids.append(cid)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid company ID format: {cid}, error: {e}")
                            unauthorized_ids.append(cid)
                
                if unauthorized_ids:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied: You don't have access to some of the requested companies. "
                               f"Unauthorized company IDs: {unauthorized_ids}"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Failed to validate company access for stats: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to validate company access"
                )
        
        stats = await facade.get_statistics_for_companies(parsed_company_ids)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get news statistics by companies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news statistics by companies"
        )


@router.get("/search", response_model=Dict[str, Any])
async def search_news(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[NewsCategory] = Query(None, description="Filter by category"),
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    facade: NewsFacade = Depends(get_news_facade),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    personalization: PersonalizationService = Depends(get_personalization_service),
):
    """
    Search news items with advanced filtering

    Performs full-text search across news titles, content, and summaries
    with optional filtering by category, source type, and company.
    
    For authenticated users, automatically filters by user_id companies.
    """
    logger.info(f"News search: query='{q}', category={category}, limit={limit}, offset={offset}, user={current_user.id if current_user else 'anonymous'}")
    
    try:
        # Parse company ID from query parameter using PersonalizationService
        parsed_company_ids, normalised_company_id = await personalization.parse_company_ids_from_query(
            company_id=company_id
        )
        
        # Get company IDs for filtering (applies personalization if needed)
        filter_company_ids = await personalization.get_filter_company_ids(
            user=current_user,
            provided_ids=parsed_company_ids
        )
        
        # Log personalization
        if current_user and not parsed_company_ids:
            if filter_company_ids:
                logger.info(
                    f"Auto-filtering search by {len(filter_company_ids)} user companies "
                    f"for user {current_user.id}"
                )
            else:
                logger.info(
                    f"User {current_user.id} has no companies, returning empty search results"
                )
        
        # КРИТИЧЕСКИ ВАЖНО: если filter_company_ids пустой список (пользователь без компаний),
        # возвращаем пустой результат БЕЗ запроса к БД
        if personalization.should_return_empty(filter_company_ids):
            logger.info(f"User {current_user.id if current_user else 'anonymous'} has no companies, returning empty search results")
            return {
                "query": q,
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "filters": {
                    "category": category.value if category else None,
                    "source_type": source_type.value if source_type else None,
                    "company_id": company_id
                }
            }
        
        # УПРОЩЕННАЯ ЛОГИКА: Используем list_news с user_id и search_query для SQL-фильтрации
        # Это эффективнее чем in-memory фильтрация
        final_company_id = None
        final_company_ids = None
        final_user_id = None
        
        if current_user:
            # Аутентифицированный пользователь - всегда используем user_id для оптимизированного JOIN
            final_user_id = str(current_user.id)
            
            # Если передан company_ids - используем как дополнительный фильтр (пересечение)
            if filter_company_ids:
                # Валидация: проверяем что все ID валидные UUID
                valid_ids = [cid for cid in filter_company_ids if isinstance(cid, UUID)]
                if len(valid_ids) != len(filter_company_ids):
                    logger.warning(
                        f"Some company IDs are invalid. Valid: {len(valid_ids)}, Total: {len(filter_company_ids)}"
                    )
                
                if len(valid_ids) == 1:
                    # Single company ID case
                    final_company_id = str(valid_ids[0])
                    final_company_ids = None
                    logger.info(f"Search with user_id={final_user_id} + company_id={final_company_id}")
                elif len(valid_ids) > 1:
                    # Multiple IDs - конвертируем UUID в строки
                    final_company_ids = [str(cid) for cid in valid_ids]
                    logger.info(f"Search with user_id={final_user_id} + company_ids={len(final_company_ids)} companies")
                else:
                    # Пустой список после валидации - уже обработано выше
                    logger.warning(f"No valid company IDs after validation for user {current_user.id}")
            else:
                # Нет company_ids - показываем все компании пользователя
                logger.info(f"Search with user_id={final_user_id} (all user companies)")
        else:
            # Анонимный пользователь - показываем только глобальные компании
            logger.info("Anonymous user search - showing only global companies")
        
        # Используем list_news с search_query для SQL-фильтрации (не in-memory!)
        news_items, total_count = await facade.list_news(
            category=category,
            company_id=final_company_id,
            company_ids=final_company_ids,
            user_id=final_user_id,  # Передаем user_id для оптимизированного JOIN
            include_global_companies=False,  # КРИТИЧЕСКИ ВАЖНО: Персонализация - только компании пользователя, БЕЗ глобальных
            source_type=source_type,
            search_query=q,  # Поиск на уровне SQL
            min_priority=None,
            limit=limit,
            offset=offset
        )

        # Convert to response format
        items = [
            serialize_news_item(item, include_activities=False)
            for item in news_items
        ]

        return {
            "query": q,
            "items": items,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total_count,
            "filters": {
                "category": category.value if category else None,
                "source_type": source_type.value if source_type else None,
                "company_id": company_id
            }
        }

    except ValidationError as e:
        logger.warning(f"Validation error in news search: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search parameters: {e.message}"
        )
    except Exception as e:
        logger.error(f"Failed to search news: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search news items"
        )


@router.get("/{news_id}", response_model=Dict[str, Any])
async def get_news_item(
    news_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    facade: NewsFacade = Depends(get_news_facade),
    db: AsyncSession = Depends(get_db),
):
    """
    Get specific news item by ID with full details
    
    Returns detailed information about a specific news item including
    related company information, keywords, and user activities.
    
    For authenticated users, checks that the news item belongs to their companies (user_id).
    """
    logger.info(f"News item request: {news_id}, user: {current_user.id if current_user else 'anonymous'}")
    
    try:
        try:
            UUID(news_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid news ID format",
            )

        # Проверка доступа: для авторизованных пользователей проверяем, что новость принадлежит их компаниям
        if current_user:
            news_item = await check_news_access(news_id, current_user, db)
            if not news_item:
                # Всегда возвращаем 404 для недоступных ресурсов (безопасность)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"News item with ID {news_id} not found",
                )
        else:
            # Для анонимных пользователей получаем новость без проверки доступа
            # (но это должно быть только для глобальных компаний)
            news_item = await facade.get_news_item(news_id, include_relations=True)
            if not news_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"News item with ID {news_id} not found",
                )
        
        # Build comprehensive response
        company_info = None
        if news_item.company:
            company_info = {
                "id": str(news_item.company.id),
                "name": news_item.company.name,
                "website": news_item.company.website,
                "description": news_item.company.description,
                "category": news_item.company.category,
                "logo_url": news_item.company.logo_url
            }
        
        # Build keywords with relevance scores
        keywords = []
        if news_item.keywords:
            keywords = [
                {
                    "keyword": kw.keyword,
                    "relevance": kw.relevance_score
                }
                for kw in news_item.keywords
            ]
        
        # Build user activities
        activities = []
        if news_item.activities:
            activities = [
                {
                    "id": str(activity.id),
                    "user_id": str(activity.user_id),
                    "activity_type": activity.activity_type,
                    "created_at": activity.created_at.isoformat() if activity.created_at else None
                }
                for activity in news_item.activities
            ]
        
        return serialize_news_item(
            news_item,
            include_activities=True,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get news item {news_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news item"
        )


@router.get("/category/{category_name}", response_model=Dict[str, Any])
async def get_news_by_category(
    category_name: str,
    company_id: Optional[str] = Query(None, description="Filter by single company ID"),
    company_ids: Optional[str] = Query(None, description="Filter by multiple company IDs (comma-separated)"),
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items to return"),
    offset: int = Query(0, ge=0, description="Number of news items to skip"),
    facade: NewsFacade = Depends(get_news_facade),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    personalization: PersonalizationService = Depends(get_personalization_service),
):
    """
    Get news items by category with statistics
    
    Returns paginated list of news items for a specific category along with
    statistics about top companies and source distribution.
    
    For authenticated users, automatically filters by user_id companies.
    """
    logger.info(f"News by category request: category={category_name}, company_id={company_id}, source_type={source_type}, limit={limit}, offset={offset}, user={current_user.id if current_user else 'anonymous'}")
    
    try:
        # Validate category name
        valid_categories = [cat.value for cat in NewsCategory]
        if category_name not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Valid categories are: {', '.join(valid_categories)}"
            )
        
        # Convert string to enum
        category_enum = NewsCategory(category_name)
        
        # Parse company IDs from query parameters using PersonalizationService
        parsed_company_ids, normalised_company_id = await personalization.parse_company_ids_from_query(
            company_ids=company_ids,
            company_id=company_id
        )
        
        # Get company IDs for filtering (applies personalization if needed)
        filter_company_ids = await personalization.get_filter_company_ids(
            user=current_user,
            provided_ids=parsed_company_ids
        )
        
        # Log personalization
        if current_user and not parsed_company_ids:
            if filter_company_ids:
                logger.info(
                    f"Auto-filtering category news by {len(filter_company_ids)} user companies "
                    f"for user {current_user.id}"
                )
            else:
                logger.info(
                    f"User {current_user.id} has no companies, returning empty category news"
                )
        
        # КРИТИЧЕСКИ ВАЖНО: если filter_company_ids пустой список (пользователь без компаний),
        # возвращаем пустой результат БЕЗ запроса к БД
        if personalization.should_return_empty(filter_company_ids):
            logger.info(f"User {current_user.id if current_user else 'anonymous'} has no companies, returning empty category news")
            return {
                "category": category_name,
                "category_description": NewsCategory.get_descriptions().get(category_enum),
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "statistics": {
                    "top_companies": [],
                    "source_distribution": {},
                    "total_in_category": 0
                },
                "filters": {
                    "company_id": company_id,
                    "source_type": (source_type.value if hasattr(source_type, 'value') else str(source_type)) if source_type else None
                }
            }
        
        # УПРОЩЕННАЯ ЛОГИКА: Всегда используем user_id для базовой персонализации
        # company_ids используется как дополнительный фильтр (пересечение)
        final_company_id = None
        final_company_ids = None
        final_user_id = None
        
        if current_user:
            # Аутентифицированный пользователь - всегда используем user_id для оптимизированного JOIN
            final_user_id = str(current_user.id)
            
            # Если передан company_ids - используем как дополнительный фильтр (пересечение)
            if filter_company_ids:
                # Валидация: проверяем что все ID валидные UUID
                valid_ids = [cid for cid in filter_company_ids if isinstance(cid, UUID)]
                if len(valid_ids) != len(filter_company_ids):
                    logger.warning(
                        f"Some company IDs are invalid. Valid: {len(valid_ids)}, Total: {len(filter_company_ids)}"
                    )
                
                if len(valid_ids) == 1:
                    # Single company ID case
                    final_company_id = str(valid_ids[0])
                    final_company_ids = None
                    logger.info(f"Category news with user_id={final_user_id} + company_id={final_company_id} filter")
                elif len(valid_ids) > 1:
                    # Multiple IDs - конвертируем UUID в строки
                    final_company_ids = [str(cid) for cid in valid_ids]
                    logger.info(f"Category news with user_id={final_user_id} + company_ids={len(final_company_ids)} companies filter")
                else:
                    # Пустой список после валидации - уже обработано выше
                    logger.warning(f"No valid company IDs after validation for user {current_user.id}")
            else:
                # Нет company_ids - показываем все компании пользователя
                logger.info(f"Category news with user_id={final_user_id} filter (all user companies)")
        else:
            # Анонимный пользователь - показываем только глобальные компании
            logger.info("Anonymous user category news - showing only global companies")
            # Не передаем user_id, будет использован стандартный запрос без фильтрации по user_id
        
        news_items, total_count = await facade.list_news(
            category=category_enum,
            company_id=final_company_id,
            company_ids=final_company_ids,
            user_id=final_user_id,  # Передаем user_id для оптимизированного JOIN
            include_global_companies=False,  # КРИТИЧЕСКИ ВАЖНО: Персонализация - только компании пользователя, БЕЗ глобальных
            source_type=source_type,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        items = [
            serialize_news_item(item, include_activities=False)
            for item in news_items
        ]
        
        # Get statistics for this category
        category_stats = await facade.get_category_statistics(category_enum, filter_company_ids)
        
        return {
            "category": category_name,
            "category_description": NewsCategory.get_descriptions().get(category_enum),
            "items": items,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total_count,
            "statistics": {
                "top_companies": category_stats.get("top_companies", []),
                "source_distribution": category_stats.get("source_distribution", {}),
                "total_in_category": category_stats.get("total_in_category", 0)
            },
            "filters": {
                "company_id": company_id,
                "source_type": (source_type.value if hasattr(source_type, 'value') else str(source_type)) if source_type else None
            }
        }
        
    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning(f"Validation error in category news request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request parameters: {e.message}"
        )
    except Exception as e:
        logger.error(f"Failed to get news by category {category_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news by category"
        )


@router.get("/categories/list")
async def get_news_categories():
    """
    Get available news categories with descriptions
    
    Returns list of all available news categories with their descriptions.
    """
    logger.info("News categories list request")
    
    try:
        categories = NewsCategory.get_descriptions()
        source_types = SourceType.get_descriptions()
        
        return {
            "categories": [
                {"value": category.value, "description": description}
                for category, description in categories.items()
            ],
            "source_types": [
                {"value": source_type.value, "description": description}
                for source_type, description in source_types.items()
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )


@router.post("/{news_id}/mark-read")
async def mark_news_read(news_id: str):
    logger.info(f"Mark news as read (stub): {news_id}")
    return {"message": "Not implemented", "news_id": news_id}


@router.post("/{news_id}/favorite")
async def favorite_news(news_id: str):
    logger.info(f"Favorite news (stub): {news_id}")
    return {"message": "Not implemented", "news_id": news_id}
