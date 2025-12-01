"""
Subscription endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models import User, Subscription, SubscriptionStatus
from app.services.subscription_service import SubscriptionService

router = APIRouter()


class SubscriptionResponse(BaseModel):
    """Subscription response model"""
    id: str
    status: str
    plan_type: str
    price: float
    currency: str
    trial_started_at: Optional[str] = None
    trial_ends_at: Optional[str] = None
    started_at: Optional[str] = None
    expires_at: Optional[str] = None
    days_remaining: int
    is_active: bool


class SubscriptionAccessResponse(BaseModel):
    """Subscription access check response"""
    has_access: bool
    days_remaining: Optional[int] = None
    reason: Optional[str] = None
    status: Optional[str] = None


class CreateSubscriptionRequest(BaseModel):
    """Request model for subscription creation/activation"""
    payment_provider: str = Field(..., description="Payment provider (stripe, paypal, etc.)")
    payment_subscription_id: str = Field(..., description="Subscription ID in payment system")
    subscription_id: Optional[str] = Field(None, description="Existing subscription ID to activate")


@router.get("/current")
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current subscription for authenticated user
    
    Returns:
        Subscription data or null if no subscription exists
    """
    service = SubscriptionService(db)
    subscription = await service.get_user_subscription(current_user.id)
    
    if not subscription:
        return {"subscription": None}
    
    return {
        "subscription": {
            "id": str(subscription.id),
            "status": subscription.status,
            "plan_type": subscription.plan_type,
            "price": float(subscription.price),
            "currency": subscription.currency,
            "trial_started_at": subscription.trial_started_at.isoformat() if subscription.trial_started_at else None,
            "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
            "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "days_remaining": subscription.days_remaining(user_email=current_user.email),
            "is_active": subscription.is_active(user_email=current_user.email)
        }
    }


@router.post("/create")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or activate subscription after payment
    
    Request body:
        - payment_provider: str (stripe, paypal, etc.)
        - payment_subscription_id: str
        - subscription_id: UUID (optional, if updating existing)
    
    Returns:
        Subscription data
    """
    service = SubscriptionService(db)
    
    payment_data = {
        "provider": request.payment_provider,
        "payment_subscription_id": request.payment_subscription_id
    }
    
    subscription_id = request.subscription_id
    
    if subscription_id:
        # Activate existing subscription
        try:
            subscription = await service.activate_subscription(
                UUID(subscription_id),
                payment_data,
                user_email=current_user.email
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    else:
        # Get or create subscription
        existing = await service.get_user_subscription(current_user.id)
        if existing:
            subscription = await service.activate_subscription(
                existing.id,
                payment_data,
                user_email=current_user.email
            )
        else:
            # Create trial first, then activate (unusual scenario)
            trial = await service.create_trial_subscription(
                current_user.id,
                user_email=current_user.email
            )
            subscription = await service.activate_subscription(
                trial.id,
                payment_data,
                user_email=current_user.email
            )
    
    return {
        "subscription": {
            "id": str(subscription.id),
            "status": subscription.status,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
        }
    }


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel user's subscription
    
    Returns:
        Confirmation of cancellation
    """
    service = SubscriptionService(db)
    subscription = await service.get_user_subscription(current_user.id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    try:
        await service.cancel_subscription(subscription.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return {"status": "cancelled", "message": "Subscription cancelled successfully"}


@router.get("/check-access")
async def check_subscription_access(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check user's access to features
    
    Returns:
        has_access: bool
        reason: str (if no access)
        days_remaining: int (if has access)
        status: str (subscription status)
    """
    service = SubscriptionService(db)
    has_access = await service.check_subscription_access(
        current_user.id,
        user_email=current_user.email
    )
    
    if has_access:
        subscription = await service.get_user_subscription(current_user.id)
        days_remaining = subscription.days_remaining(user_email=current_user.email) if subscription else 0
        
        return {
            "has_access": True,
            "days_remaining": days_remaining,
            "status": subscription.status if subscription else None
        }
    else:
        subscription = await service.get_user_subscription(current_user.id)
        
        if not subscription:
            reason = "No subscription found. Please complete onboarding to start trial."
        elif subscription.status == SubscriptionStatus.EXPIRED.value:
            reason = "Your trial/subscription has expired. Please subscribe to continue."
        elif subscription.status == SubscriptionStatus.CANCELLED.value:
            reason = "Your subscription was cancelled. Please subscribe to continue."
        else:
            reason = "Access denied. Please check your subscription status."
        
        return {
            "has_access": False,
            "reason": reason,
            "status": subscription.status if subscription else None
        }

