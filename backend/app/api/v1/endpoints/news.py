"""
Enhanced News endpoints with improved error handling and validation
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.services.news_service import NewsService
from app.models.news import (
    NewsCategory, SourceType, 
    NewsResponseSchema, NewsSearchSchema, NewsStatsSchema
)
from app.core.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/", response_model=Dict[str, Any])
async def get_news(
    category: Optional[NewsCategory] = Query(None, description="Filter by news category"),
    company_id: Optional[str] = Query(None, description="Filter by single company ID"),
    company_ids: Optional[str] = Query(None, description="Filter by multiple company IDs (comma-separated)"),
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    search_query: Optional[str] = Query(None, description="Search query for title/content"),
    min_priority: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum priority score"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items to return"),
    offset: int = Query(0, ge=0, description="Number of news items to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get news items with enhanced filtering and search capabilities
    
    Returns paginated list of news items with comprehensive filtering options.
    """
    logger.info(f"News request: category={category}, company_id={company_id}, source_type={source_type}, limit={limit}, offset={offset}")
    
    async with NewsService(db) as news_service:
        try:
            # Parse company IDs if provided
            parsed_company_ids = None
            if company_ids:
                parsed_company_ids = [cid.strip() for cid in company_ids.split(',') if cid.strip()]
            elif company_id:
                parsed_company_ids = [company_id]
            
            # Get news items with enhanced filtering
            news_items, total_count = await news_service.get_news_items(
                category=category,
                company_id=company_id,
                company_ids=parsed_company_ids,
                source_type=source_type,
                search_query=search_query,
                min_priority=min_priority,
                limit=limit,
                offset=offset
            )
            
            # Convert to response format with enhanced data
            items = []
            for item in news_items:
                # Build company info
                company_info = None
                if item.company:
                    company_info = {
                        "id": str(item.company.id),
                        "name": item.company.name,
                        "website": item.company.website,
                        "description": item.company.description,
                        "category": item.company.category
                    }
                
                # Build keywords
                keywords = [{"keyword": kw.keyword, "relevance": kw.relevance_score} for kw in item.keywords] if item.keywords else []
                
                items.append({
                    "id": str(item.id),
                    "title": item.title,
                    "title_truncated": item.title_truncated,
                    "summary": item.summary,
                    "content": item.content,
                    "source_url": item.source_url,
                    "source_type": item.source_type,
                    "category": item.category,
                    "priority_score": item.priority_score,
                    "priority_level": item.priority_level,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                    "is_recent": item.is_recent,
                    "company": company_info,
                    "keywords": keywords
                })
            
            return {
                "items": items,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(items) < total_count,
                "filters": {
                    "category": category.value if category else None,
                    "company_id": company_id,
                    "source_type": source_type.value if source_type else None,
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
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive news statistics
    
    Returns statistics about news items including counts by category,
    source type, recent news, and high priority items.
    """
    logger.info("News statistics request")
    
    async with NewsService(db) as news_service:
        try:
            stats = await news_service.get_news_statistics()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get news statistics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve news statistics"
            )


@router.get("/{news_id}", response_model=Dict[str, Any])
async def get_news_item(
    news_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific news item by ID with full details
    
    Returns detailed information about a specific news item including
    related company information, keywords, and user activities.
    """
    logger.info(f"News item request: {news_id}")
    
    async with NewsService(db) as news_service:
        try:
            news_item = await news_service.get_news_item_by_id(news_id)
            
            if not news_item:
                raise NotFoundError(f"News item with ID {news_id} not found", resource_type="news_item")
            
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
            
            return {
                "id": str(news_item.id),
                "title": news_item.title,
                "title_truncated": news_item.title_truncated,
                "summary": news_item.summary,
                "content": news_item.content,
                "source_url": news_item.source_url,
                "source_type": news_item.source_type,
                "category": news_item.category,
                "priority_score": news_item.priority_score,
                "priority_level": news_item.priority_level,
                "published_at": news_item.published_at.isoformat() if news_item.published_at else None,
                "created_at": news_item.created_at.isoformat() if news_item.created_at else None,
                "updated_at": news_item.updated_at.isoformat() if news_item.updated_at else None,
                "is_recent": news_item.is_recent,
                "company": company_info,
                "keywords": keywords,
                "activities": activities
            }
            
        except NotFoundError:
            raise
        except ValidationError as e:
            logger.warning(f"Validation error in news item request: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid news ID format: {e.message}"
            )
        except Exception as e:
            logger.error(f"Failed to get news item {news_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve news item"
            )


@router.get("/search", response_model=Dict[str, Any])
async def search_news(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[NewsCategory] = Query(None, description="Filter by category"),
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search news items with advanced filtering
    
    Performs full-text search across news titles, content, and summaries
    with optional filtering by category, source type, and company.
    """
    logger.info(f"News search: query='{q}', category={category}, limit={limit}, offset={offset}")
    
    async with NewsService(db) as news_service:
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
            news_items, total_count = await news_service.search_news(search_params)
            
            # Convert to response format
            items = []
            for item in news_items:
                company_info = None
                if item.company:
                    company_info = {
                        "id": str(item.company.id),
                        "name": item.company.name,
                        "website": item.company.website
                    }
                
                items.append({
                    "id": str(item.id),
                    "title": item.title,
                    "title_truncated": item.title_truncated,
                    "summary": item.summary,
                    "source_url": item.source_url,
                    "source_type": item.source_type,
                    "category": item.category,
                    "priority_score": item.priority_score,
                    "priority_level": item.priority_level,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "is_recent": item.is_recent,
                    "company": company_info
                })
            
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
async def mark_news_read(
    news_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark news item as read for the current user
    
    Creates a user activity record to track that the news item has been read.
    """
    logger.info(f"Mark news as read: {news_id}")
    
    # TODO: Implement mark as read functionality
    # This would require user authentication and user activity tracking
    # For now, return a placeholder response
    
    return {
        "message": "News item marked as read",
        "news_id": news_id,
        "status": "read",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.post("/{news_id}/favorite")
async def favorite_news(
    news_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Add news item to favorites for the current user
    
    Creates a user activity record to track that the news item has been favorited.
    """
    logger.info(f"Favorite news: {news_id}")
    
    # TODO: Implement favorite functionality
    # This would require user authentication and user activity tracking
    # For now, return a placeholder response
    
    return {
        "message": "News item added to favorites",
        "news_id": news_id,
        "status": "favorited",
        "timestamp": "2024-01-01T00:00:00Z"
    }
