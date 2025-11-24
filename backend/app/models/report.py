"""
Report models for company analysis reports
"""

from typing import Optional, Dict, Any
from datetime import datetime
import enum
from uuid import UUID
from sqlalchemy import String, Text, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import BaseModel


class ReportStatus(str, enum.Enum):
    """Report generation status"""
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class Report(BaseModel):
    """Report model for company analysis reports"""
    __tablename__ = "reports"
    
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who requested the report"
    )
    query: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Company name or URL query"
    )
    status: Mapped[ReportStatus] = mapped_column(
        ENUM(ReportStatus, name="reportstatus", create_type=False, values_callable=lambda enum_cls: [member.value for member in enum_cls]),
        nullable=False,
        server_default="'processing'",
        index=True,
        comment="Report generation status"
    )
    company_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated company (if found/created)"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if status is error"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When report generation completed"
    )
    report_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Report data (company, news, categories, sources, pricing, competitors)"
    )
    
    # Relationships
    user = relationship("User", backref="reports")
    company = relationship("Company", backref="reports")
    
    # Indexes are defined in migration
    __table_args__ = (
        Index("idx_report_user_status", "user_id", "status"),
        Index("idx_report_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Report(id={self.id}, user_id={self.user_id}, status={self.status.value}, query={self.query[:50]})>"

