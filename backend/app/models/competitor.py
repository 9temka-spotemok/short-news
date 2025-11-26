"""
Competitor analysis models
"""

from __future__ import annotations

import enum
from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from .news import SourceType, source_type_enum


class ChangeProcessingStatus(str, enum.Enum):
    """Status of change detection processing."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    ERROR = "error"


class ChangeNotificationStatus(str, enum.Enum):
    """Notification delivery status for change events."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


processing_status_enum = Enum(
    ChangeProcessingStatus,
    name="competitorprocessingstatus",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
    native_enum=True,
    create_type=False,
)

notification_status_enum = Enum(
    ChangeNotificationStatus,
    name="competitornotificationstatus",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
    native_enum=True,
    create_type=False,
)


class CompetitorComparison(BaseModel):
    """Competitor comparison model."""

    __tablename__ = "competitor_comparisons"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Array of company IDs being compared
    company_ids: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID), nullable=False)

    # Date range for comparison
    date_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Comparison name/title
    name: Mapped[Optional[str]] = mapped_column(String(255))

    # Cached metrics (JSON)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    user = relationship("User", backref="competitor_comparisons")

    def __repr__(self) -> str:
        return (
            f"<CompetitorComparison(id={self.id}, user_id={self.user_id}, "
            f"companies={len(self.company_ids)})>"
        )


class CompetitorPricingSnapshot(BaseModel):
    """Raw and normalized pricing snapshot for a competitor."""

    __tablename__ = "competitor_pricing_snapshots"
    __table_args__ = (
        Index(
            "ix_competitor_pricing_snapshot_company_url",
            "company_id",
            "source_url",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        source_type_enum, nullable=False
    )
    data_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    normalized_data: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )
    raw_snapshot_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    extraction_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict
    )
    warnings: Mapped[List[str]] = mapped_column(JSON, default=list)
    processing_status: Mapped[ChangeProcessingStatus] = mapped_column(
        processing_status_enum.copy(),
        default=ChangeProcessingStatus.SUCCESS,
        nullable=False,
    )
    processing_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company = relationship("Company", backref="pricing_snapshots")
    change_events = relationship(
        "CompetitorChangeEvent",
        back_populates="current_snapshot",
        foreign_keys="CompetitorChangeEvent.current_snapshot_id",
    )
    previous_change_events = relationship(
        "CompetitorChangeEvent",
        back_populates="previous_snapshot",
        foreign_keys="CompetitorChangeEvent.previous_snapshot_id",
    )


class CompetitorChangeEvent(BaseModel):
    """Detected pricing/feature change on competitor assets."""

    __tablename__ = "competitor_change_events"
    __table_args__ = (
        Index(
            "ix_competitor_change_events_company_detected",
            "company_id",
            "detected_at",
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[SourceType] = mapped_column(
        source_type_enum, nullable=False
    )
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    changed_fields: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, default=list
    )
    raw_diff: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    current_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "competitor_pricing_snapshots.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    previous_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "competitor_pricing_snapshots.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    processing_status: Mapped[ChangeProcessingStatus] = mapped_column(
        processing_status_enum.copy(),
        default=ChangeProcessingStatus.SUCCESS,
        nullable=False,
    )
    notification_status: Mapped[ChangeNotificationStatus] = mapped_column(
        notification_status_enum.copy(),
        default=ChangeNotificationStatus.PENDING,
        nullable=False,
    )

    company = relationship("Company", backref="change_events")
    current_snapshot = relationship(
        "CompetitorPricingSnapshot",
        foreign_keys=[current_snapshot_id],
        back_populates="change_events",
    )
    previous_snapshot = relationship(
        "CompetitorPricingSnapshot",
        foreign_keys=[previous_snapshot_id],
        back_populates="previous_change_events",
    )


class CompetitorMonitoringMatrix(BaseModel):
    """Consolidated monitoring matrix for competitor observation."""

    __tablename__ = "competitor_monitoring_matrices"
    __table_args__ = (
        Index(
            "ix_competitor_monitoring_matrix_company_updated",
            "company_id",
            "last_updated",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One matrix per company
    )

    # General monitoring configuration
    monitoring_config: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    # Social media sources discovered and monitored
    social_media_sources: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    # Structure: {
    #   "facebook": {"url": "...", "handle": "...", "last_checked": "..."},
    #   "instagram": {...},
    #   ...
    # }

    # Website structure snapshots
    website_sources: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    # Structure: {
    #   "snapshots": [...],
    #   "structure": {...},
    #   "key_pages": [...],
    #   "last_snapshot_at": "..."
    # }

    # News and press release sources
    news_sources: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    # Structure: {
    #   "press_release_urls": [...],
    #   "blog_urls": [...],
    #   "last_scraped_at": "..."
    # }

    # Marketing change tracking
    marketing_sources: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    # Structure: {
    #   "banners": [...],
    #   "landing_pages": [...],
    #   "products": [...],
    #   "job_postings": [...],
    #   "last_checked_at": "..."
    # }

    # SEO signals collected
    seo_signals: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    # Structure: {
    #   "meta_tags": {...},
    #   "structured_data": {...},
    #   "robots_txt": "...",
    #   "sitemap_url": "...",
    #   "canonical_urls": [...],
    #   "last_collected_at": "..."
    # }

    # Timestamp of last update
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=datetime.utcnow,
    )

    # Relationships
    company = relationship("Company", backref="monitoring_matrix")

    def __repr__(self) -> str:
        return (
            f"<CompetitorMonitoringMatrix(id={self.id}, company_id={self.company_id}, "
            f"last_updated={self.last_updated})>"
        )
