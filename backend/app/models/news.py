"""
Enhanced News models with improved typing and validation
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import Field, AnyUrl, validator
import enum

from .base import BaseModel, BaseSchema, BaseResponseSchema


class NewsCategory(str, enum.Enum):
    """Enhanced News category enumeration with descriptions"""
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
    
    @classmethod
    def get_descriptions(cls) -> Dict[str, str]:
        """Get human-readable descriptions for categories"""
        return {
            cls.PRODUCT_UPDATE: "Product updates and new features",
            cls.PRICING_CHANGE: "Pricing changes and plans",
            cls.STRATEGIC_ANNOUNCEMENT: "Strategic business announcements",
            cls.TECHNICAL_UPDATE: "Technical improvements and updates",
            cls.FUNDING_NEWS: "Funding rounds and investments",
            cls.RESEARCH_PAPER: "Research papers and publications",
            cls.COMMUNITY_EVENT: "Community events and meetups",
            cls.PARTNERSHIP: "Partnerships and collaborations",
            cls.ACQUISITION: "Company acquisitions and mergers",
            cls.INTEGRATION: "API integrations and partnerships",
            cls.SECURITY_UPDATE: "Security updates and patches",
            cls.API_UPDATE: "API changes and updates",
            cls.MODEL_RELEASE: "New AI model releases",
            cls.PERFORMANCE_IMPROVEMENT: "Performance improvements",
            cls.FEATURE_DEPRECATION: "Feature deprecations and removals",
        }


class SourceType(str, enum.Enum):
    """Enhanced Source type enumeration with descriptions"""
    BLOG = "blog"
    TWITTER = "twitter"
    GITHUB = "github"
    REDDIT = "reddit"
    NEWS_SITE = "news_site"
    PRESS_RELEASE = "press_release"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    
    @classmethod
    def get_descriptions(cls) -> Dict[str, str]:
        """Get human-readable descriptions for source types"""
        return {
            cls.BLOG: "Company blog posts",
            cls.TWITTER: "Twitter/X posts",
            cls.GITHUB: "GitHub repositories and releases",
            cls.REDDIT: "Reddit discussions",
            cls.NEWS_SITE: "News websites and articles",
            cls.PRESS_RELEASE: "Official press releases",
            cls.FACEBOOK: "Facebook posts and pages",
            cls.INSTAGRAM: "Instagram posts and profiles",
            cls.LINKEDIN: "LinkedIn company pages and posts",
            cls.YOUTUBE: "YouTube channels and videos",
            cls.TIKTOK: "TikTok profiles and videos",
        }


class NewsTopic(str, enum.Enum):
    """High-level NLP topic labels"""
    PRODUCT = "product"
    STRATEGY = "strategy"
    FINANCE = "finance"
    TECHNOLOGY = "technology"
    SECURITY = "security"
    RESEARCH = "research"
    COMMUNITY = "community"
    TALENT = "talent"
    REGULATION = "regulation"
    MARKET = "market"
    OTHER = "other"

    @classmethod
    def get_descriptions(cls) -> Dict[str, str]:
        """Get human-readable descriptions for topics"""
        return {
            cls.PRODUCT: "Product launches, feature updates and packaging changes",
            cls.STRATEGY: "Company strategy, positioning and GTM initiatives",
            cls.FINANCE: "Funding rounds, financial metrics and pricing moves",
            cls.TECHNOLOGY: "Technology stack, architecture and engineering updates",
            cls.SECURITY: "Security incidents, compliance and governance",
            cls.RESEARCH: "Research milestones, benchmarks and publications",
            cls.COMMUNITY: "Community programs, ecosystem and advocacy",
            cls.TALENT: "Hiring, leadership and organisational updates",
            cls.REGULATION: "Policy, regulations and governance news",
            cls.MARKET: "Market trends, competitive moves and customer wins",
            cls.OTHER: "Items that do not fit predefined topics",
        }


class SentimentLabel(str, enum.Enum):
    """Sentiment labels for NLP analysis"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"

    @classmethod
    def get_descriptions(cls) -> Dict[str, str]:
        """Get human-readable descriptions for sentiment labels"""
        return {
            cls.POSITIVE: "Overall positive sentiment",
            cls.NEUTRAL: "Neutral or informational sentiment",
            cls.NEGATIVE: "Negative sentiment or risks",
            cls.MIXED: "Mixed positive and negative signals",
        }


