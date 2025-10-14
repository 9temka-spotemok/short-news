"""
User preferences models
"""

from sqlalchemy import Column, String, ForeignKey, Enum, Boolean, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
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


class DigestFrequency(enum.Enum):
    """Digest frequency enumeration"""
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class DigestFormat(enum.Enum):
    """Digest format enumeration"""
    SHORT = "short"
    DETAILED = "detailed"


class UserPreferences(BaseModel):
    """User preferences model"""
    __tablename__ = "user_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscribed_companies = Column(ARRAY(UUID), default=list)
    interested_categories = Column(ARRAY(Enum(NewsCategory)), default=list)
    keywords = Column(ARRAY(String), default=list)
    notification_frequency = Column(Enum(NotificationFrequency), default=NotificationFrequency.DAILY)
    
    # Digest settings
    digest_enabled = Column(Boolean, default=False)
    digest_frequency = Column(Enum(DigestFrequency), default=DigestFrequency.DAILY)
    digest_custom_schedule = Column(JSON, default=dict)  # {"time": "09:00", "days": [1,2,3,4,5], "timezone": "UTC"}
    digest_format = Column(Enum(DigestFormat), default=DigestFormat.SHORT)
    digest_include_summaries = Column(Boolean, default=True)
    
    # Telegram integration
    telegram_chat_id = Column(String(255))
    telegram_enabled = Column(Boolean, default=False)
    
    # Timezone and locale settings
    timezone = Column(String(50), default="UTC")  # e.g., "UTC", "America/New_York", "Europe/Moscow"
    week_start_day = Column(Integer, default=0)  # 0=Sunday, 1=Monday
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    def __repr__(self) -> str:
        return f"<UserPreferences(id={self.id}, user_id={self.user_id})>"
