"""
Extended notification delivery models covering channels, subscriptions, events and deliveries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from .base import BaseModel
from .notifications import NotificationPriority, NotificationType
from .user import User


def enum_values(enum_cls):
    """Return enum values preserving definition order."""
    return [member.value for member in enum_cls]


class NotificationChannelType(str, enum.Enum):
    """Supported outbound notification channels."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    SLACK = "slack"
    ZAPIER = "zapier"


class NotificationDeliveryStatus(str, enum.Enum):
    """Delivery attempt status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class NotificationEventStatus(str, enum.Enum):
    """Notification event lifecycle status."""

    QUEUED = "queued"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    FAILED = "failed"
    SUPPRESSED = "suppressed"
    EXPIRED = "expired"


class NotificationChannel(BaseModel):
    """Represents a verified notification channel for a user."""

    __tablename__ = "notification_channels"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_type = Column(
        Enum(NotificationChannelType, name="notificationchanneltype", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    destination = Column(String(500), nullable=False)
    metadata_json = Column("metadata", JSON, default=dict)
    is_verified = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    disabled = Column(Boolean, nullable=False, default=False)

    user = relationship(User, backref="notification_channels")

    __table_args__ = (
        UniqueConstraint("user_id", "channel_type", "destination", name="uq_notification_channel_destination"),
    )


class NotificationSubscription(BaseModel):
    """User subscription preferences per channel and notification type."""

    __tablename__ = "notification_subscriptions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(
        Enum(NotificationType, name="notification_type", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    enabled = Column(Boolean, nullable=False, default=True)
    frequency = Column(String(50), nullable=False, default="immediate")
    min_priority = Column(
        Enum(NotificationPriority, name="notification_priority", values_callable=enum_values),
        nullable=False,
        default=NotificationPriority.MEDIUM,
    )
    filters = Column(JSON, default=dict)

    user = relationship(User, backref="notification_subscriptions")
    channel = relationship(NotificationChannel, backref="subscriptions")

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", "notification_type", name="uq_notification_subscription"),
    )


class NotificationEvent(BaseModel):
    """Recorded notification event before channel fan-out."""

    __tablename__ = "notification_events"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(
        Enum(NotificationType, name="notification_type", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    priority = Column(
        Enum(NotificationPriority, name="notification_priority", values_callable=enum_values),
        nullable=False,
        default=NotificationPriority.MEDIUM,
    )
    payload = Column(JSON, default=dict)
    deduplication_key = Column(String(255), index=True)
    status = Column(
        Enum(NotificationEventStatus, name="notificationeventstatus", values_callable=enum_values),
        nullable=False,
        default=NotificationEventStatus.QUEUED,
        index=True,
    )
    scheduled_for = Column(DateTime(timezone=True))
    dispatched_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    error_message = Column(String(1000))

    user = relationship(User, backref="notification_events")


class NotificationDelivery(BaseModel):
    """Individual delivery attempt for a notification event and channel."""

    __tablename__ = "notification_deliveries"

    event_id = Column(UUID(as_uuid=True), ForeignKey("notification_events.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        Enum(NotificationDeliveryStatus, name="notificationdeliverystatus", values_callable=enum_values),
        nullable=False,
        default=NotificationDeliveryStatus.PENDING,
        index=True,
    )
    attempt = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True))
    next_retry_at = Column(DateTime(timezone=True))
    response_metadata = Column(JSON, default=dict)
    error_message = Column(String(1000))

    event = relationship(NotificationEvent, backref="deliveries")
    channel = relationship(NotificationChannel, backref="deliveries")


