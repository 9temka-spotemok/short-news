"""
Subscription service for managing user subscriptions and trials
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from decimal import Decimal

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.core.config import settings


class SubscriptionService:
    """Service for managing subscriptions and trials"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_trial_subscription(self, user_id: UUID, user_email: Optional[str] = None) -> Subscription:
        """
        Create a trial subscription for 3 days
        
        Args:
            user_id: User ID
            user_email: Optional user email for dev environment checks
            
        Returns:
            Subscription object with trial
        """
        # Check if subscription already exists
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"Subscription already exists for user {user_id}")
            return existing
        
        now = datetime.now(timezone.utc)
        
        # Dev environment protection: create infinite trial for dev users
        if settings.DISABLE_SUBSCRIPTION_CHECK:
            trial_ends_at = None  # Infinite trial
            logger.info(f"Creating infinite trial for dev environment (user {user_id})")
        elif user_email and user_email.lower() in [email.lower() for email in settings.SUBSCRIPTION_DEV_USERS]:
            trial_ends_at = None  # Infinite trial
            logger.info(f"Creating infinite trial for dev user {user_email}")
        else:
            trial_ends_at = now + timedelta(days=3)
        
        subscription = Subscription(
            user_id=user_id,
            status=SubscriptionStatus.TRIAL.value,
            plan_type="monthly",
            price=Decimal("29.00"),
            currency="USD",
            trial_started_at=now,
            trial_ends_at=trial_ends_at,
            subscription_metadata={}
        )
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(
            f"Created trial subscription for user {user_id}, "
            f"expires at {trial_ends_at if trial_ends_at else 'never (dev)'}"
        )
        
        return subscription
    
    async def check_subscription_access(self, user_id: UUID, user_email: Optional[str] = None) -> bool:
        """
        Check if user has active subscription or trial
        
        Args:
            user_id: User ID
            user_email: Optional user email for dev environment checks
            
        Returns:
            True if user has active subscription/trial, False otherwise
        """
        # Dev environment protection: always allow access
        if settings.DISABLE_SUBSCRIPTION_CHECK:
            return True
        
        # Dev users protection: always allow access
        if user_email and user_email.lower() in [email.lower() for email in settings.SUBSCRIPTION_DEV_USERS]:
            return True
        
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return False
        
        return subscription.is_active(user_email=user_email)
    
    async def activate_subscription(
        self, 
        subscription_id: UUID, 
        payment_data: dict,
        user_email: Optional[str] = None
    ) -> Subscription:
        """
        Activate subscription after payment
        
        Args:
            subscription_id: Subscription ID
            payment_data: Payment data (provider, payment_subscription_id)
            user_email: Optional user email for dev environment checks
            
        Returns:
            Updated Subscription object
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)  # Monthly subscription
        
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.started_at = now
        subscription.expires_at = expires_at
        subscription.payment_provider = payment_data.get("provider")
        subscription.payment_subscription_id = payment_data.get("payment_subscription_id")
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Activated subscription {subscription_id} for user {subscription.user_id}")
        
        return subscription
    
    async def cancel_subscription(self, subscription_id: UUID) -> Subscription:
        """
        Cancel subscription
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Updated Subscription object
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        subscription.status = SubscriptionStatus.CANCELLED.value
        subscription.cancelled_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Cancelled subscription {subscription_id} for user {subscription.user_id}")
        
        return subscription
    
    async def get_user_subscription(self, user_id: UUID) -> Optional[Subscription]:
        """
        Get current subscription for user
        
        Args:
            user_id: User ID
            
        Returns:
            Subscription object or None
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def expire_trials(self) -> int:
        """
        Mark expired trials as EXPIRED
        
        Returns:
            Number of updated subscriptions
        """
        # Skip expiration check in dev environment
        if settings.DISABLE_SUBSCRIPTION_CHECK:
            logger.debug("Skipping trial expiration check (dev environment)")
            return 0
        
        now = datetime.now(timezone.utc)
        
        # Get expired trials (excluding dev users)
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.TRIAL.value,
                Subscription.trial_ends_at.isnot(None),
                Subscription.trial_ends_at < now
            )
        )
        expired_trials = result.scalars().all()
        
        # Filter out dev users
        expired_count = 0
        for subscription in expired_trials:
            # Get user email to check if dev user
            user_result = await self.db.execute(
                select(User).where(User.id == subscription.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user and user.email.lower() in [email.lower() for email in settings.SUBSCRIPTION_DEV_USERS]:
                continue  # Skip dev users
            
            subscription.status = SubscriptionStatus.EXPIRED.value
            expired_count += 1
        
        if expired_count > 0:
            await self.db.commit()
            logger.info(f"Expired {expired_count} trial subscriptions")
        
        return expired_count
    
    async def expire_subscriptions(self) -> int:
        """
        Mark expired subscriptions as EXPIRED
        
        Returns:
            Number of updated subscriptions
        """
        # Skip expiration check in dev environment
        if settings.DISABLE_SUBSCRIPTION_CHECK:
            logger.debug("Skipping subscription expiration check (dev environment)")
            return 0
        
        now = datetime.now(timezone.utc)
        
        # Get expired subscriptions (excluding dev users)
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.expires_at.isnot(None),
                Subscription.expires_at < now
            )
        )
        expired_subscriptions = result.scalars().all()
        
        # Filter out dev users
        expired_count = 0
        for subscription in expired_subscriptions:
            # Get user email to check if dev user
            user_result = await self.db.execute(
                select(User).where(User.id == subscription.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user and user.email.lower() in [email.lower() for email in settings.SUBSCRIPTION_DEV_USERS]:
                continue  # Skip dev users
            
            subscription.status = SubscriptionStatus.EXPIRED.value
            expired_count += 1
        
        if expired_count > 0:
            await self.db.commit()
            logger.info(f"Expired {expired_count} active subscriptions")
        
        return expired_count

