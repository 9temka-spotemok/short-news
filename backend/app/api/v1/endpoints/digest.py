"""
Digest endpoints
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models import User
from app.services.digest_service import DigestService
from app.tasks.digest import generate_user_digest

router = APIRouter()


@router.get("/daily")
async def get_daily_digest(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily digest for current user
    """
    logger.info(f"Daily digest request from user {current_user.id}")
    
    try:
        digest_service = DigestService(db)
        digest_data = await digest_service.generate_user_digest(
            user_id=str(current_user.id),
            period="daily"
        )
        
        return digest_data
        
    except Exception as e:
        logger.error(f"Error generating daily digest: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate digest")


@router.get("/weekly")
async def get_weekly_digest(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get weekly digest for current user
    """
    logger.info(f"Weekly digest request from user {current_user.id}")
    
    try:
        digest_service = DigestService(db)
        digest_data = await digest_service.generate_user_digest(
            user_id=str(current_user.id),
            period="weekly"
        )
        
        return digest_data
        
    except Exception as e:
        logger.error(f"Error generating weekly digest: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate digest")


@router.get("/custom")
async def get_custom_digest(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get custom digest for date range
    """
    logger.info(f"Custom digest request from user {current_user.id}: {start_date} to {end_date}")
    
    try:
        # Parse dates
        date_from = datetime.fromisoformat(start_date) if start_date else None
        date_to = datetime.fromisoformat(end_date) if end_date else None
        
        digest_service = DigestService(db)
        digest_data = await digest_service.generate_user_digest(
            user_id=str(current_user.id),
            period="custom",
            custom_date_from=date_from,
            custom_date_to=date_to
        )
        
        return digest_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error generating custom digest: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate digest")


@router.post("/generate")
async def generate_digest_async(
    digest_type: str = Query(..., description="Type of digest: daily, weekly, custom"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger async digest generation (background task)
    """
    logger.info(f"Async digest generation request from user {current_user.id}: type={digest_type}")
    
    try:
        # Trigger Celery task
        task = generate_user_digest.delay(str(current_user.id), digest_type)
        
        return {
            "status": "processing",
            "task_id": task.id,
            "digest_type": digest_type,
            "message": "Digest generation started. Check back later or wait for Telegram notification."
        }
        
    except Exception as e:
        logger.error(f"Error triggering digest generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to start digest generation")
