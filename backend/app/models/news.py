"""
News models
"""

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class NewsCategory(enum.Enum):
    """News category enumeration"""
    PRODUCT_UPDATE = "product_update"
    PRICING_CHANGE = "pricing_change"
    STRATEGIC_ANNOUNCEMENT = "strategic_announcement"
    TECHNICAL_UPDATE = "technical_update"
    FUNDING_NEWS = "funding_news"
    RESEARCH_PAPER = "research_paper"
    COMMUNITY_EVENT = "community_event"


class SourceType(enum.Enum):
    """Source type enumeration"""
    BLOG = "blog"
    TWITTER = "twitter"
    GITHUB = "github"
    REDDIT = "reddit"
    NEWS_SITE = "news_site"
    PRESS_RELEASE = "press_release"


class NewsItem(BaseModel):
    """News item model"""
    __tablename__ = "news_items"
    
    title = Column(String(500), nullable=False)
    content = Column(Text)
    summary = Column(Text)
    source_url = Column(String(1000), unique=True, nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    category = Column(Enum(NewsCategory))
    priority_score = Column(Float, default=0.5)
    published_at = Column(DateTime, nullable=False)
    
    # Full-text search
    search_vector = Column(TSVECTOR)
    
    # Relationships
    company = relationship("Company", back_populates="news_items")
    keywords = relationship("NewsKeyword", back_populates="news_item")
    activities = relationship("UserActivity", back_populates="news_item")
    
    def __repr__(self) -> str:
        return f"<NewsItem(id={self.id}, title={self.title[:50]}...)>"
