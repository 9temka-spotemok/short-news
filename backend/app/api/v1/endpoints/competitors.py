"""
Competitor analysis endpoints
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models import User
from app.services.competitor_service import CompetitorAnalysisService

router = APIRouter()


class CompareRequest(BaseModel):
    """Request model for company comparison"""
    company_ids: List[str]
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    name: Optional[str] = None


@router.post("/compare")
async def compare_companies(
    request: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare multiple companies
    
    Request body:
    {
        "company_ids": ["uuid1", "uuid2", "uuid3"],
        "date_from": "2025-01-01",  // optional
        "date_to": "2025-01-31",     // optional
        "name": "Q1 2025 Comparison" // optional
    }
    """
    logger.info(f"Compare companies request from user {current_user.id}: {len(request.company_ids)} companies")
    
    try:
        # Validate input
        if len(request.company_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 companies required for comparison")
        
        if len(request.company_ids) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 companies can be compared at once")
        
        # Parse dates
        if request.date_from:
            date_from = datetime.fromisoformat(request.date_from)
        else:
            date_from = datetime.utcnow() - timedelta(days=30)  # Default: last 30 days
        
        if request.date_to:
            date_to = datetime.fromisoformat(request.date_to)
        else:
            date_to = datetime.utcnow()
        
        # Perform comparison
        competitor_service = CompetitorAnalysisService(db)
        comparison_data = await competitor_service.compare_companies(
            company_ids=request.company_ids,
            date_from=date_from,
            date_to=date_to,
            user_id=str(current_user.id),
            comparison_name=request.name
        )
        
        return comparison_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare companies")


@router.get("/comparisons")
async def get_user_comparisons(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's saved comparisons
    """
    logger.info(f"Get comparisons for user {current_user.id}")
    
    try:
        competitor_service = CompetitorAnalysisService(db)
        comparisons = await competitor_service.get_user_comparisons(str(current_user.id), limit)
        
        return {
            "comparisons": comparisons,
            "total": len(comparisons)
        }
        
    except Exception as e:
        logger.error(f"Error fetching comparisons: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comparisons")


@router.get("/comparisons/{comparison_id}")
async def get_comparison(
    comparison_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific comparison details
    """
    logger.info(f"Get comparison {comparison_id} for user {current_user.id}")
    
    try:
        competitor_service = CompetitorAnalysisService(db)
        comparison = await competitor_service.get_comparison(comparison_id, str(current_user.id))
        
        if not comparison:
            raise HTTPException(status_code=404, detail="Comparison not found")
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comparison")


@router.delete("/comparisons/{comparison_id}")
async def delete_comparison(
    comparison_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a comparison
    """
    logger.info(f"Delete comparison {comparison_id} for user {current_user.id}")
    
    try:
        competitor_service = CompetitorAnalysisService(db)
        success = await competitor_service.delete_comparison(comparison_id, str(current_user.id))
        
        if not success:
            raise HTTPException(status_code=404, detail="Comparison not found")
        
        return {"status": "success", "message": "Comparison deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete comparison")


@router.get("/activity/{company_id}")
async def get_company_activity(
    company_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity metrics for a specific company
    """
    logger.info(f"Get activity for company {company_id} from user {current_user.id}")
    
    try:
        import uuid as uuid_lib
        
        date_from = datetime.utcnow() - timedelta(days=days)
        date_to = datetime.utcnow()
        
        competitor_service = CompetitorAnalysisService(db)
        company_uuid = uuid_lib.UUID(company_id)
        
        # Get metrics
        news_volume = await competitor_service.get_news_volume(company_uuid, date_from, date_to)
        category_distribution = await competitor_service.get_category_distribution(company_uuid, date_from, date_to)
        activity_score = await competitor_service.get_activity_score(company_uuid, date_from, date_to)
        daily_activity = await competitor_service.get_daily_activity(company_uuid, date_from, date_to)
        top_news = await competitor_service.get_top_news(company_uuid, date_from, date_to, limit=10)
        
        return {
            "company_id": company_id,
            "period_days": days,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "metrics": {
                "news_volume": news_volume,
                "category_distribution": category_distribution,
                "activity_score": activity_score,
                "daily_activity": daily_activity,
                "top_news": top_news
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid company ID: {e}")
    except Exception as e:
        logger.error(f"Error fetching company activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch company activity")

