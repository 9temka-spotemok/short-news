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
    
    news_service = NewsService(db)
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
                    "id": str(item.company.id) if item.company.id else None,
                    "name": item.company.name if item.company.name else "",
                    "website": item.company.website if item.company.website else "",
                    "description": item.company.description if item.company.description else "",
                    "category": item.company.category if item.company.category else ""
                }
            
            # Build keywords
            keywords = []
            if item.keywords:
                keywords = [{
                    "keyword": kw.keyword if kw.keyword else "",
                    "relevance": float(kw.relevance_score) if kw.relevance_score else 0.0
                } for kw in item.keywords]
            
            # Safely extract and serialize values
            title = item.title if item.title else ""
            title_truncated = title[:100] + "..." if len(title) > 100 else title
            
            # Handle enum serialization
            source_type_val = item.source_type.value if hasattr(item.source_type, 'value') else str(item.source_type) if item.source_type else None
            category_val = item.category.value if hasattr(item.category, 'value') else str(item.category) if item.category else None
            topic_val = item.topic.value if hasattr(item.topic, 'value') else str(item.topic) if item.topic else None
            sentiment_val = item.sentiment.value if hasattr(item.sentiment, 'value') else str(item.sentiment) if item.sentiment else None
            
            items.append({
                "id": str(item.id),
                "title": item.title,
                "title_truncated": title_truncated,
                "summary": item.summary if item.summary else "",
                "content": item.content if item.content else "",
                "source_url": item.source_url,
                "source_type": source_type_val,
                "category": category_val,
                "topic": topic_val,
                "sentiment": sentiment_val,
                "raw_snapshot_url": item.raw_snapshot_url,
                "priority_score": float(item.priority_score) if item.priority_score else 0.0,
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
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive news statistics
    
    Returns statistics about news items including counts by category,
    source type, recent news, and high priority items.
    """
    logger.info("News statistics request")
    
    news_service = NewsService(db)
    try:
        stats = await news_service.get_news_statistics()
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
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive news statistics filtered by company IDs
    
    Returns statistics about news items for specific companies including counts by category,
    source type, recent news, and high priority items.
    """
    logger.info(f"News statistics by companies request: {company_ids}")
    
    news_service = NewsService(db)
    try:
        # Parse company IDs
        parsed_company_ids = [cid.strip() for cid in company_ids.split(',') if cid.strip()]
        
        if not parsed_company_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one company ID is required"
            )
        
        stats = await news_service.get_news_statistics_by_companies(parsed_company_ids)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get news statistics by companies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news statistics by companies"
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
    
    news_service = NewsService(db)
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
            "title_truncated": news_item.title[:100] + "..." if news_item.title and len(news_item.title) > 100 else news_item.title,
            "summary": news_item.summary,
            "content": news_item.content,
            "source_url": news_item.source_url,
            "source_type": news_item.source_type.value if hasattr(news_item.source_type, 'value') else str(news_item.source_type) if news_item.source_type else None,
            "category": news_item.category.value if hasattr(news_item.category, 'value') else str(news_item.category) if news_item.category else None,
            "topic": news_item.topic.value if hasattr(news_item.topic, 'value') else str(news_item.topic) if news_item.topic else None,
            "sentiment": news_item.sentiment.value if hasattr(news_item.sentiment, 'value') else str(news_item.sentiment) if news_item.sentiment else None,
            "raw_snapshot_url": news_item.raw_snapshot_url,
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
    
    news_service = NewsService(db)
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
            
            # Safely extract values
            title = item.title if item.title else ""
            title_truncated = title[:100] + "..." if len(title) > 100 else title
            
            # Handle enum serialization
            source_type_val = item.source_type.value if hasattr(item.source_type, 'value') else str(item.source_type) if item.source_type else None
            category_val = item.category.value if hasattr(item.category, 'value') else str(item.category) if item.category else None
            topic_val = item.topic.value if hasattr(item.topic, 'value') else str(item.topic) if item.topic else None
            sentiment_val = item.sentiment.value if hasattr(item.sentiment, 'value') else str(item.sentiment) if item.sentiment else None
            
            items.append({
                "id": str(item.id),
                "title": item.title,
                "title_truncated": title_truncated,
                "summary": item.summary if item.summary else "",
                "source_url": item.source_url,
                "source_type": source_type_val,
                "category": category_val,
                "topic": topic_val,
                "sentiment": sentiment_val,
                "raw_snapshot_url": item.raw_snapshot_url,
                "priority_score": float(item.priority_score) if item.priority_score else 0.0,
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




@router.get("/category/{category_name}", response_model=Dict[str, Any])
async def get_news_by_category(
    category_name: str,
    company_id: Optional[str] = Query(None, description="Filter by single company ID"),
    company_ids: Optional[str] = Query(None, description="Filter by multiple company IDs (comma-separated)"),
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items to return"),
    offset: int = Query(0, ge=0, description="Number of news items to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get news items by category with statistics
    
    Returns paginated list of news items for a specific category along with
    statistics about top companies and source distribution.
    """
    logger.info(f"News by category request: category={category_name}, company_id={company_id}, source_type={source_type}, limit={limit}, offset={offset}")
    
    news_service = NewsService(db)
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
        news_items, total_count = await news_service.get_news_items(
            category=category_enum,
            company_id=company_id,
            company_ids=parsed_company_ids,
            source_type=source_type,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        items = []
        for item in news_items:
            company_info = None
            if item.company:
                company_info = {
                    "id": str(item.company.id),
                    "name": item.company.name,
                    "website": item.company.website,
                    "description": item.company.description,
                    "category": item.company.category
                }
            
            keywords = [{"keyword": kw.keyword, "relevance": kw.relevance_score} for kw in item.keywords] if item.keywords else []
            
            # Safely extract and serialize values for category endpoint
            title = item.title if item.title else ""
            title_truncated = title[:100] + "..." if len(title) > 100 else title
            source_type_val = item.source_type.value if hasattr(item.source_type, 'value') else str(item.source_type) if item.source_type else None
            category_val = item.category.value if hasattr(item.category, 'value') else str(item.category) if item.category else None
            topic_val = item.topic.value if hasattr(item.topic, 'value') else str(item.topic) if item.topic else None
            sentiment_val = item.sentiment.value if hasattr(item.sentiment, 'value') else str(item.sentiment) if item.sentiment else None

            items.append({
                "id": str(item.id),
                "title": item.title,
                "title_truncated": title_truncated,
                "summary": item.summary if item.summary else "",
                "content": item.content if item.content else "",
                "source_url": item.source_url,
                "source_type": source_type_val,
                "category": category_val,
                "topic": topic_val,
                "sentiment": sentiment_val,
                "raw_snapshot_url": item.raw_snapshot_url,
                "priority_score": float(item.priority_score) if item.priority_score else 0.0,
                "priority_level": item.priority_level,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "is_recent": item.is_recent,
                "company": company_info,
                "keywords": keywords
            })
        
        # Get statistics for this category
        category_stats = await news_service.get_category_statistics(category_enum, parsed_company_ids)
        
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
