from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime
import enum

from sqlalchemy import String, Boolean, Float, ForeignKey, Index, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class NLPStage(str, enum.Enum):
    CLASSIFICATION = "classification"
    SENTIMENT = "sentiment"
    PRIORITY = "priority"
    SUMMARY = "summary"
    KEYWORDS = "keywords"


class NLPProvider(str, enum.Enum):
    HEURISTIC = "heuristic"
    OPENAI = "openai"
    SYSTEM = "system"


class NewsNLPLog(BaseModel):
    """Log entry for NLP processing of news items."""

    __tablename__ = "news_nlp_logs"

    news_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("news_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[NLPStage] = mapped_column(
        SAEnum(NLPStage, name="newsnlpstage"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    news_item: Mapped["NewsItem"] = relationship("NewsItem", back_populates="nlp_logs")

    __table_args__ = (
        Index("idx_news_nlp_logs_stage", "stage"),
        Index("idx_news_nlp_logs_provider", "provider"),
    )

    def __repr__(self) -> str:  # pragma: no cover - repr utility
        status = "ok" if self.success else "failed"
        return f"<NewsNLPLog(news_id={self.news_id}, stage={self.stage}, status={status})>"
