"""
API dependencies
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.core.security import decode_token
from app.domains.news import NewsFacade
from app.domains.competitors import CompetitorFacade
from app.domains.analytics import AnalyticsFacade
from app.domains.notifications import NotificationsFacade
from app.models import User
from app.core.personalization import PersonalizationService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from JWT token
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    # Get user ID from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    try:
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
    except Exception:
        raise credentials_exception
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    
    Args:
        current_user: Current user from token
        
    Returns:
        Active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_optional(
    token: Optional[str] = Security(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token, returns None if not authenticated
    
    Args:
        token: JWT access token (optional)
        db: Database session
        
    Returns:
        Current user or None if not authenticated
    """
    # If no token provided, return None
    if token is None:
        return None
    
    try:
        # Decode token
        payload = decode_token(token)
        if payload is None:
            return None
        
        # Get user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Get user from database
        try:
            result = await db.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = result.scalar_one_or_none()
        except Exception:
            return None
        
        if user is None or not user.is_active:
            return None
            
        return user
    except Exception:
        return None


def get_news_facade(
    db: AsyncSession = Depends(get_db),
) -> NewsFacade:
    """
    Provide NewsFacade instance for request-scoped operations.
    """
    return NewsFacade(db)


def get_competitor_facade(
    db: AsyncSession = Depends(get_db),
) -> CompetitorFacade:
    """
    Provide CompetitorFacade instance for request-scoped operations.
    """
    return CompetitorFacade(db)


def get_analytics_facade(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsFacade:
    """
    Provide AnalyticsFacade instance for request-scoped operations.
    """
    return AnalyticsFacade(db)


def get_notifications_facade(
    db: AsyncSession = Depends(get_db),
) -> NotificationsFacade:
    """
    Provide NotificationsFacade instance for request-scoped operations.
    """
    return NotificationsFacade(db)


def get_personalization_service(
    db: AsyncSession = Depends(get_db),
) -> PersonalizationService:
    """
    Provide PersonalizationService instance for request-scoped operations.
    """
    return PersonalizationService(db)

