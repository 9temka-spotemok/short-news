"""
Pydantic schemas for analytics API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import (
    AnalyticsEntityType,
    AnalyticsPeriod,
    ImpactComponentType,
    RelationshipType,
)


class ImpactComponentResponse(BaseModel):
    """Response schema for impact score components."""

    id: UUID
    component_type: ImpactComponentType
    weight: float
    score_contribution: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class CompanyAnalyticsSnapshotResponse(BaseModel):
    """Aggregated analytics snapshot response."""

    id: UUID
    company_id: UUID
    period: AnalyticsPeriod
    period_start: datetime
    period_end: datetime

    news_total: int
    news_positive: int
    news_negative: int
    news_neutral: int
    news_average_sentiment: float
    news_average_priority: float

    pricing_changes: int
    feature_updates: int
    funding_events: int

    impact_score: float
    innovation_velocity: float
    trend_delta: float

    metric_breakdown: Dict[str, Any] = Field(default_factory=dict)
    components: List[ImpactComponentResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SnapshotSeriesResponse(BaseModel):
    """Collection of snapshots for charting."""

    company_id: UUID
    period: AnalyticsPeriod
    snapshots: List[CompanyAnalyticsSnapshotResponse]


class KnowledgeGraphEdgeResponse(BaseModel):
    """Response schema for knowledge graph edges."""

    id: UUID
    company_id: Optional[UUID]
    source_entity_type: AnalyticsEntityType
    source_entity_id: UUID
    target_entity_type: AnalyticsEntityType
    target_entity_id: UUID
    relationship_type: RelationshipType
    confidence: float
    weight: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ReportPresetResponse(BaseModel):
    """Response schema for saved report presets."""

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    companies: List[UUID] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    visualization_config: Dict[str, Any] = Field(default_factory=dict)
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportPresetCreateRequest(BaseModel):
    """Create or update preset payload."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    companies: List[UUID] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    visualization_config: Dict[str, Any] = Field(default_factory=dict)
    is_favorite: bool = False