# Define PostgreSQL ENUMs that already exist in database
# Note: PostgreSQL stores enum values in UPPERCASE, but SQLAlchemy ENUM uses lowercase
# SQLAlchemy automatically converts between Python enum values (lowercase) and PostgreSQL (uppercase)
source_type_enum = ENUM(
    'blog', 'twitter', 'github', 'reddit', 'news_site', 'press_release',
    'facebook', 'instagram', 'linkedin', 'youtube', 'tiktok',
    name='sourcetype',
    create_type=False
)

news_category_enum = ENUM(
    'product_update', 'pricing_change', 'strategic_announcement', 
    'technical_update', 'funding_news', 'research_paper', 'community_event',
    'partnership', 'acquisition', 'integration', 'security_update',
    'api_update', 'model_release', 'performance_improvement', 'feature_deprecation',
    name='newscategory',
    create_type=False
)

news_topic_enum = ENUM(
    'product', 'strategy', 'finance', 'technology', 'security', 'research',
    'community', 'talent', 'regulation', 'market', 'other',
    name='newstopic',
    create_type=False
)

sentiment_enum = ENUM(
    'positive', 'neutral', 'negative', 'mixed',
    name='sentimentlabel',
    create_type=False
)


class NewsItem(BaseModel):
    """Enhanced News item model with improved typing"""
    __tablename__ = "news_items"
    
    title: Mapped[str] = mapped_column(
        String(500), 
        nullable=False,
        comment="News item title"
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Full content of the news item"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="AI-generated summary of the news item"
    )
    source_url: Mapped[str] = mapped_column(
        String(1000), 
        unique=True, 
        nullable=False,
        comment="Original URL of the news item"
    )
    source_type: Mapped[SourceType] = mapped_column(
        source_type_enum, 
        nullable=False,
        comment="Type of the news source"
    )
    company_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("companies.id"),
        comment="Associated company ID"
    )
    category: Mapped[Optional[NewsCategory]] = mapped_column(
        news_category_enum,
        comment="News category classification"
    )
    priority_score: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        nullable=False,
        comment="Priority score for news ranking (0.0-1.0)"
    )
    topic: Mapped[Optional[NewsTopic]] = mapped_column(
        news_topic_enum,
        nullable=True,
        comment="High-level NLP topic label"
    )
    sentiment: Mapped[Optional[SentimentLabel]] = mapped_column(
        sentiment_enum,
        nullable=True,
        comment="Sentiment label derived from NLP analysis"
    )
    raw_snapshot_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Link to stored raw HTML snapshot of the source page"
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False,
        comment="When the news was originally published"
    )
    
    # Full-text search
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        comment="Full-text search vector"
    )
    
    # Relationships
    company: Mapped[Optional["Company"]] = relationship(
        "Company", 
        back_populates="news_items"
    )
    keywords: Mapped[List["NewsKeyword"]] = relationship(
        "NewsKeyword", 
        back_populates="news_item",
        cascade="all, delete-orphan"
    )
    activities: Mapped[List["UserActivity"]] = relationship(
        "UserActivity",
        back_populates="news_item",
        cascade="all, delete-orphan"
    )
    nlp_logs: Mapped[List["NewsNLPLog"]] = relationship(
        "NewsNLPLog",
        back_populates="news_item",
        cascade="all, delete-orphan"
    )
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_news_company_published', 'company_id', 'published_at'),
        Index('idx_news_category_published', 'category', 'published_at'),
        Index('idx_news_source_type', 'source_type'),
        Index('idx_news_priority_score', 'priority_score'),
        Index('idx_news_published_at', 'published_at'),
        UniqueConstraint('source_url', name='uq_news_source_url'),
    )
    
    @property
    def title_truncated(self) -> str:
        """Get truncated title for display"""
        return self.title[:100] + "..." if len(self.title) > 100 else self.title
    
    @property
    def is_recent(self) -> bool:
        """Check if news is recent (within 24 hours)"""
        try:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if self.published_at:
                published = self.published_at if self.published_at.tzinfo else self.published_at.replace(tzinfo=timezone.utc)
                return (now - published).total_seconds() < 24 * 3600
            return False
        except (TypeError, ValueError):
            return False
    
    @property
    def priority_level(self) -> str:
        """Get human-readable priority level"""
        if self.priority_score >= 0.8:
            return "High"
        elif self.priority_score >= 0.6:
            return "Medium"
        else:
            return "Low"
    
    def __repr__(self) -> str:
        return f"<NewsItem(id={self.id}, title={self.title_truncated}, category={self.category})>"


