"""
Company models
"""

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel


class Company(BaseModel):
    """Company model"""
    __tablename__ = "companies"
    
    name = Column(String(255), unique=True, nullable=False, index=True)
    website = Column(String(500))
    description = Column(Text)
    logo_url = Column(String(500))
    category = Column(String(100))  # llm_provider, search_engine, toolkit, etc.
    twitter_handle = Column(String(100))
    github_org = Column(String(100))
    
    # Relationships
    news_items = relationship("NewsItem", back_populates="company")
    
    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name})>"
