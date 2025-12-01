"""
Subscription models
"""

from enum import Enum
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID as PyUUID
from typing import Optional

from app.models.base import BaseModel


class SubscriptionStatus(str, Enum):
    """Subscription status enum"""
    TRIAL = "trial"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Subscription(BaseModel):
    """Subscription model for user subscriptions and trials"""
    __tablename__ = "subscriptions"
    
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="User ID (one-to-one relationship)"
    )
    
    # Status and plan
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SubscriptionStatus.TRIAL.value,
        index=True,
        comment="Subscription status: trial, active, cancelled, expired"
    )
    plan_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="monthly",
        comment="Subscription plan type: monthly, yearly"
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("29.00"),
        comment="Subscription price"
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
        comment="Currency code (USD, EUR, etc.)"
    )
    
    # Trial dates
    trial_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Trial start date"
    )
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Trial end date"
    )
    
    # Subscription dates
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Subscription start date"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Subscription expiration date"
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Subscription cancellation date"
    )
    
    # Payment data
    payment_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Payment provider: stripe, paypal, etc."
    )
    payment_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Subscription ID in payment system"
    )
    
    # Metadata
    subscription_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional metadata"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="subscription",
        uselist=False
    )
    
    __table_args__ = (
        Index('idx_subscription_user_id', 'user_id'),
        Index('idx_subscription_status', 'status'),
        Index('idx_subscription_trial_ends_at', 'trial_ends_at'),
        Index('idx_subscription_expires_at', 'expires_at'),
        {"comment": "User subscriptions and trials"}
    )
    
    def is_active(self, user_email: Optional[str] = None) -> bool:
        """
        Check if subscription or trial is active
        
        Args:
            user_email: Optional user email for dev environment checks
            
        Returns:
            True if subscription/trial is active, False otherwise
        """
        # Import here to avoid circular dependency
        from app.core.config import settings
        
        # Dev environment protection: if subscription check is disabled, always return True
        if settings.DISABLE_SUBSCRIPTION_CHECK:
            return True
        
        # Dev users protection: if user email is in dev users list, always return True
        if user_email and user_email.lower() in [email.lower() for email in settings.SUBSCRIPTION_DEV_USERS]:
            return True
        
        # Normal checks
        if self.status == SubscriptionStatus.EXPIRED.value:
            return False
        if self.status == SubscriptionStatus.CANCELLED.value:
            return False
        
        now = datetime.now(timezone.utc)
        
        # Check trial
        if self.status == SubscriptionStatus.TRIAL.value:
            if self.trial_ends_at and self.trial_ends_at < now:
                return False
            return True
        
        # Check active subscription
        if self.status == SubscriptionStatus.ACTIVE.value:
            if self.expires_at and self.expires_at < now:
                return False
            return True
        
        return False
    
    def days_remaining(self, user_email: Optional[str] = None) -> int:
        """
        Get number of days remaining until trial or subscription expires
        
        Args:
            user_email: Optional user email for dev environment checks
            
        Returns:
            Number of days remaining (0 if expired or inactive, 9999 if dev user)
        """
        # Import here to avoid circular dependency
        from app.core.config import settings
        
        # Dev environment protection: return large number for dev users
        if settings.DISABLE_SUBSCRIPTION_CHECK:
            return 9999
        
        if user_email and user_email.lower() in [email.lower() for email in settings.SUBSCRIPTION_DEV_USERS]:
            return 9999
        
        if not self.is_active(user_email):
            return 0
        
        now = datetime.now(timezone.utc)
        
        if self.status == SubscriptionStatus.TRIAL.value and self.trial_ends_at:
            delta = self.trial_ends_at - now
            return max(0, delta.days)
        
        if self.status == SubscriptionStatus.ACTIVE.value and self.expires_at:
            delta = self.expires_at - now
            return max(0, delta.days)
        
        return 0
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status={self.status})>"