# Pydantic Schemas
class NewsBaseSchema(BaseSchema):
    """Base news schema"""
    
    title: str = Field(..., max_length=500, description="News item title")
    content: Optional[str] = Field(None, description="Full content of the news item")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    source_url: AnyUrl = Field(..., description="Original URL of the news item")
    source_type: SourceType = Field(..., description="Type of the news source")
    company_id: Optional[str] = Field(None, description="Associated company ID")
    category: Optional[NewsCategory] = Field(None, description="News category")
    priority_score: float = Field(0.5, ge=0.0, le=1.0, description="Priority score")
    published_at: datetime = Field(..., description="Publication date")
    topic: Optional[NewsTopic] = Field(None, description="NLP topic classification")
    sentiment: Optional[SentimentLabel] = Field(None, description="Sentiment label")
    raw_snapshot_url: Optional[AnyUrl] = Field(None, description="Link to raw page snapshot for provenance")
    
    @validator('title')
    def validate_title(cls, v):
        """Validate title"""
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @validator('priority_score')
    def validate_priority_score(cls, v):
        """Validate priority score"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Priority score must be between 0.0 and 1.0')
        return v


class NewsCreateSchema(NewsBaseSchema):
    """Schema for creating news items"""
    pass


class NewsUpdateSchema(BaseSchema):
    """Schema for updating news items"""
    
    title: Optional[str] = Field(None, max_length=500, description="News item title")
    content: Optional[str] = Field(None, description="Full content")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    category: Optional[NewsCategory] = Field(None, description="News category")
    priority_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Priority score")
    topic: Optional[NewsTopic] = Field(None, description="NLP topic classification")
    sentiment: Optional[SentimentLabel] = Field(None, description="Sentiment label")
    raw_snapshot_url: Optional[AnyUrl] = Field(None, description="Link to raw page snapshot for provenance")


class NewsResponseSchema(BaseResponseSchema, NewsBaseSchema):
    """Schema for news responses"""
    
    title_truncated: str = Field(..., description="Truncated title for display")
    is_recent: bool = Field(..., description="Whether news is recent")
    priority_level: str = Field(..., description="Human-readable priority level")
    company_name: Optional[str] = Field(None, description="Company name")


class NewsSearchSchema(BaseSchema):
    """Schema for news search"""
    
    query: str = Field(..., min_length=1, description="Search query")
    category: Optional[NewsCategory] = Field(None, description="Filter by category")
    source_type: Optional[SourceType] = Field(None, description="Filter by source type")
    company_id: Optional[str] = Field(None, description="Filter by company")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    limit: int = Field(20, ge=1, le=100, description="Number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class NewsStatsSchema(BaseSchema):
    """Schema for news statistics"""
    
    total_count: int = Field(..., description="Total number of news items")
    category_counts: Dict[str, int] = Field(..., description="Count by category")
    source_type_counts: Dict[str, int] = Field(..., description="Count by source type")
    recent_count: int = Field(..., description="Number of recent news items")
    high_priority_count: int = Field(..., description="Number of high priority items")
