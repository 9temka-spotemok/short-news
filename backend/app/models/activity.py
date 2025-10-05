"""
User activity models
"""

from sqlalchemy import Column, String, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class ActivityType(enum.Enum):
    """Activity type enumeration"""
    VIEWED = "viewed"
    FAVORITED = "favorited"
    MARKED_READ = "marked_read"
    SHARED = "shared"


class UserActivity(BaseModel):
    """User activity model"""
    __tablename__ = "user_activity"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    news_id = Column(UUID(as_uuid=True), ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False)
    action = Column(Enum(ActivityType), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="activities")
    news_item = relationship("NewsItem", back_populates="activities")
    
    def __repr__(self) -> str:
        return f"<UserActivity(id={self.id}, user_id={self.user_id}, action={self.action})>"
