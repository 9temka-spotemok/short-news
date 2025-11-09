"""
Analytics endpoints for API v2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import (
    AnalyticsGraphEdge,
    AnalyticsPeriod,
    RelationshipType,
    User,
    UserReportPreset,
)
from app.schemas.analytics import (
    AnalyticsExportRequest,
    AnalyticsExportResponse,
    CompanyAnalyticsSnapshotResponse,
    ComparisonRequest,
    ComparisonResponse,
    ImpactComponentResponse,
    KnowledgeGraphEdgeResponse,
    ReportPresetCreateRequest,
    ReportPresetResponse,
    SnapshotSeriesResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.analytics_comparison_service import AnalyticsComparisonService
from app.tasks.analytics import (
    recompute_company_analytics,
    sync_company_knowledge_graph,
)


router = APIRouter()


@router.get(
    "/companies/{company_id}/snapshots",
    response_model=SnapshotSeriesResponse,
    summary="Get analytics snapshots for a company",
)
async def get_company_snapshots(
    company_id: UUID,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),
    limit: int = Query(default=30, ge=1, le=180),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SnapshotSeriesResponse:
    service = AnalyticsService(db)
    snapshots = await service.get_snapshots(company_id, period, limit)
    snapshot_models = [_snapshot_to_response(snapshot) for snapshot in snapshots]
    return SnapshotSeriesResponse(
        company_id=company_id,
        period=period,
        snapshots=snapshot_models,
    )


@router.get(
    "/companies/{company_id}/impact/latest",
    response_model=CompanyAnalyticsSnapshotResponse,
    summary="Get latest analytics snapshot",
)
async def get_latest_snapshot(
    company_id: UUID,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAnalyticsSnapshotResponse:
    service = AnalyticsService(db)
    snapshot = await service.get_latest_snapshot(company_id, period)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )
    return _snapshot_to_response(snapshot)


@router.post(
    "/companies/{company_id}/recompute",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger analytics recomputation",
)
async def trigger_recompute(
    company_id: UUID,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),
    lookback: int = Query(default=30, ge=1, le=180),
    current_user: User = Depends(get_current_user),
) -> dict:
    logger.info("User %s triggered analytics recompute for company %s", current_user.id, company_id)
    task = recompute_company_analytics.delay(str(company_id), period.value, lookback)
    return {"status": "queued", "task_id": task.id}


@router.post(
    "/companies/{company_id}/graph/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger knowledge graph sync",
)
async def trigger_graph_sync(
    company_id: UUID,
    period_start: datetime = Query(..., description="Period start in ISO format"),
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),
    current_user: User = Depends(get_current_user),
) -> dict:
    period_start = _ensure_timezone(period_start)
    logger.info("User %s triggered graph sync for company %s", current_user.id, company_id)
    task = sync_company_knowledge_graph.delay(
        str(company_id),
        period_start.isoformat(),
        period.value,
    )
    return {"status": "queued", "task_id": task.id}


@router.get(
    "/graph",
    response_model=List[KnowledgeGraphEdgeResponse],
    summary="Get analytics knowledge graph edges",
)
async def get_graph_edges(
    company_id: UUID = Query(default=None),
    relationship: RelationshipType | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[KnowledgeGraphEdgeResponse]:
    stmt = select(AnalyticsGraphEdge).order_by(AnalyticsGraphEdge.created_at.desc()).limit(limit)

    if company_id:
        stmt = stmt.where(AnalyticsGraphEdge.company_id == company_id)
    if relationship:
        stmt = stmt.where(AnalyticsGraphEdge.relationship_type == relationship)

    result = await db.execute(stmt)
    edges = list(result.scalars().all())
    return [_edge_to_response(edge) for edge in edges]


@router.get(
    "/reports/presets",
    response_model=List[ReportPresetResponse],
    summary="List analytics report presets",
)
async def list_report_presets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ReportPresetResponse]:
    stmt = (
        select(UserReportPreset)
        .where(UserReportPreset.user_id == current_user.id)
        .order_by(UserReportPreset.created_at.desc())
    )
    result = await db.execute(stmt)
    presets = list(result.scalars().all())
    return [
        ReportPresetResponse.model_validate(preset, from_attributes=True)
        for preset in presets
    ]


@router.post(
    "/reports/presets",
    response_model=ReportPresetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create report preset",
)
async def create_report_preset(
    payload: ReportPresetCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportPresetResponse:
    preset = UserReportPreset(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        companies=payload.companies,
        filters=payload.filters,
        visualization_config=payload.visualization_config,
        is_favorite=payload.is_favorite,
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return ReportPresetResponse.model_validate(preset, from_attributes=True)


@router.post(
    "/comparisons",
    response_model=ComparisonResponse,
    summary="Build analytics comparison overview",
)
async def build_comparison_overview(
    payload: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComparisonResponse:
    service = AnalyticsComparisonService(db)
    return await service.build_comparison(payload, user=current_user)


@router.post(
    "/export",
    response_model=AnalyticsExportResponse,
    summary="Build analytics export payload",
)
async def build_export_payload(
    payload: AnalyticsExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsExportResponse:
    service = AnalyticsComparisonService(db)
    return await service.build_export_payload(payload, user=current_user)


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo:
        return value
    return value.replace(tzinfo=timezone.utc)


def _snapshot_to_response(snapshot) -> CompanyAnalyticsSnapshotResponse:
    return CompanyAnalyticsSnapshotResponse(
        id=snapshot.id,
        company_id=snapshot.company_id,
        period=snapshot.period,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        news_total=snapshot.news_total,
        news_positive=snapshot.news_positive,
        news_negative=snapshot.news_negative,
        news_neutral=snapshot.news_neutral,
        news_average_sentiment=snapshot.news_average_sentiment,
        news_average_priority=snapshot.news_average_priority,
        pricing_changes=snapshot.pricing_changes,
        feature_updates=snapshot.feature_updates,
        funding_events=snapshot.funding_events,
        impact_score=snapshot.impact_score,
        innovation_velocity=snapshot.innovation_velocity,
        trend_delta=snapshot.trend_delta,
        metric_breakdown=snapshot.metric_breakdown or {},
        components=[
            ImpactComponentResponse(
                id=component.id,
                component_type=component.component_type,
                weight=component.weight,
                score_contribution=component.score_contribution,
                metadata=component.metadata_json or {},
            )
            for component in (snapshot.components or [])
        ],
    )


def _edge_to_response(edge) -> KnowledgeGraphEdgeResponse:
    return KnowledgeGraphEdgeResponse(
        id=edge.id,
        company_id=edge.company_id,
        source_entity_type=edge.source_entity_type,
        source_entity_id=edge.source_entity_id,
        target_entity_type=edge.target_entity_type,
        target_entity_id=edge.target_entity_id,
        relationship_type=edge.relationship_type,
        confidence=edge.confidence,
        weight=edge.weight,
        metadata=edge.metadata_json or {},
    )


