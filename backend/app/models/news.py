"""
News models
"""

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum, TypeDecorator, types
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR, ENUM
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class NewsCategory(str, enum.Enum):
    """News category enumeration"""
    PRODUCT_UPDATE = "product_update"
    PRICING_CHANGE = "pricing_change"
    STRATEGIC_ANNOUNCEMENT = "strategic_announcement"
    TECHNICAL_UPDATE = "technical_update"
    FUNDING_NEWS = "funding_news"
    RESEARCH_PAPER = "research_paper"
    COMMUNITY_EVENT = "community_event"
    PARTNERSHIP = "partnership"
    ACQUISITION = "acquisition"
    INTEGRATION = "integration"
    SECURITY_UPDATE = "security_update"
    API_UPDATE = "api_update"
    MODEL_RELEASE = "model_release"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    FEATURE_DEPRECATION = "feature_deprecation"


class SourceType(str, enum.Enum):
    """Source type enumeration"""
    BLOG = "blog"
    TWITTER = "twitter"
    GITHUB = "github"
    REDDIT = "reddit"
    NEWS_SITE = "news_site"
    PRESS_RELEASE = "press_release"


# Define PostgreSQL ENUMs that already exist in database
source_type_enum = ENUM(
    'blog', 'twitter', 'github', 'reddit', 'news_site', 'press_release',
    name='source_type',
    create_type=False
)

news_category_enum = ENUM(
    'product_update', 'pricing_change', 'strategic_announcement', 
    'technical_update', 'funding_news', 'research_paper', 'community_event',
    'partnership', 'acquisition', 'integration', 'security_update',
    'api_update', 'model_release', 'performance_improvement', 'feature_deprecation',
    name='news_category',
    create_type=False
)


class NewsItem(BaseModel):
    """News item model"""
    __tablename__ = "news_items"
    
    title = Column(String(500), nullable=False)
    content = Column(Text)
    summary = Column(Text)
    source_url = Column(String(1000), unique=True, nullable=False)
    source_type = Column(source_type_enum, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    category = Column(news_category_enum)
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
