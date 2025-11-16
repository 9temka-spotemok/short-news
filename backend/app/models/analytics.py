"""
Analytics and knowledge graph models for iteration 4.
"""

from __future__ import annotations

from datetime import datetime
import enum
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSON, ARRAY
from sqlalchemy.orm import relationship

from .base import BaseModel


class AnalyticsPeriod(str, enum.Enum):
    """Supported aggregation periods for analytics snapshots."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ImpactComponentType(str, enum.Enum):
    """Type of component contributing to impact score."""

    NEWS_SIGNAL = "news_signal"
    PRICING_CHANGE = "pricing_change"
    FEATURE_RELEASE = "feature_release"
    FUNDING_EVENT = "funding_event"
    COMMUNITY_EVENT = "community_event"
    OTHER = "other"


class AnalyticsEntityType(str, enum.Enum):
    """Entities supported by the analytics knowledge graph."""

    COMPANY = "company"
    NEWS_ITEM = "news_item"
    CHANGE_EVENT = "change_event"
    PRICING_SNAPSHOT = "pricing_snapshot"
    PRODUCT = "product"
    FEATURE = "feature"
    TEAM = "team"
    METRIC = "metric"
    EXTERNAL = "external"


class RelationshipType(str, enum.Enum):
    """Relationship semantics between graph entities."""

    CAUSES = "causes"
    CORRELATED_WITH = "correlated_with"
    FOLLOWS = "follows"
    AMPLIFIES = "amplifies"
    DEPENDS_ON = "depends_on"


analytics_period_enum = Enum(
    AnalyticsPeriod,
    name="analyticsperiod",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
    native_enum=True,
    create_type=False,
)

impact_component_type_enum = Enum(
    ImpactComponentType,
    name="impactcomponenttype",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
    native_enum=True,
    create_type=False,
)

analytics_entity_type_enum = Enum(
    AnalyticsEntityType,
    name="analyticsentitytype",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
    native_enum=True,
    create_type=False,
)

relationship_type_enum = Enum(
    RelationshipType,
    name="relationshiptype",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
    native_enum=True,
    create_type=False,
)


class CompanyAnalyticsSnapshot(BaseModel):
    """Aggregated metrics for a company within a period."""

    __tablename__ = "company_analytics_snapshots"

    company_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period = Column(analytics_period_enum.copy(), nullable=False, default=AnalyticsPeriod.DAILY)

    news_total = Column(Integer, nullable=False, default=0)
    news_positive = Column(Integer, nullable=False, default=0)
    news_negative = Column(Integer, nullable=False, default=0)
    news_neutral = Column(Integer, nullable=False, default=0)
    news_average_sentiment = Column(Float, nullable=False, default=0.0)
    news_average_priority = Column(Float, nullable=False, default=0.0)

    pricing_changes = Column(Integer, nullable=False, default=0)
    feature_updates = Column(Integer, nullable=False, default=0)
    funding_events = Column(Integer, nullable=False, default=0)

    impact_score = Column(Float, nullable=False, default=0.0)
    innovation_velocity = Column(Float, nullable=False, default=0.0)
    trend_delta = Column(Float, nullable=False, default=0.0)

    metric_breakdown = Column(JSON, default=dict)

    company = relationship("Company", backref="analytics_snapshots", lazy="selectin")
    components = relationship(
        "ImpactComponent",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "period_start",
            "period",
            name="uq_company_snapshot_period",
        ),
        Index(
            "ix_company_snapshot_company_period",
            "company_id",
            "period",
            "period_start",
        ),
    )


class ImpactComponent(BaseModel):
    """Breakdown of impact score components."""

    __tablename__ = "impact_components"

    snapshot_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("company_analytics_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_type = Column(impact_component_type_enum.copy(), nullable=False)
    weight = Column(Float, nullable=False, default=0.0)
    score_contribution = Column(Float, nullable=False, default=0.0)

    source_entity_type = Column(analytics_entity_type_enum.copy(), nullable=True)
    source_entity_id = Column(PGUUID(as_uuid=True), nullable=True)
    metadata_json = Column("metadata", JSON, default=dict)

    snapshot = relationship(
        "CompanyAnalyticsSnapshot",
        back_populates="components",
        lazy="selectin",
    )
    company = relationship("Company", backref="impact_components", lazy="selectin")


class AnalyticsGraphEdge(BaseModel):
    """Directed knowledge graph edge connecting analytics entities."""

    __tablename__ = "analytics_graph_edges"

    company_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_entity_type = Column(analytics_entity_type_enum.copy(), nullable=False)
    source_entity_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    target_entity_type = Column(analytics_entity_type_enum.copy(), nullable=False)
    target_entity_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    relationship_type = Column(relationship_type_enum.copy(), nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    weight = Column(Float, nullable=False, default=1.0)
    metadata_json = Column("metadata", JSON, default=dict)

    company = relationship("Company", backref="analytics_graph_edges")

    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_analytics_graph_edge",
        ),
    )


class UserReportPreset(BaseModel):
    """Saved analytics report presets for users."""

    __tablename__ = "user_report_presets"

    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    companies = Column(ARRAY(PGUUID()), default=list)
    filters = Column(JSON, default=dict)
    visualization_config = Column(JSON, default=dict)
    is_favorite = Column(Boolean, nullable=False, default=False)

    user = relationship("User", backref="analytics_report_presets")


