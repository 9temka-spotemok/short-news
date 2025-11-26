"""
Models for adaptive crawl scheduling and source profiles.
"""

from __future__ import annotations

from datetime import datetime, timezone
import enum
from typing import Optional, Dict, Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from .base import BaseModel
from .news import SourceType, source_type_enum
from .company import Company


class CrawlScope(str, enum.Enum):
    """Scope level for crawl schedule application."""

    SOURCE_TYPE = "source_type"
    COMPANY = "company"
    SOURCE = "source"


class CrawlMode(str, enum.Enum):
    """Mode of crawling behaviour."""

    ALWAYS_UPDATE = "always_update"
    CHANGE_DETECTION = "change_detection"


class CrawlStatus(str, enum.Enum):
    """Status of a crawl run."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# Define PostgreSQL ENUMs with values_callable to ensure values are used, not names
def enum_values(enum_cls):
    """Helper to extract enum values for SQLAlchemy Enum definition."""
    return [member.value for member in enum_cls]


crawl_scope_enum = Enum(
    CrawlScope,
    name="crawlscope",
    values_callable=enum_values,
    native_enum=True,
    create_type=False,
)

crawl_mode_enum = Enum(
    CrawlMode,
    name="crawlmode",
    values_callable=enum_values,
    native_enum=True,
    create_type=False,
)

crawl_status_enum = Enum(
    CrawlStatus,
    name="crawlstatus",
    values_callable=enum_values,
    native_enum=True,
    create_type=False,
)


class CrawlSchedule(BaseModel):
    """
    Adaptive crawl schedule configuration.

    Allows defining frequency and retry policies per scope (source type, company, or specific source).
    """

    __tablename__ = "crawl_schedules"

    scope = Column(crawl_scope_enum, nullable=False, index=True)
    scope_value = Column(String(255), nullable=False, index=True)
    mode = Column(crawl_mode_enum, nullable=False, default=CrawlMode.ALWAYS_UPDATE)
    frequency_seconds = Column(Integer, nullable=False, default=15 * 60)
    jitter_seconds = Column(Integer, nullable=False, default=5 * 60)
    max_retries = Column(Integer, nullable=False, default=3)
    retry_backoff_seconds = Column(Integer, nullable=False, default=60)
    enabled = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)
    run_window_start = Column(DateTime(timezone=True))
    run_window_end = Column(DateTime(timezone=True))
    metadata_json = Column("metadata", JSON, default=dict)
    last_applied_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("scope", "scope_value", name="uq_crawl_schedule_scope"),
    )


class SourceProfile(BaseModel):
    """
    Source profile captures crawl behaviour for a specific competitor/source pair.

    Keeps track of change detection hashes and run counters to drive adaptive strategies.
    """

    __tablename__ = "source_profiles"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(source_type_enum, nullable=False, index=True)
    mode = Column(crawl_mode_enum, nullable=False, default=CrawlMode.ALWAYS_UPDATE)
    last_content_hash = Column(String(255))
    last_run_at = Column(DateTime(timezone=True))
    last_success_at = Column(DateTime(timezone=True))
    last_error_at = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, nullable=False, default=0)
    consecutive_no_change = Column(Integer, nullable=False, default=0)
    metadata_json = Column("metadata", JSON, default=dict)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("crawl_schedules.id"))

    company = relationship(Company, backref="source_profiles")
    schedule = relationship("CrawlSchedule", backref="source_profiles")
    runs = relationship("CrawlRun", back_populates="profile", order_by="CrawlRun.started_at.desc()")

    __table_args__ = (
        UniqueConstraint("company_id", "source_type", name="uq_source_profile_company_source"),
    )


def utcnow() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class CrawlRun(BaseModel):
    """History of crawl executions for monitoring, retries and analytics."""

    __tablename__ = "crawl_runs"

    profile_id = Column(UUID(as_uuid=True), ForeignKey("source_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("crawl_schedules.id", ondelete="SET NULL"))
    status = Column(crawl_status_enum, nullable=False, default=CrawlStatus.SCHEDULED, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at = Column(DateTime(timezone=True))
    item_count = Column(Integer, nullable=False, default=0)
    change_detected = Column(Boolean, nullable=False, default=False)
    error_message = Column(String(1000))
    metadata_json = Column("metadata", JSON, default=dict)

    profile = relationship("SourceProfile", back_populates="runs")
    schedule = relationship("CrawlSchedule", backref="runs")


class CrawlScheduleSchemaMixin:
    """Helper mixin for serialising crawl schedules in API responses."""

    def to_schedule_dict(self) -> Dict[str, Any]:
        """Return schedule details as dictionary."""
        return {
            "id": str(self.id),
            "scope": self.scope.value if isinstance(self.scope, CrawlScope) else self.scope,
            "scope_value": self.scope_value,
            "mode": self.mode.value if isinstance(self.mode, CrawlMode) else self.mode,
            "frequency_seconds": self.frequency_seconds,
            "jitter_seconds": self.jitter_seconds,
            "max_retries": self.max_retries,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "enabled": self.enabled,
            "priority": self.priority,
            "run_window_start": self.run_window_start.isoformat() if self.run_window_start else None,
            "run_window_end": self.run_window_end.isoformat() if self.run_window_end else None,
            "metadata": self.metadata_json or {},
            "last_applied_at": self.last_applied_at.isoformat() if self.last_applied_at else None,
        }


class SourceProfileSchemaMixin:
    """Helper mixin for serialising source profiles in API responses."""

    def to_profile_dict(self) -> Dict[str, Any]:
        """Return profile details as dictionary."""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "source_type": self.source_type.value if isinstance(self.source_type, SourceType) else self.source_type,
            "mode": self.mode.value if isinstance(self.mode, CrawlMode) else self.mode,
            "last_content_hash": self.last_content_hash,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_no_change": self.consecutive_no_change,
            "metadata": self.metadata_json or {},
            "schedule_id": str(self.schedule_id) if self.schedule_id else None,
        }


