"""
Competitor analysis endpoints
"""

from typing import List, Optional
from datetime import datetime, timedelta, timezone
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
    request_data: dict = Body(...),
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
    logger.info(f"Compare companies request from user {current_user.id}")
    logger.info(f"Request data: {request_data}")
    logger.info(f"Request type: {type(request_data)}")
    
    try:
        # Extract data from request
        company_ids = request_data.get('company_ids', [])
        date_from_str = request_data.get('date_from')
        date_to_str = request_data.get('date_to')
        name = request_data.get('name')
        
        logger.info(f"Company IDs: {company_ids}")
        logger.info(f"Company IDs type: {type(company_ids)}")
        
        # Validate input
        if not isinstance(company_ids, list):
            raise HTTPException(status_code=400, detail="company_ids must be a list")
        
        if len(company_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 companies required for comparison")
        
        if len(company_ids) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 companies can be compared at once")
        
        # Validate UUIDs
        import uuid as uuid_lib
        for company_id in company_ids:
            try:
                uuid_lib.UUID(company_id)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid company ID format: {company_id}")
        
        # Parse dates
        if date_from_str:
            try:
                date_from = datetime.fromisoformat(date_from_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError as e:
                logger.error(f"Invalid date_from format: {date_from_str}, error: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid date_from format: {date_from_str}")
        else:
            date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)  # Default: last 30 days
        
        if date_to_str:
            try:
                date_to = datetime.fromisoformat(date_to_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError as e:
                logger.error(f"Invalid date_to format: {date_to_str}, error: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid date_to format: {date_to_str}")
        else:
            date_to = datetime.now(timezone.utc).replace(tzinfo=None)
        
        logger.info(f"Parsed dates: from={date_from}, to={date_to}")
        
        # Perform comparison
        competitor_service = CompetitorAnalysisService(db)
        comparison_data = await competitor_service.compare_companies(
            company_ids=company_ids,
            date_from=date_from,
            date_to=date_to,
            user_id=str(current_user.id),
            comparison_name=name
        )
        
        return comparison_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing companies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compare companies: {str(e)}")


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
        
        date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        date_to = datetime.now(timezone.utc).replace(tzinfo=None)
        
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


@router.get("/suggest/{company_id}")
async def suggest_competitors(
    company_id: str,
    limit: int = 5,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Автоматически подобрать конкурентов
    
    Query params:
        limit: сколько конкурентов вернуть (default: 5, max: 10)
        days: за какой период анализировать (default: 30)
    """
    try:
        import uuid as uuid_lib
        
        company_uuid = uuid_lib.UUID(company_id)
        
        date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        date_to = datetime.now(timezone.utc).replace(tzinfo=None)
        
        competitor_service = CompetitorAnalysisService(db)
        suggestions = await competitor_service.suggest_competitors(
            company_id=company_uuid,
            limit=min(limit, 10),
            date_from=date_from,
            date_to=date_to
        )
        
        return {
            "company_id": company_id,
            "period_days": days,
            "suggestions": suggestions
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company ID")
    except Exception as e:
        logger.error(f"Error suggesting competitors: {e}")
        raise HTTPException(status_code=500, detail="Failed to suggest competitors")


@router.post("/themes")
async def analyze_themes(
    request_data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Анализ новостных тем для списка компаний
    
    Body:
        {
            "company_ids": ["uuid1", "uuid2", "uuid3"],
            "date_from": "2025-01-01",  // optional
            "date_to": "2025-01-31"     // optional
        }
    """
    try:
        import uuid as uuid_lib
        
        # Извлекаем данные из request_data
        company_ids = request_data.get("company_ids", [])
        date_from_str = request_data.get("date_from")
        date_to_str = request_data.get("date_to")
        
        # Валидация company_ids
        if not isinstance(company_ids, list):
            raise HTTPException(status_code=400, detail="company_ids must be a list")
        
        company_uuids = []
        for company_id in company_ids:
            try:
                company_uuids.append(uuid_lib.UUID(company_id))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid company ID: {company_id}")
        
        # Парсинг дат
        if date_from_str:
            date_from_dt = datetime.fromisoformat(date_from_str).replace(tzinfo=None)
        else:
            date_from_dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
            
        if date_to_str:
            date_to_dt = datetime.fromisoformat(date_to_str).replace(tzinfo=None)
        else:
            date_to_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Анализ тем
        competitor_service = CompetitorAnalysisService(db)
        themes_data = await competitor_service.analyze_news_themes(
            company_ids=company_uuids,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
        
        return themes_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error analyzing themes: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze themes")
