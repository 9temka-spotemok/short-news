"""
Scraper state models
"""

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel


class ScraperState(BaseModel):
    """Scraper state model"""
    __tablename__ = "scraper_state"
    
    source_id = Column(String(255), primary_key=True)
    last_scraped_at = Column(DateTime)
    last_item_id = Column(String(500))
    status = Column(String(50), default="active")  # active, paused, error
    error_message = Column(Text)
    
    def __repr__(self) -> str:
        return f"<ScraperState(source_id={self.source_id}, status={self.status})>"
