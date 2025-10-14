"""
Notification endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from loguru import logger
import uuid

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models import User, Notification, NotificationSettings
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/")
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user notifications with pagination
    """
    logger.info(f"Get notifications request from user {current_user.id}")
    
    try:
        # Build query
        query = select(Notification).where(Notification.user_id == current_user.id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        
        # Get notifications
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        # Get total count
        count_query = select(Notification).where(Notification.user_id == current_user.id)
        if unread_only:
            count_query = count_query.where(Notification.is_read == False)
        
        from sqlalchemy import func
        total_result = await db.execute(
            select(func.count()).select_from(count_query.subquery())
        )
        total = total_result.scalar()
        
        return {
            "notifications": [
                {
                    "id": str(n.id),
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "data": n.data,
                    "is_read": n.is_read,
                    "priority": n.priority,
                    "created_at": n.created_at.isoformat()
                }
                for n in notifications
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.get("/unread")
async def get_unread_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get unread notifications count and latest items
    """
    logger.info(f"Get unread notifications from user {current_user.id}")
    
    try:
        # Get unread notifications
        result = await db.execute(
            select(Notification)
            .where(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.is_read == False
                )
            )
            .order_by(desc(Notification.created_at))
            .limit(10)
        )
        notifications = result.scalars().all()
        
        # Get total unread count
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.is_read == False
                )
            )
        )
        unread_count = count_result.scalar()
        
        return {
            "unread_count": unread_count,
            "notifications": [
                {
                    "id": str(n.id),
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "data": n.data,
                    "priority": n.priority,
                    "created_at": n.created_at.isoformat()
                }
                for n in notifications
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching unread notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch unread notifications")


@router.put("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a notification as read
    """
    logger.info(f"Mark notification {notification_id} as read for user {current_user.id}")
    
    try:
        notification_service = NotificationService(db)
        success = await notification_service.mark_as_read(notification_id, str(current_user.id))
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"status": "success", "message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")


@router.put("/mark-all-read")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all notifications as read for current user
    """
    logger.info(f"Mark all notifications as read for user {current_user.id}")
    
    try:
        notification_service = NotificationService(db)
        count = await notification_service.mark_all_as_read(str(current_user.id))
        
        return {
            "status": "success",
            "message": f"{count} notifications marked as read"
        }
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notifications as read")


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a notification
    """
    logger.info(f"Delete notification {notification_id} for user {current_user.id}")
    
    try:
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == uuid.UUID(notification_id),
                    Notification.user_id == current_user.id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        await db.delete(notification)
        await db.commit()
        
        return {"status": "success", "message": "Notification deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete notification")


@router.get("/settings")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user notification settings
    """
    logger.info(f"Get notification settings for user {current_user.id}")
    
    try:
        result = await db.execute(
            select(NotificationSettings).where(NotificationSettings.user_id == current_user.id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            # Create default settings
            settings = NotificationSettings(
                id=uuid.uuid4(),
                user_id=current_user.id,
                enabled=True,
                notification_types={},
                min_priority_score=0,
                company_alerts=True,
                category_trends=True,
                keyword_alerts=True
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        
        return {
            "id": str(settings.id),
            "enabled": settings.enabled,
            "notification_types": settings.notification_types,
            "min_priority_score": settings.min_priority_score,
            "company_alerts": settings.company_alerts,
            "category_trends": settings.category_trends,
            "keyword_alerts": settings.keyword_alerts
        }
        
    except Exception as e:
        logger.error(f"Error fetching notification settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notification settings")


@router.put("/settings")
async def update_notification_settings(
    enabled: Optional[bool] = None,
    notification_types: Optional[dict] = None,
    min_priority_score: Optional[int] = None,
    company_alerts: Optional[bool] = None,
    category_trends: Optional[bool] = None,
    keyword_alerts: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user notification settings
    """
    logger.info(f"Update notification settings for user {current_user.id}")
    
    try:
        result = await db.execute(
            select(NotificationSettings).where(NotificationSettings.user_id == current_user.id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            # Create new settings
            settings = NotificationSettings(
                id=uuid.uuid4(),
                user_id=current_user.id,
                enabled=enabled if enabled is not None else True,
                notification_types=notification_types or {},
                min_priority_score=min_priority_score or 0,
                company_alerts=company_alerts if company_alerts is not None else True,
                category_trends=category_trends if category_trends is not None else True,
                keyword_alerts=keyword_alerts if keyword_alerts is not None else True
            )
            db.add(settings)
        else:
            # Update existing settings
            if enabled is not None:
                settings.enabled = enabled
            if notification_types is not None:
                settings.notification_types = notification_types
            if min_priority_score is not None:
                settings.min_priority_score = min_priority_score
            if company_alerts is not None:
                settings.company_alerts = company_alerts
            if category_trends is not None:
                settings.category_trends = category_trends
            if keyword_alerts is not None:
                settings.keyword_alerts = keyword_alerts
        
        await db.commit()
        await db.refresh(settings)
        
        return {
            "status": "success",
            "settings": {
                "id": str(settings.id),
                "enabled": settings.enabled,
                "notification_types": settings.notification_types,
                "min_priority_score": settings.min_priority_score,
                "company_alerts": settings.company_alerts,
                "category_trends": settings.category_trends,
                "keyword_alerts": settings.keyword_alerts
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update notification settings")

