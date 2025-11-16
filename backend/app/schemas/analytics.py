"""
Pydantic schemas for analytics API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import (
    AnalyticsEntityType,
    AnalyticsPeriod,
    ImpactComponentType,
    RelationshipType,
)
from app.schemas.competitor_events import CompetitorChangeEventSchema


class ImpactComponentResponse(BaseModel):
    """Response schema for impact score components."""

    id: Optional[UUID] = None
    component_type: ImpactComponentType
    weight: float
    score_contribution: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class CompanyAnalyticsSnapshotResponse(BaseModel):
    """Aggregated analytics snapshot response."""

    id: Optional[UUID] = None
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


# ----------------------------------------------------------------------
# Comparison & export schemas
# ----------------------------------------------------------------------


class ComparisonFilters(BaseModel):
    """Public filters applied to comparison subjects."""

    topics: List[str] = Field(default_factory=list)
    sentiments: List[str] = Field(default_factory=list)
    source_types: List[str] = Field(default_factory=list)
    min_priority: Optional[float] = None


class ComparisonSubjectRequest(BaseModel):
    """Comparison subject definition from client."""

    subject_type: Literal["company", "preset"]
    reference_id: UUID
    label: Optional[str] = None
    color: Optional[str] = None


class ComparisonRequest(BaseModel):
    """Comparison query payload."""

    subjects: List[ComparisonSubjectRequest]
    period: AnalyticsPeriod = AnalyticsPeriod.DAILY
    lookback: int = Field(default=30, ge=1, le=365)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    filters: Optional[ComparisonFilters] = None
    include_series: bool = True
    include_components: bool = True
    include_change_log: bool = True
    include_knowledge_graph: bool = True
    change_log_limit: int = Field(default=5, ge=1, le=50)
    knowledge_graph_limit: int = Field(default=10, ge=1, le=200)
    top_news_limit: int = Field(default=5, ge=1, le=20)


class ExportIncludeOptions(BaseModel):
    """Export payload inclusion flags."""

    include_notifications: bool = True
    include_presets: bool = True


class AnalyticsExportRequest(ComparisonRequest):
    """Export payload request inherits comparison options."""

    export_format: Optional[str] = None
    include: ExportIncludeOptions = Field(default_factory=ExportIncludeOptions)


class ComparisonCompanySummary(BaseModel):
    """Lightweight company descriptor used in comparison results."""

    id: UUID
    name: str
    category: Optional[str] = None
    logo_url: Optional[str] = None


class AggregatedImpactComponent(BaseModel):
    """Aggregated impact component entry across companies."""

    component_type: str
    score_contribution: float
    weight: float


class CompanyAnalyticsSnapshotSummary(BaseModel):
    """Aggregated snapshot summary for subject."""

    period_start: datetime
    impact_score: float
    innovation_velocity: float
    trend_delta: Optional[float] = None
    news_total: int
    news_positive: int
    news_negative: int
    news_neutral: int
    pricing_changes: int
    feature_updates: int
    funding_events: int
    components: List[AggregatedImpactComponent] = Field(default_factory=list)


class ComparisonSubjectSummary(BaseModel):
    """Resolved comparison subject metadata."""

    subject_key: str
    subject_id: UUID
    subject_type: Literal["company", "preset"]
    label: str
    company_ids: List[UUID]
    preset_id: Optional[UUID] = None
    color: Optional[str] = None
    companies: List[ComparisonCompanySummary] = Field(default_factory=list)
    filters: ComparisonFilters = Field(default_factory=ComparisonFilters)


class ComparisonSeriesPoint(BaseModel):
    """Single data point for multi-subject series."""

    period_start: datetime
    impact_score: float
    innovation_velocity: float
    trend_delta: Optional[float] = None
    news_total: int
    news_positive: int
    news_negative: int
    news_neutral: int
    pricing_changes: int
    feature_updates: int
    funding_events: int


class ComparisonSeries(BaseModel):
    """Series response for subject."""

    subject_key: str
    subject_id: UUID
    snapshots: List[ComparisonSeriesPoint] = Field(default_factory=list)


class ComparisonMetricSummary(BaseModel):
    """Aggregated metric summary per subject."""

    subject_key: str
    subject_id: UUID
    news_volume: int
    activity_score: float
    avg_priority: float
    impact_score: float
    trend_delta: float
    innovation_velocity: float
    sentiment_distribution: Dict[str, int] = Field(default_factory=dict)
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    topic_distribution: Dict[str, int] = Field(default_factory=dict)
    daily_activity: Dict[str, int] = Field(default_factory=dict)
    top_news: List[Dict[str, Any]] = Field(default_factory=list)
    impact_components: List[AggregatedImpactComponent] = Field(default_factory=list)
    snapshot: Optional[CompanyAnalyticsSnapshotSummary] = None


class ComparisonResponse(BaseModel):
    """Full comparison response payload."""

    generated_at: datetime
    period: AnalyticsPeriod
    lookback: int
    date_from: datetime
    date_to: datetime

    subjects: List[ComparisonSubjectSummary]
    metrics: List[ComparisonMetricSummary]
    series: List[ComparisonSeries] = Field(default_factory=list)
    change_log: Dict[str, List[CompetitorChangeEventSchema]] = Field(default_factory=dict)
    knowledge_graph: Dict[str, List[KnowledgeGraphEdgeResponse]] = Field(default_factory=dict)


class AnalyticsChangeLogResponse(BaseModel):
    """Paginated change log response for analytics v2."""

    events: List[CompetitorChangeEventSchema] = Field(default_factory=list)
    next_cursor: Optional[str] = None
    total: int


class NotificationSettingsSummary(BaseModel):
    """Notification settings snapshot included in exports."""

    notification_frequency: str
    digest_enabled: bool
    digest_frequency: str
    digest_format: str
    digest_custom_schedule: Dict[str, Any] = Field(default_factory=dict)
    subscribed_companies: List[UUID] = Field(default_factory=list)
    interested_categories: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    telegram_enabled: bool
    telegram_chat_id: Optional[str] = None
    telegram_digest_mode: str
    timezone: Optional[str] = None
    week_start_day: Optional[int] = None


class AnalyticsExportResponse(BaseModel):
    """Backend export payload for analytics comparison."""

    version: str
    generated_at: datetime
    export_format: Optional[str] = None
    timeframe: Dict[str, Any]
    comparison: ComparisonResponse
    notification_settings: Optional[NotificationSettingsSummary] = None
    presets: List[ReportPresetResponse] = Field(default_factory=list)


