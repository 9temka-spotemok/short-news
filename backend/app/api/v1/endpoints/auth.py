"""
Authentication endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.models.user import User
from app.schemas.auth import UserRegister, AuthResponse, UserResponse

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/register", response_model=dict)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    User registration endpoint
    """
    logger.info(f"User registration attempt: {user_data.email}")
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.warning(f"Registration failed: User {user_data.email} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Hash password
    password_hash = get_password_hash(user_data.password)
    
    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=password_hash,
        full_name=user_data.full_name,
        is_active=True,
        is_verified=False
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(f"User registered successfully: {user_data.email}")
    
    return {
        "message": "Регистрация успешна. Проверьте email для подтверждения.",
        "email": user_data.email
    }


@router.post("/login", response_model=AuthResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    User login endpoint
    """
    logger.info(f"User login attempt: {form_data.username}")
    
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    # Verify credentials
    if not user or not verify_password(form_data.password, user.password_hash):
        logger.warning(f"Login failed: Invalid credentials for {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login failed: User {form_data.username} is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})
    
    logger.info(f"User logged in successfully: {user.email}")
    
    # Return response
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token endpoint
    """
    logger.info("Token refresh attempt")
    
    # TODO: Implement token refresh
    # 1. Validate refresh token
    # 2. Generate new access token
    # 3. Return new access token
    
    return {
        "message": "Token refresh endpoint - TODO: Implement",
        "access_token": "new_dummy_token",
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    User logout endpoint
    """
    logger.info("User logout attempt")
    
    # TODO: Implement logout
    # 1. Add token to blacklist
    # 2. Return success message
    
    return {
        "message": "User logout endpoint - TODO: Implement"
    }


@router.post("/reset-password")
async def reset_password(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Password reset endpoint
    """
    logger.info(f"Password reset request: {email}")
    
    # TODO: Implement password reset
    # 1. Validate email
    # 2. Generate reset token
    # 3. Send reset email
    
    return {
        "message": "Password reset endpoint - TODO: Implement",
        "email": email
    }
