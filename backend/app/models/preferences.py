"""
User preferences models
"""

from sqlalchemy import Column, String, ForeignKey, Enum, Boolean, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.orm import relationship
import enum
from sqlalchemy import Enum as SQLEnum

from .base import BaseModel
from .news import NewsCategory, news_category_enum


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
    interested_categories = Column(ARRAY(news_category_enum), default=list)
    keywords = Column(ARRAY(String), default=list)
    notification_frequency = Column(
        SQLEnum(
            'realtime',
            'daily',
            'weekly',
            'never',
            name='notificationfrequency',
            create_type=False,
        ),
        default='daily',
    )
    
    # Digest settings
    digest_enabled = Column(Boolean, default=False)
    digest_frequency = Column(SQLEnum('daily', 'weekly', 'custom', name='digest_frequency'), default='daily')
    digest_custom_schedule = Column(JSON, default=dict)  # {"time": "09:00", "days": [1,2,3,4,5], "timezone": "UTC"}
    digest_format = Column(SQLEnum('short', 'detailed', name='digest_format'), default='short')
    digest_include_summaries = Column(Boolean, default=True)
    
    # Telegram integration
    telegram_chat_id = Column(String(255))
    telegram_enabled = Column(Boolean, default=False)
    telegram_digest_mode = Column(SQLEnum('all', 'tracked', name='telegram_digest_mode'), nullable=True, default='all')
    
    # Timezone and locale settings
    timezone = Column(String(50), default="UTC")  # e.g., "UTC", "America/New_York", "Europe/Moscow"
    week_start_day = Column(Integer, default=0)  # 0=Sunday, 1=Monday

    # Monitoring settings
    monitoring_enabled = Column(Boolean, default=True)
    monitoring_check_frequency = Column(
        SQLEnum('hourly', '6h', 'daily', 'weekly', name='monitoring_frequency'),
        default='daily',
    )
    monitoring_notify_on_changes = Column(Boolean, default=True)
    monitoring_change_types = Column(
        JSON,
        default=lambda: [
            'website_structure',
            'marketing_banner',
            'marketing_landing',
            'marketing_product',
            'marketing_jobs',
            'seo_meta',
            'seo_structure',
            'pricing',
        ],
    )
    monitoring_auto_refresh = Column(Boolean, default=True)
    monitoring_notification_channels = Column(
        JSON,
        default=lambda: {'email': True, 'telegram': False},
    )
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    def __repr__(self) -> str:
        return f"<UserPreferences(id={self.id}, user_id={self.user_id})>"
