"""
Onboarding models for user onboarding flow
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import enum
from uuid import UUID
from sqlalchemy import String, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import BaseModel, BaseSchema, BaseResponseSchema
from pydantic import Field


class OnboardingStep(str, enum.Enum):
    """Onboarding flow steps"""
    COMPANY_INPUT = "company_input"
    COMPANY_CARD = "company_card"
    COMPETITOR_SELECTION = "competitor_selection"
    OBSERVATION_SETUP = "observation_setup"
    SUBSCRIPTION_CONFIRM = "subscription_confirm"
    COMPLETED = "completed"


class OnboardingSession(BaseModel):
    """Onboarding session model for tracking user onboarding progress"""
    __tablename__ = "onboarding_sessions"
    
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User ID (null for anonymous sessions)"
    )
    session_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique session token for anonymous users"
    )
    current_step: Mapped[OnboardingStep] = mapped_column(
        ENUM(OnboardingStep, name="onboardingstep", create_type=False, values_callable=lambda enum_cls: [member.value for member in enum_cls]),
        nullable=False,
        server_default="'company_input'",
        index=True,
        comment="Current step in onboarding flow"
    )
    company_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Data about the parent company (name, website, description, logo, category, etc.)"
    )
    selected_competitors: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of selected competitors with their data"
    )
    observation_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Configuration for observation setup (task IDs, status, etc.)"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When onboarding was completed"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Session expiration time (default: 24 hours from creation)"
    )
    
    # Relationships
    user = relationship("User", backref="onboarding_sessions")
    
    # Indexes
    __table_args__ = (
        Index("idx_onboarding_session_token", "session_token"),
        Index("idx_onboarding_user_id", "user_id"),
        Index("idx_onboarding_current_step", "current_step"),
        Index("idx_onboarding_created_at", "created_at"),
        Index("idx_onboarding_expires_at", "expires_at"),
        UniqueConstraint("session_token", name="uq_onboarding_session_token"),
    )
    
    def __repr__(self) -> str:
        return f"<OnboardingSession(id={self.id}, user_id={self.user_id}, step={self.current_step.value}, token={self.session_token[:8]}...)>"


# Pydantic Schemas
class OnboardingStepSchema(BaseSchema):
    """Schema for onboarding step"""
    step: OnboardingStep = Field(..., description="Current onboarding step")


class OnboardingSessionBaseSchema(BaseSchema):
    """Base schema for onboarding session"""
    user_id: Optional[UUID] = Field(None, description="User ID (null for anonymous)")
    session_token: str = Field(..., description="Unique session token")
    current_step: OnboardingStep = Field(..., description="Current step in onboarding")
    company_data: Optional[Dict[str, Any]] = Field(None, description="Parent company data")
    selected_competitors: Optional[List[Dict[str, Any]]] = Field(None, description="Selected competitors")
    observation_config: Optional[Dict[str, Any]] = Field(None, description="Observation configuration")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class OnboardingSessionResponseSchema(BaseResponseSchema, OnboardingSessionBaseSchema):
    """Response schema for onboarding session"""
    pass


class OnboardingSessionCreateSchema(BaseSchema):
    """Schema for creating onboarding session"""
    user_id: Optional[UUID] = Field(None, description="User ID (if authenticated)")


class OnboardingSessionUpdateSchema(BaseSchema):
    """Schema for updating onboarding session"""
    current_step: Optional[OnboardingStep] = Field(None, description="Update current step")
    company_data: Optional[Dict[str, Any]] = Field(None, description="Update company data")
    selected_competitors: Optional[List[Dict[str, Any]]] = Field(None, description="Update selected competitors")
    observation_config: Optional[Dict[str, Any]] = Field(None, description="Update observation config")







