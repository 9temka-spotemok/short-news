"""
User endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db

router = APIRouter()


@router.get("/me")
async def get_current_user(
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile
    """
    logger.info("Current user profile request")
    
    # TODO: Implement get current user
    # 1. Extract user from JWT token
    # 2. Query user profile from database
    # 3. Return user profile
    
    return {
        "message": "Current user endpoint - TODO: Implement",
        "user": {
            "id": "dummy_id",
            "email": "user@example.com",
            "full_name": "Dummy User"
        }
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
    db: AsyncSession = Depends(get_db)
):
    """
    Unsubscribe from a company
    """
    logger.info(f"Unsubscribe from company: {company_id}")
    
    # TODO: Implement unsubscribe from company
    # 1. Extract user from JWT token
    # 2. Remove company from user's subscriptions
    # 3. Return success
    
    return {
        "message": "Unsubscribe from company endpoint - TODO: Implement",
        "company_id": company_id,
        "status": "unsubscribed"
    }
