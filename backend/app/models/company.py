"""
Company models
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import Column, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import BaseModel


class Company(BaseModel):
    """Company model"""
    __tablename__ = "companies"
    
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="User ID for data isolation (null for global companies)"
    )
    name = Column(String(255), nullable=False, index=True)
    website = Column(String(500))
    description = Column(Text)
    logo_url = Column(String(500))
    category = Column(String(100))  # llm_provider, search_engine, toolkit, etc.
    twitter_handle = Column(String(100))
    github_org = Column(String(100))
    
    # Social media URLs
    facebook_url = Column(String(500))
    instagram_url = Column(String(500))
    linkedin_url = Column(String(500))
    youtube_url = Column(String(500))
    tiktok_url = Column(String(500))
    
    # Relationships
    news_items = relationship("NewsItem", back_populates="company")
    
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_companies_name_user"),
    )
    
    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name}, user_id={self.user_id})>"
