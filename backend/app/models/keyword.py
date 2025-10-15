"""
Keyword models
"""

from sqlalchemy import Column, String, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Use the same Base as other models
from .base import Base


class NewsKeyword(Base):
    """News keyword model - composite primary key (news_id, keyword)"""
    __tablename__ = "news_keywords"
    
    news_id = Column(UUID(as_uuid=True), ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    keyword = Column(String(100), nullable=False, primary_key=True)
    relevance_score = Column(Float, default=0.5)
    
    # Relationships
    news_item = relationship("NewsItem", back_populates="keywords")
    
    # Indexes
    __table_args__ = (
        Index('idx_keywords', 'keyword'),
    )
    
    def __repr__(self) -> str:
        return f"<NewsKeyword(news_id={self.news_id}, keyword={self.keyword})>"
