"""
Enhanced User models with improved typing and validation
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import EmailStr, Field, validator
import uuid

from .base import BaseModel, BaseSchema, BaseResponseSchema


class User(BaseModel):
    """Enhanced User model with improved typing"""
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="User email address"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="Hashed password"
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="User's full name"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        nullable=False,
        comment="Whether user account is active"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        nullable=False,
        comment="Whether user email is verified"
    )
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="Token for email verification"
    )
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="Token for password reset"
    )
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="Password reset token expiration"
    )
    
    # Relationships
    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        "UserPreferences", 
        back_populates="user", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    activities: Mapped[List["UserActivity"]] = relationship(
        "UserActivity", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_verification_token', 'email_verification_token'),
        Index('idx_user_reset_token', 'password_reset_token'),
    )
    
    @property
    def is_password_reset_valid(self) -> bool:
        """Check if password reset token is still valid"""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        return datetime.utcnow() < self.password_reset_expires
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"


# Pydantic Schemas
class UserBaseSchema(BaseSchema):
    """Base user schema"""
    
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="User's full name")


class UserCreateSchema(UserBaseSchema):
    """Schema for user creation"""
    
    password: str = Field(..., min_length=8, description="User password")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdateSchema(BaseSchema):
    """Schema for user updates"""
    
    full_name: Optional[str] = Field(None, description="User's full name")
    is_active: Optional[bool] = Field(None, description="Whether user account is active")


class UserResponseSchema(BaseResponseSchema, UserBaseSchema):
    """Schema for user responses"""
    
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether user email is verified")


class UserLoginSchema(BaseSchema):
    """Schema for user login"""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class PasswordResetRequestSchema(BaseSchema):
    """Schema for password reset request"""
    
    email: EmailStr = Field(..., description="User email address")


class PasswordResetSchema(BaseSchema):
    """Schema for password reset"""
    
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class EmailVerificationSchema(BaseSchema):
    """Schema for email verification"""
    
    token: str = Field(..., description="Email verification token")
