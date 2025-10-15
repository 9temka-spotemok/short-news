"""
Competitor analysis models
"""

from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.orm import relationship

from .base import BaseModel


class CompetitorComparison(BaseModel):
    """Competitor comparison model"""
    __tablename__ = "competitor_comparisons"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Array of company IDs being compared
    company_ids = Column(ARRAY(UUID), nullable=False)
    
    # Date range for comparison
    date_from = Column(DateTime, nullable=False)
    date_to = Column(DateTime, nullable=False)
    
    # Comparison name/title
    name = Column(String(255))
    
    # Cached metrics (JSON)
    # Structure: {
    #   "news_volume": {"company_id": count},
    #   "category_distribution": {"company_id": {"category": count}},
    #   "activity_score": {"company_id": score}
    # }
    metrics = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", backref="competitor_comparisons")
    
    def __repr__(self) -> str:
        return f"<CompetitorComparison(id={self.id}, user_id={self.user_id}, companies={len(self.company_ids)})>"



