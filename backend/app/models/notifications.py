"""
Notification models
"""

from sqlalchemy import Column, String, ForeignKey, Enum, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class NotificationType(str, enum.Enum):
    """Notification type enumeration"""
    NEW_NEWS = "new_news"
    COMPANY_ACTIVE = "company_active"
    PRICING_CHANGE = "pricing_change"
    FUNDING_ANNOUNCEMENT = "funding_announcement"
    PRODUCT_LAUNCH = "product_launch"
    CATEGORY_TREND = "category_trend"
    KEYWORD_MATCH = "keyword_match"
    COMPETITOR_MILESTONE = "competitor_milestone"


class NotificationPriority(str, enum.Enum):
    """Notification priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NotificationSettings(BaseModel):
    """User notification settings model"""
    __tablename__ = "notification_settings"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    
    # Notification types configuration (JSON with enabled/disabled per type)
    notification_types = Column(JSON, default=dict)
    
    # Minimum priority score for news notifications
    min_priority_score = Column(Integer, default=0)
    
    # Company alerts (notify when these companies have news)
    company_alerts = Column(Boolean, default=True)
    
    # Category trends (notify about trends in categories)
    category_trends = Column(Boolean, default=True)
    
    # Keyword alerts (notify on keyword matches)
    keyword_alerts = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", backref="notification_settings")
    
    def __repr__(self) -> str:
        return f"<NotificationSettings(id={self.id}, user_id={self.user_id})>"


class Notification(BaseModel):
    """Notification model"""
    __tablename__ = "notifications"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Additional data (JSON) - e.g., news_id, company_id, etc.
    data = Column(JSON, default=dict)
    
    is_read = Column(Boolean, default=False, index=True)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)
    
    # Relationships
    user = relationship("User", backref="notifications")
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.type}, user_id={self.user_id})>"



