"""
User endpoints
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel, field_validator
from loguru import logger
import uuid
import json

from app.core.database import get_db
from app.api.dependencies import get_current_user, get_current_user_optional
from app.models import User, UserPreferences
from app.models.user import UserUpdateSchema

router = APIRouter()


def build_default_preferences() -> dict:
    """
    Build a default preferences payload.
    Used for unauthenticated users or fallback scenarios.
    """
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
        "week_start_day": 0,
    }


def safe_enum_to_string(value, default: str = "daily") -> str:
    """
    Safely convert enum value to string.
    Handles None, enum instances, and string values.
    """
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if hasattr(value, 'value'):
        try:
            return str(value.value)
        except (AttributeError, TypeError):
            return str(value) if value else default
    return str(value) if value else default


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
    user_update: UserUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile
    """
    logger.info(f"Update current user profile request for user {current_user.id}")
    
    try:
        # Update user fields if provided
        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name
            logger.info(f"Updating full_name for user {current_user.id}")
        
        if user_update.is_active is not None:
            # Only allow users to update their own active status (or admin logic could go here)
            current_user.is_active = user_update.is_active
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"Successfully updated user {current_user.id}")
        
        return {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at.isoformat(),
            "updated_at": current_user.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error("Error updating user profile: {}", e)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user profile")


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
        return build_default_preferences()
    
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
                notification_frequency='daily',  # Use string value, not enum
                digest_enabled=False,
                digest_frequency='daily',  # Use string value, not enum
                digest_custom_schedule={},
                digest_format='short',  # Use string value, not enum
                digest_include_summaries=True,
                telegram_chat_id=None,
                telegram_enabled=False,
                timezone='UTC',
                week_start_day=0
            )
            db.add(preferences)
            await db.commit()
            await db.refresh(preferences)
        
        # Safely convert interested_categories to list of strings
        interested_categories_list = []
        if preferences.interested_categories:
            for cat in preferences.interested_categories:
                if hasattr(cat, 'value'):
                    try:
                        interested_categories_list.append(cat.value)
                    except (AttributeError, TypeError):
                        interested_categories_list.append(str(cat))
                else:
                    interested_categories_list.append(str(cat))
        
        return {
            "subscribed_companies": [str(company_id) for company_id in (preferences.subscribed_companies or [])],
            "interested_categories": interested_categories_list,
            "keywords": preferences.keywords or [],
            "notification_frequency": safe_enum_to_string(preferences.notification_frequency, "daily"),
            "digest_enabled": preferences.digest_enabled,
            "digest_frequency": safe_enum_to_string(preferences.digest_frequency, "daily"),
            "digest_custom_schedule": preferences.digest_custom_schedule or {},
            "digest_format": safe_enum_to_string(preferences.digest_format, "short"),
            "digest_include_summaries": preferences.digest_include_summaries,
            "telegram_chat_id": preferences.telegram_chat_id,
            "telegram_enabled": preferences.telegram_enabled,
            "timezone": preferences.timezone or "UTC",
            "week_start_day": preferences.week_start_day or 0
        }
        
    except Exception as e:
        logger.error("Error fetching user preferences: {}", e, exc_info=True)
        try:
            await db.rollback()
        except Exception as rollback_error:
            logger.warning(f"Rollback failed while handling preferences error: {rollback_error}", exc_info=True)
        return build_default_preferences()


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
        
        # Safely convert interested_categories to list of strings
        interested_categories_list = []
        if preferences.interested_categories:
            for cat in preferences.interested_categories:
                if hasattr(cat, 'value'):
                    try:
                        interested_categories_list.append(cat.value)
                    except (AttributeError, TypeError):
                        interested_categories_list.append(str(cat))
                else:
                    interested_categories_list.append(str(cat))
        
        return {
            "status": "success",
            "preferences": {
                "subscribed_companies": [str(company_id) for company_id in (preferences.subscribed_companies or [])],
                "interested_categories": interested_categories_list,
                "keywords": preferences.keywords or [],
                "notification_frequency": safe_enum_to_string(preferences.notification_frequency, "daily")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user preferences: {}", e)
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
        
        # Get user preferences with FOR UPDATE lock to prevent race conditions
        # This ensures that concurrent requests are serialized
        result = await db.execute(
            select(UserPreferences)
            .where(UserPreferences.user_id == current_user.id)
            .with_for_update()
        )
        preferences = result.scalar_one_or_none()
        
        # Create default preferences if they don't exist
        if not preferences:
            logger.info(f"Creating default preferences for user {current_user.id}")
            try:
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
                await db.flush()  # Flush to get the ID
            except IntegrityError:
                # Preferences were created by another concurrent request
                logger.info(f"Preferences already exist for user {current_user.id}, retrying select")
                await db.rollback()
                # Retry select with lock
                result = await db.execute(
                    select(UserPreferences)
                    .where(UserPreferences.user_id == current_user.id)
                    .with_for_update()
                )
                preferences = result.scalar_one_or_none()
                if not preferences:
                    raise HTTPException(status_code=500, detail="Failed to create or retrieve user preferences")
        
        # Initialize subscribed_companies if None
        if preferences.subscribed_companies is None:
            preferences.subscribed_companies = []
        
        # Add company to subscriptions if not already subscribed
        # Check again after acquiring lock to handle race conditions
        was_already_subscribed = company_uuid in (preferences.subscribed_companies or [])
        
        if not was_already_subscribed:
            # Create a new list to ensure SQLAlchemy detects the change
            current_companies = list(preferences.subscribed_companies) if preferences.subscribed_companies else []
            current_companies.append(company_uuid)
            preferences.subscribed_companies = current_companies
            logger.info(f"Adding company {company_id} to user {current_user.id} subscriptions. Total will be: {len(preferences.subscribed_companies)}")
        else:
            logger.info(f"Company {company_id} already in subscriptions for user {current_user.id}")
        
        # Mark the object as modified to ensure SQLAlchemy detects the change to ARRAY field
        # This is critical for PostgreSQL ARRAY fields as SQLAlchemy may not detect in-place mutations
        flag_modified(preferences, "subscribed_companies")
        
        await db.commit()
        logger.info(f"Committed changes for user {current_user.id}")
        
        # Refresh to get the latest state after commit
        await db.refresh(preferences)
        logger.info(f"Final subscribed_companies count for user {current_user.id}: {len(preferences.subscribed_companies or [])}, IDs: {[str(c) for c in (preferences.subscribed_companies or [])]}")
        
        return {
            "status": "success",
            "company_id": company_id,
            "company_name": company.name,
            "message": "Successfully subscribed to company" if not was_already_subscribed else "Already subscribed to company"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error subscribing to company: {}", e)
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
        logger.error("Error unsubscribing from company: {}", e)
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
            "digest_frequency": safe_enum_to_string(preferences.digest_frequency, "daily"),
            "digest_custom_schedule": preferences.digest_custom_schedule or {},
            "digest_format": safe_enum_to_string(preferences.digest_format, "short"),
            "digest_include_summaries": preferences.digest_include_summaries,
            "telegram_chat_id": preferences.telegram_chat_id,
            "telegram_enabled": preferences.telegram_enabled,
            "telegram_digest_mode": safe_enum_to_string(preferences.telegram_digest_mode, "all"),
            "timezone": preferences.timezone or "UTC",
            "week_start_day": preferences.week_start_day or 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching digest settings: {}", e)
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
        
        # Apply updates via ORM assignments (no raw SQL/CAST)
        if settings.digest_enabled is not None:
            preferences.digest_enabled = settings.digest_enabled
        if settings.digest_frequency is not None:
            preferences.digest_frequency = settings.digest_frequency
        if settings.digest_custom_schedule is not None:
            preferences.digest_custom_schedule = settings.digest_custom_schedule or {}
        if settings.digest_format is not None:
            preferences.digest_format = settings.digest_format
        if settings.digest_include_summaries is not None:
            preferences.digest_include_summaries = settings.digest_include_summaries
        if settings.telegram_chat_id is not None:
            preferences.telegram_chat_id = settings.telegram_chat_id
        if settings.telegram_enabled is not None:
            preferences.telegram_enabled = settings.telegram_enabled
        if settings.telegram_digest_mode is not None:
            preferences.telegram_digest_mode = settings.telegram_digest_mode
        if settings.timezone is not None:
            preferences.timezone = settings.timezone
        if settings.week_start_day is not None:
            preferences.week_start_day = settings.week_start_day

        await db.commit()
        await db.refresh(preferences)
        
        # Get telegram_digest_mode value (may need refresh after SQL update)
        telegram_digest_mode = preferences.telegram_digest_mode
        
        return {
            "status": "success",
            "digest_settings": {
                "digest_enabled": preferences.digest_enabled,
                "digest_frequency": safe_enum_to_string(preferences.digest_frequency, "daily"),
                "digest_custom_schedule": preferences.digest_custom_schedule or {},
                "digest_format": safe_enum_to_string(preferences.digest_format, "short"),
                "digest_include_summaries": preferences.digest_include_summaries,
                "telegram_chat_id": preferences.telegram_chat_id,
                "telegram_enabled": preferences.telegram_enabled,
                "telegram_digest_mode": safe_enum_to_string(telegram_digest_mode, "all"),
                "timezone": preferences.timezone or "UTC",
                "week_start_day": preferences.week_start_day or 0
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Validation error updating digest settings: {}", e)
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
    except Exception as e:
        logger.error("Error updating digest settings: {}", e, exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update digest settings: {str(e)}")


@router.get("/monitoring/preferences")
async def get_monitoring_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user monitoring preferences.

    Returns a structure compatible with frontend MonitoringPreferences type:
    - enabled: global monitoring toggle
    - check_frequency: per-feature check intervals in hours
    - notification_enabled: whether to send notifications
    - notification_types: list of change types to notify about
    """
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()

        if not preferences:
            # Create default preferences if missing
            logger.info(f"Creating default preferences for monitoring for user {current_user.id}")
            import uuid as uuid_module

            preferences = UserPreferences(
                id=uuid_module.uuid4(),
                user_id=current_user.id,
                subscribed_companies=[],
                interested_categories=[],
                keywords=[],
                notification_frequency="daily",
                digest_enabled=False,
                digest_frequency="daily",
                digest_custom_schedule={},
                digest_format="short",
                digest_include_summaries=True,
                telegram_chat_id=None,
                telegram_enabled=False,
                timezone="UTC",
                week_start_day=0,
                monitoring_enabled=True,
                monitoring_check_frequency="daily",
                monitoring_notify_on_changes=True,
                monitoring_change_types=[
                    "website_structure",
                    "marketing_banner",
                    "marketing_landing",
                    "marketing_product",
                    "marketing_jobs",
                    "seo_meta",
                    "seo_structure",
                    "pricing",
                ],
                monitoring_auto_refresh=True,
                monitoring_notification_channels={"email": True, "telegram": False},
            )
            db.add(preferences)
            await db.commit()
            await db.refresh(preferences)

        # Map enum-like monitoring_check_frequency to numeric hours per feature
        freq_value = safe_enum_to_string(
            getattr(preferences, "monitoring_check_frequency", "daily"),
            "daily",
        )
        if freq_value == "hourly":
            hours = 1
        elif freq_value == "6h":
            hours = 6
        elif freq_value == "weekly":
            hours = 24 * 7
        else:
            # Default daily
            hours = 24

        # Normalize change types to list of strings
        change_types = preferences.monitoring_change_types or [
            "website_structure",
            "marketing_banner",
            "marketing_landing",
            "marketing_product",
            "marketing_jobs",
            "seo_meta",
            "seo_structure",
            "pricing",
        ]

        return {
            "enabled": bool(preferences.monitoring_enabled),
            "check_frequency": {
                "website_structure": hours,
                "marketing_changes": hours,
                "seo_signals": hours,
                "press_releases": hours,
            },
            "notification_enabled": bool(preferences.monitoring_notify_on_changes),
            "notification_types": change_types,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching monitoring preferences: {}", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch monitoring preferences",
        )


@router.put("/monitoring/preferences")
async def update_monitoring_preferences(
    enabled: Optional[bool] = Body(None),
    check_frequency: Optional[Dict[str, Any]] = Body(None),
    notification_enabled: Optional[bool] = Body(None),
    notification_types: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user monitoring preferences.

    Accepts partial updates for MonitoringPreferences-like payload:
    - enabled
    - check_frequency: { website_structure, marketing_changes, seo_signals, press_releases } in hours
    - notification_enabled
    - notification_types: list of change types
    """
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()

        if not preferences:
            logger.info(f"Creating default preferences for monitoring for user {current_user.id}")
            import uuid as uuid_module

            preferences = UserPreferences(
                id=uuid_module.uuid4(),
                user_id=current_user.id,
                subscribed_companies=[],
                interested_categories=[],
                keywords=[],
                notification_frequency="daily",
                digest_enabled=False,
                digest_frequency="daily",
                digest_custom_schedule={},
                digest_format="short",
                digest_include_summaries=True,
                telegram_chat_id=None,
                telegram_enabled=False,
                timezone="UTC",
                week_start_day=0,
                monitoring_enabled=True,
                monitoring_check_frequency="daily",
                monitoring_notify_on_changes=True,
                monitoring_change_types=[
                    "website_structure",
                    "marketing_banner",
                    "marketing_landing",
                    "marketing_product",
                    "marketing_jobs",
                    "seo_meta",
                    "seo_structure",
                    "pricing",
                ],
                monitoring_auto_refresh=True,
                monitoring_notification_channels={"email": True, "telegram": False},
            )
            db.add(preferences)

        # Update global enabled flag
        if enabled is not None:
            preferences.monitoring_enabled = enabled

        # Update check frequency -> map hours to enum bucket
        if check_frequency is not None:
            # For now we use a single global frequency derived from website_structure
            try:
                hours = int(
                    check_frequency.get("website_structure")
                    or check_frequency.get("marketing_changes")
                    or check_frequency.get("seo_signals")
                    or check_frequency.get("press_releases")
                )
            except (TypeError, ValueError):
                hours = None

            if hours is not None:
                if hours <= 1:
                    freq_value = "hourly"
                elif hours <= 6:
                    freq_value = "6h"
                elif hours < 24 * 7:
                    freq_value = "daily"
                else:
                    freq_value = "weekly"
                preferences.monitoring_check_frequency = freq_value

        # Update notification flag
        if notification_enabled is not None:
            preferences.monitoring_notify_on_changes = notification_enabled

        # Update notification types
        if notification_types is not None:
            preferences.monitoring_change_types = notification_types

        await db.commit()
        await db.refresh(preferences)

        # Reuse getter logic to build response
        return await get_monitoring_preferences(current_user=current_user, db=db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating monitoring preferences: {}", e, exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update monitoring preferences",
        )
