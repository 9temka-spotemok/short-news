"""
Enhanced News endpoints with improved error handling and validation
"""

from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_news_facade, get_current_user_optional
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
from app.models import User
from app.core.database import get_db
from app.core.exceptions import ValidationError

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
    facade: NewsFacade = Depends(get_news_facade),
):
    logger.info(f"Update news request: {news_id}")
    try:
        UUID(news_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid news ID format")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    try:
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
    facade: NewsFacade = Depends(get_news_facade),
):
    logger.info(f"Delete news request: {news_id}")
    try:
        UUID(news_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid news ID format")

    try:
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
):
    """
    Get news items with enhanced filtering and search capabilities
    
    Returns paginated list of news items with comprehensive filtering options.
    """
    logger.info(f"News request: category={category}, company_id={company_id}, source_type={source_type}, limit={limit}, offset={offset}")
    
    try:
        # Parse company IDs if provided
        parsed_company_ids = None
        normalised_company_id = None
        if company_ids:
            parsed_company_ids = [cid.strip() for cid in company_ids.split(',') if cid.strip()]
        elif company_id:
            parsed_company_ids = [company_id]

        if parsed_company_ids:
            normalised_ids = []
            for cid in parsed_company_ids:
                try:
                    normalised_ids.append(UUID(cid))
                except (ValueError, TypeError):
                    normalised_ids.append(cid)
            parsed_company_ids = normalised_ids
            if len(parsed_company_ids) == 1:
                normalised_company_id = parsed_company_ids[0]
        elif company_id:
            try:
                normalised_company_id = UUID(company_id)
            except (ValueError, TypeError):
                normalised_company_id = company_id
        
        # Automatic isolation: if user is authenticated and didn't specify company_ids,
        # filter by subscribed_companies from UserPreferences
        if current_user and not parsed_company_ids:
            try:
                prefs_result = await db.execute(
                    select(UserPreferences).where(UserPreferences.user_id == current_user.id)
                )
                user_prefs = prefs_result.scalar_one_or_none()
                
                if user_prefs and user_prefs.subscribed_companies:
                    # Automatically filter by subscribed companies for data isolation
                    parsed_company_ids = user_prefs.subscribed_companies
                    normalised_company_id = None  # Reset single company_id, use list instead
                    logger.info(
                        f"Auto-filtering news by {len(parsed_company_ids)} subscribed companies "
                        f"for user {current_user.id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to get user preferences for auto-filtering: {e}")
                # Continue without auto-filtering if there's an error
        
        # Get news items with enhanced filtering
        news_items, total_count = await facade.list_news(
            category=category,
            company_id=normalised_company_id,
            company_ids=parsed_company_ids,
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
    
    For authenticated users, automatically filters by subscribed_companies.
    For anonymous users, returns statistics for all news.
    
    Returns statistics about news items including counts by category,
    source type, recent news, and high priority items.
    """
    logger.info(f"News statistics request - user: {current_user.id if current_user else 'anonymous'}")
    
    try:
        # Automatic isolation: if user is authenticated, filter by subscribed_companies
        if current_user:
            try:
                prefs_result = await db.execute(
                    select(UserPreferences).where(UserPreferences.user_id == current_user.id)
                )
                user_prefs = prefs_result.scalar_one_or_none()
                
                if user_prefs and user_prefs.subscribed_companies:
                    # Filter statistics by subscribed companies for data isolation
                    stats = await facade.get_statistics_for_companies(
                        [str(cid) for cid in user_prefs.subscribed_companies]
                    )
                    logger.info(
                        f"Filtered statistics by {len(user_prefs.subscribed_companies)} "
                        f"subscribed companies for user {current_user.id}"
                    )
                    return stats
            except Exception as e:
                logger.warning(f"Failed to get user preferences for stats filtering: {e}")
                # Fall through to general statistics if there's an error
        
        # For anonymous users or if no subscribed companies, return general statistics
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
    
    For authenticated users, validates that all requested companies are in subscribed_companies.
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
        
        # For authenticated users, validate that all requested companies are in subscribed_companies
        if current_user:
            try:
                prefs_result = await db.execute(
                    select(UserPreferences).where(UserPreferences.user_id == current_user.id)
                )
                user_prefs = prefs_result.scalar_one_or_none()
                
                if user_prefs and user_prefs.subscribed_companies:
                    # Convert to sets for comparison
                    requested_ids = set()
                    for cid in parsed_company_ids:
                        if cid:
                            try:
                                requested_ids.add(UUID(cid))
                            except (ValueError, TypeError):
                                # Skip invalid UUIDs
                                continue
                    
                    subscribed_ids = set(user_prefs.subscribed_companies)
                    
                    # Check if all requested companies are in subscribed list
                    if requested_ids and not requested_ids.issubset(subscribed_ids):
                        unauthorized_ids = requested_ids - subscribed_ids
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Access denied: You are not subscribed to some of the requested companies. "
                                   f"Unauthorized company IDs: {[str(uid) for uid in unauthorized_ids]}"
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Failed to validate company access for stats: {e}")
                # Continue without validation if there's an error (for backward compatibility)
        
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
):
    """
    Search news items with advanced filtering

    Performs full-text search across news titles, content, and summaries
    with optional filtering by category, source type, and company.
    """
    logger.info(f"News search: query='{q}', category={category}, limit={limit}, offset={offset}")

    try:
        # Create search parameters
        search_params = NewsSearchSchema(
            query=q,
            category=category,
            source_type=source_type,
            company_id=company_id,
            limit=limit,
            offset=offset
        )

        # Perform search
        news_items, total_count = await facade.search_news(search_params)

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
    facade: NewsFacade = Depends(get_news_facade),
):
    """
    Get specific news item by ID with full details
    
    Returns detailed information about a specific news item including
    related company information, keywords, and user activities.
    """
    logger.info(f"News item request: {news_id}")
    
    try:
        try:
            UUID(news_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid news ID format",
            )

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
):
    """
    Get news items by category with statistics
    
    Returns paginated list of news items for a specific category along with
    statistics about top companies and source distribution.
    """
    logger.info(f"News by category request: category={category_name}, company_id={company_id}, source_type={source_type}, limit={limit}, offset={offset}")
    
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
        
        # Parse company IDs if provided
        parsed_company_ids = None
        if company_ids:
            parsed_company_ids = [cid.strip() for cid in company_ids.split(',') if cid.strip()]
        elif company_id:
            parsed_company_ids = [company_id]
        
        # Get news items
        news_items, total_count = await facade.list_news(
            category=category_enum,
            company_id=company_id,
            company_ids=parsed_company_ids,
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
        category_stats = await facade.get_category_statistics(category_enum, parsed_company_ids)
        
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
