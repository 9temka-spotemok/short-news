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
import json

from app.core.database import get_db
from app.api.dependencies import get_current_user, get_current_user_optional
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
    telegram_digest_mode: Optional[str] = None
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
    
    @field_validator('telegram_digest_mode')
    @classmethod
    def validate_telegram_digest_mode(cls, v):
        if v is not None and v not in ['all', 'tracked']:
            raise ValueError('telegram_digest_mode must be one of: all, tracked')
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user preferences
    """
    # If user is not authenticated, return default preferences
    if current_user is None:
        logger.info("Get user preferences - not authenticated, returning defaults")
        return {
            "subscribed_companies": [],
            "interested_categories": [],
            "keywords": [],
            "notification_frequency": "daily",
            "digest_enabled": False,
            "digest_frequency": "daily",
            "digest_custom_schedule": {},
            "digest_format": "short",
            "digest_include_summaries": True,
            "telegram_chat_id": None,
            "telegram_enabled": False,
            "timezone": "UTC",
            "week_start_day": 0
        }
    
    logger.info(f"Get user preferences for user {current_user.id}")
    
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()
        
        # Create default preferences if they don't exist
        if not preferences:
            logger.info(f"Creating default preferences for user {current_user.id}")
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
            "subscribed_companies": [str(company_id) for company_id in (preferences.subscribed_companies or [])],
            "interested_categories": [cat.value for cat in (preferences.interested_categories or [])],
            "keywords": preferences.keywords or [],
            "notification_frequency": preferences.notification_frequency or "daily",
            "digest_enabled": preferences.digest_enabled,
            "digest_frequency": preferences.digest_frequency or "daily",
            "digest_custom_schedule": preferences.digest_custom_schedule or {},
            "digest_format": preferences.digest_format or "short",
            "digest_include_summaries": preferences.digest_include_summaries,
            "telegram_chat_id": preferences.telegram_chat_id,
            "telegram_enabled": preferences.telegram_enabled,
            "timezone": preferences.timezone or "UTC",
            "week_start_day": preferences.week_start_day or 0
        }
        
    except Exception as e:
        logger.error(f"Error fetching user preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user preferences")


@router.put("/preferences")
async def update_user_preferences(
    subscribed_companies: List[str] = None,
    interested_categories: List[str] = None,
    keywords: List[str] = None,
    notification_frequency: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user preferences
    """
    logger.info(f"Update user preferences for user {current_user.id}")
    
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()
        
        # Create default preferences if they don't exist
        if not preferences:
            logger.info(f"Creating default preferences for user {current_user.id}")
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
        
        # Update preferences
        if subscribed_companies is not None:
            # Convert string IDs to UUIDs
            try:
                preferences.subscribed_companies = [uuid.UUID(company_id) for company_id in subscribed_companies]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid company ID format: {e}")
        
        if interested_categories is not None:
            # Convert string categories to enum values
            from app.models.news import NewsCategory
            try:
                preferences.interested_categories = [NewsCategory(cat) for cat in interested_categories]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid category: {e}")
        
        if keywords is not None:
            preferences.keywords = keywords
        
        if notification_frequency is not None:
            if notification_frequency not in ['realtime', 'daily', 'weekly', 'never']:
                raise HTTPException(status_code=400, detail="Invalid notification frequency")
            preferences.notification_frequency = notification_frequency
        
        await db.commit()
        await db.refresh(preferences)
        
        return {
            "status": "success",
            "preferences": {
                "subscribed_companies": [str(company_id) for company_id in (preferences.subscribed_companies or [])],
                "interested_categories": [cat.value for cat in (preferences.interested_categories or [])],
                "keywords": preferences.keywords or [],
                "notification_frequency": preferences.notification_frequency or "daily"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user preferences")


@router.post("/companies/{company_id}/subscribe")
async def subscribe_to_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Subscribe to a company
    """
    logger.info(f"Subscribe to company {company_id} for user {current_user.id}")
    
    try:
        # Validate company ID format
        try:
            company_uuid = uuid.UUID(company_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company ID format")
        
        # Verify company exists
        from app.models.company import Company
        result = await db.execute(
            select(Company).where(Company.id == company_uuid)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get user preferences
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()
        
        # Create default preferences if they don't exist
        if not preferences:
            logger.info(f"Creating default preferences for user {current_user.id}")
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
        
        # Add company to subscriptions if not already subscribed
        if not preferences.subscribed_companies:
            preferences.subscribed_companies = []
        
        if company_uuid not in preferences.subscribed_companies:
            preferences.subscribed_companies.append(company_uuid)
            await db.commit()
        
        return {
            "status": "success",
            "company_id": company_id,
            "company_name": company.name,
            "message": "Successfully subscribed to company"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to company: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to subscribe to company")


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
            "telegram_digest_mode": preferences.telegram_digest_mode if preferences.telegram_digest_mode else "all",
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
        
        # Use direct SQL updates for all fields to avoid enum casting issues
        from sqlalchemy import text
        
        # Build dynamic UPDATE statement
        updates = []
        params = {"user_id": preferences.id}
        
        if settings.digest_enabled is not None:
            updates.append("digest_enabled = :digest_enabled")
            params["digest_enabled"] = settings.digest_enabled
        
        if settings.digest_frequency is not None:
            # Use :: operator to handle enum name mismatch (digestfrequency vs digest_frequency)
            updates.append("digest_frequency = CAST(:digest_frequency AS text)::digestfrequency")
            params["digest_frequency"] = settings.digest_frequency
        
        if settings.digest_custom_schedule is not None:
            # Use CAST(:param AS jsonb) to avoid mixed param styles with asyncpg
            updates.append("digest_custom_schedule = CAST(:digest_custom_schedule AS jsonb)")
            params["digest_custom_schedule"] = json.dumps(settings.digest_custom_schedule)
        
        if settings.digest_format is not None:
            # Use :: operator to handle enum name mismatch (digestformat vs digest_format)
            updates.append("digest_format = CAST(:digest_format AS text)::digestformat")
            params["digest_format"] = settings.digest_format
        
        if settings.digest_include_summaries is not None:
            updates.append("digest_include_summaries = :digest_include_summaries")
            params["digest_include_summaries"] = settings.digest_include_summaries
        
        if settings.telegram_chat_id is not None:
            updates.append("telegram_chat_id = :telegram_chat_id")
            params["telegram_chat_id"] = settings.telegram_chat_id
        
        if settings.telegram_enabled is not None:
            updates.append("telegram_enabled = :telegram_enabled")
            params["telegram_enabled"] = settings.telegram_enabled
        
        if settings.telegram_digest_mode is not None:
            # Use :: operator to handle enum name mismatch (telegramdigestmode vs telegram_digest_mode)
            updates.append("telegram_digest_mode = CAST(:telegram_digest_mode AS text)::telegramdigestmode")
            params["telegram_digest_mode"] = settings.telegram_digest_mode
        
        if settings.timezone is not None:
            updates.append("timezone = :timezone")
            params["timezone"] = settings.timezone
        
        if settings.week_start_day is not None:
            updates.append("week_start_day = :week_start_day")
            params["week_start_day"] = settings.week_start_day
        
        # Add updated_at timestamp
        updates.append("updated_at = now()")
        
        # Execute single UPDATE query if there are any updates
        if updates:
            update_query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE id = :user_id"
            await db.execute(text(update_query), params)
            updated_fields = [k for k in params.keys() if k != 'user_id']
            logger.info(f"Updated digest settings for user {current_user.id}: {', '.join(updated_fields)}")
        
        await db.commit()
        await db.refresh(preferences)
        
        # Get telegram_digest_mode value (may need refresh after SQL update)
        telegram_digest_mode = preferences.telegram_digest_mode
        
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
                "telegram_digest_mode": telegram_digest_mode if telegram_digest_mode else 'all',
                "timezone": preferences.timezone if hasattr(preferences, 'timezone') else "UTC",
                "week_start_day": preferences.week_start_day if hasattr(preferences, 'week_start_day') else 0
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating digest settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
    except Exception as e:
        logger.error(f"Error updating digest settings: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update digest settings: {str(e)}")
