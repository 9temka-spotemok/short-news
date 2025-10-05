"""
News endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.services.news_service import NewsService

router = APIRouter()


@router.get("/")
async def get_news(
    category: Optional[str] = Query(None, description="Filter by category"),
    company: Optional[str] = Query(None, description="Filter by company"),
    limit: int = Query(20, ge=1, le=100, description="Number of news items to return"),
    offset: int = Query(0, ge=0, description="Number of news items to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get news items with optional filtering
    """
    logger.info(f"News request: category={category}, company={company}, limit={limit}, offset={offset}")
    
    try:
        news_service = NewsService(db)
        
        # Get news items
        news_items = await news_service.get_news_items(
            category=category,
            company_id=company,
            limit=limit,
            offset=offset
        )
        
        # Get total count
        total_count = await news_service.get_news_count(
            category=category,
            company_id=company
        )
        
        # Convert to response format
        items = []
        for item in news_items:
            items.append({
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "source_url": item.source_url,
                "source_type": item.source_type.value if item.source_type else None,
                "category": item.category.value if item.category else None,
                "priority_score": item.priority_score,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })
        
        return {
            "items": items,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "filters": {
                "category": category,
                "company": company
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get news: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve news")


@router.get("/{news_id}")
async def get_news_item(
    news_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific news item by ID
    """
    logger.info(f"News item request: {news_id}")
    
    # TODO: Implement news item retrieval
    # 1. Query news item by ID
    # 2. Check if exists
    # 3. Return detailed news item
    
    return {
        "message": "News item endpoint - TODO: Implement",
        "news_id": news_id
    }


@router.get("/search")
async def search_news(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search news items
    """
    logger.info(f"News search: query='{q}', limit={limit}, offset={offset}")
    
    # TODO: Implement news search
    # 1. Build full-text search query
    # 2. Execute search with pagination
    # 3. Return search results
    
    return {
        "message": "News search endpoint - TODO: Implement",
        "query": q,
        "items": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.post("/{news_id}/mark-read")
async def mark_news_read(
    news_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark news item as read
    """
    logger.info(f"Mark news as read: {news_id}")
    
    # TODO: Implement mark as read
    # 1. Verify news item exists
    # 2. Create/update user activity record
    # 3. Return success
    
    return {
        "message": "Mark as read endpoint - TODO: Implement",
        "news_id": news_id,
        "status": "read"
    }


@router.post("/{news_id}/favorite")
async def favorite_news(
    news_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Add news item to favorites
    """
    logger.info(f"Favorite news: {news_id}")
    
    # TODO: Implement favorite functionality
    # 1. Verify news item exists
    # 2. Create/update user activity record
    # 3. Return success
    
    return {
        "message": "Favorite news endpoint - TODO: Implement",
        "news_id": news_id,
        "status": "favorited"
    }
