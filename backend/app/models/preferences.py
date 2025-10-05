"""
User preferences models
"""

from sqlalchemy import Column, String, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel
from .news import NewsCategory


class NotificationFrequency(enum.Enum):
    """Notification frequency enumeration"""
    REALTIME = "realtime"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


class UserPreferences(BaseModel):
    """User preferences model"""
    __tablename__ = "user_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscribed_companies = Column(ARRAY(UUID), default=list)
    interested_categories = Column(ARRAY(Enum(NewsCategory)), default=list)
    keywords = Column(ARRAY(String), default=list)
    notification_frequency = Column(Enum(NotificationFrequency), default=NotificationFrequency.DAILY)
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    def __repr__(self) -> str:
        return f"<UserPreferences(id={self.id}, user_id={self.user_id})>"
