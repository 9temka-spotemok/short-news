"""
User endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from loguru import logger
import uuid

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models import User, UserPreferences

router = APIRouter()


class DigestSettingsUpdate(BaseModel):
    """Model for updating digest settings"""
    digest_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None
    digest_custom_schedule: Optional[dict] = None
    digest_format: Optional[str] = None
    digest_include_summaries: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    timezone: Optional[str] = None
    week_start_day: Optional[int] = None
    
    @field_validator('digest_frequency')
    @classmethod
    def validate_digest_frequency(cls, v):
        if v is not None and v not in ['daily', 'weekly', 'custom']:
            raise ValueError('digest_frequency must be one of: daily, weekly, custom')
        return v
    
    @field_validator('digest_format')
    @classmethod
    def validate_digest_format(cls, v):
        if v is not None and v not in ['short', 'detailed']:
            raise ValueError('digest_format must be one of: short, detailed')
        return v


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile
    """
    logger.info(f"Current user profile request from {current_user.id}")
    
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }


@router.put("/me")
async def update_current_user(
    full_name: str = None,
    email: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile
    """
    logger.info("Update current user profile request")
    
    # TODO: Implement update user profile
    # 1. Extract user from JWT token
    # 2. Validate input data
    # 3. Update user profile in database
    # 4. Return updated profile
    
    return {
        "message": "Update user endpoint - TODO: Implement",
        "user": {
            "id": "dummy_id",
            "email": email or "user@example.com",
            "full_name": full_name or "Dummy User"
        }
    }


@router.get("/preferences")
async def get_user_preferences(
    db: AsyncSession = Depends(get_db)
):
    """
    Get user preferences
    """
    logger.info("User preferences request")
    
    # TODO: Implement get user preferences
    # 1. Extract user from JWT token
    # 2. Query user preferences from database
    # 3. Return preferences
    
    return {
        "message": "User preferences endpoint - TODO: Implement",
        "preferences": {
            "subscribed_companies": [],
            "interested_categories": [],
            "keywords": [],
            "notification_frequency": "daily"
        }
    }


@router.put("/preferences")
async def update_user_preferences(
    subscribed_companies: List[str] = None,
    interested_categories: List[str] = None,
    keywords: List[str] = None,
    notification_frequency: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Update user preferences
    """
    logger.info("Update user preferences request")
    
    # TODO: Implement update user preferences
    # 1. Extract user from JWT token
    # 2. Validate input data
    # 3. Update preferences in database
    # 4. Return updated preferences
    
    return {
        "message": "Update preferences endpoint - TODO: Implement",
        "preferences": {
            "subscribed_companies": subscribed_companies or [],
            "interested_categories": interested_categories or [],
            "keywords": keywords or [],
            "notification_frequency": notification_frequency or "daily"
        }
    }


@router.post("/companies/{company_id}/subscribe")
async def subscribe_to_company(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Subscribe to a company
    """
    logger.info(f"Subscribe to company: {company_id}")
    
    # TODO: Implement subscribe to company
    # 1. Extract user from JWT token
    # 2. Verify company exists
    # 3. Add company to user's subscriptions
    # 4. Return success
    
    return {
        "message": "Subscribe to company endpoint - TODO: Implement",
        "company_id": company_id,
        "status": "subscribed"
    }


@router.delete("/companies/{company_id}/unsubscribe")
async def unsubscribe_from_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Unsubscribe from a company
    """
    logger.info(f"Unsubscribe from company {company_id} for user {current_user.id}")
    
    try:
        # Get user preferences
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()
        
        if not preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        # Remove company from subscriptions
        company_uuid = uuid.UUID(company_id)
        if preferences.subscribed_companies and company_uuid in preferences.subscribed_companies:
            preferences.subscribed_companies.remove(company_uuid)
            await db.commit()
        
        return {
            "status": "success",
            "company_id": company_id,
            "message": "Unsubscribed from company"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from company: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to unsubscribe from company")


@router.get("/preferences/digest")
async def get_digest_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user digest settings
    """
    logger.info(f"Get digest settings for user {current_user.id}")
    
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()
        
        # Create default preferences if they don't exist
        if not preferences:
            logger.info(f"Creating default preferences for user {current_user.id}")
            from app.models.preferences import DigestFrequency, DigestFormat, NotificationFrequency
            
            preferences = UserPreferences(
                id=uuid.uuid4(),
                user_id=current_user.id,
                subscribed_companies=[],
                interested_categories=[],
                keywords=[],
                notification_frequency='daily',
                digest_enabled=False,
                digest_frequency='daily',
                digest_custom_schedule={},
                digest_format='short',
                digest_include_summaries=True,
                telegram_chat_id=None,
                telegram_enabled=False,
                timezone='UTC',
                week_start_day=0
            )
            db.add(preferences)
            await db.commit()
            await db.refresh(preferences)
        
        return {
            "digest_enabled": preferences.digest_enabled,
            "digest_frequency": preferences.digest_frequency if preferences.digest_frequency else "daily",
            "digest_custom_schedule": preferences.digest_custom_schedule,
            "digest_format": preferences.digest_format if preferences.digest_format else "short",
            "digest_include_summaries": preferences.digest_include_summaries,
            "telegram_chat_id": preferences.telegram_chat_id,
            "telegram_enabled": preferences.telegram_enabled,
            "timezone": preferences.timezone if hasattr(preferences, 'timezone') else "UTC",
            "week_start_day": preferences.week_start_day if hasattr(preferences, 'week_start_day') else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching digest settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch digest settings")


@router.put("/preferences/digest")
async def update_digest_settings(
    settings: DigestSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user digest settings
    """
    logger.info(f"Update digest settings for user {current_user.id}")
    
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()
        
        # Create default preferences if they don't exist
        if not preferences:
            logger.info(f"Creating default preferences for user {current_user.id}")
            from app.models.preferences import DigestFrequency, DigestFormat, NotificationFrequency
            
            preferences = UserPreferences(
                id=uuid.uuid4(),
                user_id=current_user.id,
                subscribed_companies=[],
                interested_categories=[],
                keywords=[],
                notification_frequency='daily',
                digest_enabled=False,
                digest_frequency='daily',
                digest_custom_schedule={},
                digest_format='short',
                digest_include_summaries=True,
                telegram_chat_id=None,
                telegram_enabled=False,
                timezone='UTC',
                week_start_day=0
            )
            db.add(preferences)
        
        # Update settings
        if settings.digest_enabled is not None:
            preferences.digest_enabled = settings.digest_enabled
        if settings.digest_frequency is not None:
            preferences.digest_frequency = settings.digest_frequency
        if settings.digest_custom_schedule is not None:
            preferences.digest_custom_schedule = settings.digest_custom_schedule
        if settings.digest_format is not None:
            preferences.digest_format = settings.digest_format
        if settings.digest_include_summaries is not None:
            preferences.digest_include_summaries = settings.digest_include_summaries
        if settings.telegram_chat_id is not None:
            preferences.telegram_chat_id = settings.telegram_chat_id
        if settings.telegram_enabled is not None:
            preferences.telegram_enabled = settings.telegram_enabled
        if settings.timezone is not None:
            preferences.timezone = settings.timezone
        if settings.week_start_day is not None:
            preferences.week_start_day = settings.week_start_day
        
        await db.commit()
        await db.refresh(preferences)
        
        return {
            "status": "success",
            "digest_settings": {
                "digest_enabled": preferences.digest_enabled,
                "digest_frequency": preferences.digest_frequency if preferences.digest_frequency else None,
                "digest_custom_schedule": preferences.digest_custom_schedule,
                "digest_format": preferences.digest_format if preferences.digest_format else None,
                "digest_include_summaries": preferences.digest_include_summaries,
                "telegram_chat_id": preferences.telegram_chat_id,
                "telegram_enabled": preferences.telegram_enabled,
                "timezone": preferences.timezone if hasattr(preferences, 'timezone') else "UTC",
                "week_start_day": preferences.week_start_day if hasattr(preferences, 'week_start_day') else 0
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
    except Exception as e:
        logger.error(f"Error updating digest settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update digest settings")
