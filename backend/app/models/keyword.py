"""
Keyword models
"""

from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class NewsKeyword(BaseModel):
    """News keyword model"""
    __tablename__ = "news_keywords"
    
    news_id = Column(UUID(as_uuid=True), ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False)
    keyword = Column(String(100), nullable=False)
    relevance_score = Column(Float, default=0.5)
    
    # Relationships
    news_item = relationship("NewsItem", back_populates="keywords")
    
    def __repr__(self) -> str:
        return f"<NewsKeyword(id={self.id}, keyword={self.keyword})>"
