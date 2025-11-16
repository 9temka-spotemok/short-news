"""
Analytics endpoints for API v2.
"""

from __future__ import annotations

import asyncio
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kombu.exceptions import OperationalError as KombuOperationalError
from redis import exceptions as redis_exceptions

from app.api.dependencies import get_current_user, get_analytics_facade
from app.core.database import get_db
from app.models import (
    AnalyticsGraphEdge,
    AnalyticsPeriod,
    CompanyAnalyticsSnapshot,
    NewsTopic,
    RelationshipType,
    SentimentLabel,
    SourceType,
    User,
    UserReportPreset,
)
from app.schemas.analytics import (
    AnalyticsChangeLogResponse,
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
from app.tasks.analytics import (
    recompute_company_analytics,
    sync_company_knowledge_graph,
)
from app.domains.analytics import AnalyticsFacade


router = APIRouter()


def _encode_change_log_cursor(detected_at: datetime, event_id: UUID) -> str:
    normalized = detected_at
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=timezone.utc)
    else:
        normalized = normalized.astimezone(timezone.utc)
    payload = {
        "detected_at": normalized.isoformat(),
        "event_id": str(event_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _decode_change_log_cursor(cursor: str) -> Tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        payload = json.loads(raw)
        detected_at = datetime.fromisoformat(payload["detected_at"])
        if detected_at.tzinfo is None:
            detected_at = detected_at.replace(tzinfo=timezone.utc)
        detected_at = detected_at.astimezone(timezone.utc).replace(tzinfo=None)
        event_id = UUID(payload["event_id"])
        return detected_at, event_id
    except Exception as exc:  # pragma: no cover - defensive: malformed cursors
        raise ValueError("Invalid pagination cursor") from exc


@router.get(
    "/companies/{company_id}/impact/latest",
    response_model=CompanyAnalyticsSnapshotResponse,
    summary="Get latest analytics snapshot",
    name="get_latest_analytics_snapshot",  # Явное имя для отладки
)
async def get_latest_snapshot(
    company_id: UUID,
    period: str = Query(default="daily", description="Analytics period: daily, weekly, or monthly"),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsFacade = Depends(get_analytics_facade),
) -> CompanyAnalyticsSnapshotResponse:
    logger.info(
        "get_latest_snapshot called: company_id=%s, period=%s, user_id=%s",
        company_id,
        period,
        current_user.id,
    )
    # Нормализуем period к enum
    try:
        period_enum = AnalyticsPeriod(period.lower())
    except ValueError:
        logger.warning("Invalid period value: %s", period)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period value: {period}. Must be one of: daily, weekly, monthly",
        )
    
    logger.info("Calling analytics.get_latest_snapshot(company_id=%s, period=%s)", company_id, period_enum.value)
    snapshot = await analytics.get_latest_snapshot(company_id, period_enum)
    logger.info("get_latest_snapshot result: snapshot=%s (id=%s)", "found" if snapshot else "NOT FOUND", snapshot.id if snapshot else None)
    if not snapshot:
        logger.info("Snapshot not found, attempting to create automatically...")
        # Автоматически создаем snapshot для последнего периода, если его нет
        from datetime import datetime, timedelta, timezone
        
        # Получаем duration для периода
        period_duration_map = {
            AnalyticsPeriod.DAILY: timedelta(days=1),
            AnalyticsPeriod.WEEKLY: timedelta(days=7),
            AnalyticsPeriod.MONTHLY: timedelta(days=30),
        }
        period_duration = period_duration_map.get(period_enum, timedelta(days=1))
        
        # Вычисляем начало последнего периода (используем ту же логику, что и в refresh_company_snapshots)
        now = datetime.now(tz=timezone.utc)
        anchor = now.replace(minute=0, second=0, microsecond=0)
        # Для последнего периода используем offset=1 (вчера для daily)
        # Для daily: начало вчерашнего дня (00:00:00 UTC)
        if period_enum == AnalyticsPeriod.DAILY:
            period_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            period_start = anchor - period_duration
        
        logger.info("Computing snapshot for period_start=%s, period=%s", period_start.isoformat(), period_enum.value)
        try:
            # Создаем snapshot для последнего периода
            snapshot = await analytics.snapshots.compute_snapshot_for_period(
                company_id=company_id,
                period_start=period_start,
                period=period_enum,
            )
            logger.info("Successfully computed snapshot: id=%s", snapshot.id if snapshot else None)
            logger.info(
                "Auto-created snapshot for company %s (period=%s, start=%s, id=%s)",
                company_id,
                period_enum.value,
                period_start.isoformat(),
                snapshot.id if snapshot else None,
            )
        except Exception as exc:
            logger.error(
                "Failed to auto-create snapshot for company %s: %s",
                company_id,
                exc,
                exc_info=True,
            )
            # Откатываем транзакцию после ошибки в compute_snapshot_for_period
            try:
                await analytics.session.rollback()
                logger.info("Rolled back transaction after compute_snapshot_for_period error")
            except Exception as rollback_exc:
                logger.warning("Failed to rollback transaction: %s", rollback_exc)
            
            # Если не удалось создать, создаем пустой snapshot и сохраняем в БД
            logger.info("compute_snapshot_for_period failed, creating empty snapshot as fallback...")
            try:
                # Проверяем, нет ли уже snapshot с такими параметрами
                period_value = period_enum.value
                existing_snapshot_stmt = select(CompanyAnalyticsSnapshot).where(
                    CompanyAnalyticsSnapshot.company_id == company_id,
                    CompanyAnalyticsSnapshot.period == period_value,
                    CompanyAnalyticsSnapshot.period_start == period_start,
                ).limit(1)
                existing_result = await analytics.session.execute(existing_snapshot_stmt)
                existing_snapshot = existing_result.scalar_one_or_none()
                
                if existing_snapshot:
                    logger.info("Found existing snapshot with same parameters, using it: id=%s", existing_snapshot.id)
                    await analytics.session.refresh(existing_snapshot, ["components"])
                    snapshot = existing_snapshot
                else:
                    logger.info("Creating empty CompanyAnalyticsSnapshot object...")
                    snapshot = CompanyAnalyticsSnapshot(
                        company_id=company_id,
                        period=period_value,
                        period_start=period_start,
                        period_end=period_start + period_duration,
                        news_total=0,
                        news_positive=0,
                        news_negative=0,
                        news_neutral=0,
                        news_average_sentiment=0.0,
                        news_average_priority=0.0,
                        pricing_changes=0,
                        feature_updates=0,
                        funding_events=0,
                        impact_score=0.0,
                        innovation_velocity=0.0,
                        trend_delta=0.0,
                        metric_breakdown={},
                    )
                    logger.info("Adding snapshot to session and committing...")
                    analytics.session.add(snapshot)
                    await analytics.session.commit()
                    logger.info("Snapshot committed, refreshing...")
                    await analytics.session.refresh(snapshot, ["components"])
                    logger.info("Snapshot refreshed: id=%s", snapshot.id if snapshot else None)
                    logger.info(
                        "Created empty snapshot for company %s (period=%s, start=%s, id=%s)",
                        company_id,
                        period_value,
                        period_start.isoformat(),
                        snapshot.id if snapshot else None,
                    )
            except Exception as db_exc:
                logger.error(
                    "Failed to create empty snapshot for company %s: %s",
                    company_id,
                    db_exc,
                    exc_info=True,
                )
                # Откатываем транзакцию перед возвратом ошибки
                try:
                    await analytics.session.rollback()
                except Exception:
                    pass
                # Если даже пустой snapshot не удалось создать, возвращаем 404
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Snapshot not found and could not be created automatically",
                ) from db_exc
    
    logger.info("Converting snapshot to response...")
    response = _snapshot_to_response(snapshot)
    logger.info("=== get_latest_snapshot SUCCESS: snapshot_id=%s ===", response.id)
    return response


@router.get(
    "/companies/{company_id}/snapshots",
    response_model=SnapshotSeriesResponse,
    summary="Get analytics snapshots for a company",
)
async def get_company_snapshots(
    company_id: UUID,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),
    limit: int = Query(default=30, ge=1, le=180),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsFacade = Depends(get_analytics_facade),
) -> SnapshotSeriesResponse:
    snapshots = await analytics.get_snapshots(company_id, period, limit)
    snapshot_models = [_snapshot_to_response(snapshot) for snapshot in snapshots]
    return SnapshotSeriesResponse(
        company_id=company_id,
        period=period,
        snapshots=snapshot_models,
    )


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
    
    # Check Redis connection first to fail fast
    try:
        from app.core.config import settings
        import redis
        redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL or "redis://localhost:6379/0", socket_connect_timeout=2, socket_timeout=2)
        redis_client.ping()
        logger.debug("Redis connection check passed for company %s", company_id)
    except Exception as redis_check_exc:
        logger.error(
            "Redis connection check failed for company %s: %s",
            company_id,
            redis_check_exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics queue is unavailable. Please ensure Redis is running and accessible.",
        ) from redis_check_exc
    
    try:
        logger.debug("Attempting to enqueue analytics recompute task for company %s", company_id)
        
        # Run apply_async in executor with timeout to prevent hanging
        # apply_async is a blocking call that may hang if broker is slow
        def enqueue_task():
            """Enqueue task synchronously in a thread."""
            return recompute_company_analytics.apply_async(
                args=[str(company_id), period.value, lookback],
                countdown=0,
                expires=None,
                connection_retry=False,  # Disable retry to fail fast
                connection_retry_on_startup=False,
            )
        
        # Use asyncio.wait_for to set timeout for apply_async
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="celery-enqueue")
        
        try:
            task = await asyncio.wait_for(
                loop.run_in_executor(executor, enqueue_task),
                timeout=10.0  # 10 seconds timeout for enqueueing
            )
        except asyncio.TimeoutError:
            logger.error(
                "Timeout while enqueueing analytics recompute for company %s (exceeded 10 seconds)",
                company_id,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timeout. The analytics queue may be unavailable or slow. Please check Celery worker status.",
            )
        finally:
            executor.shutdown(wait=False)
        
        # Verify task was created
        if not task or not task.id:
            logger.error("Task was created but has no ID for company %s", company_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create task. Please try again later.",
            )
        
        logger.info("Successfully enqueued analytics recompute task %s for company %s", task.id, company_id)
        return {"status": "queued", "task_id": task.id}
        
    except HTTPException:
        # Re-raise HTTP exceptions (timeout, etc.)
        raise
    except (KombuOperationalError, redis_exceptions.RedisError, redis_exceptions.ConnectionError) as exc:
        logger.error(
            "Failed to enqueue analytics recompute for company %s: %s",
            company_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics queue is unavailable. Please ensure Celery worker and Redis are running.",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error while enqueueing analytics recompute for company %s: %s",
            company_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue analytics recompute. Please try again later.",
        ) from exc


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
    
    # Check Redis connection first to fail fast
    try:
        from app.core.config import settings
        import redis
        redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL or "redis://localhost:6379/0", socket_connect_timeout=2, socket_timeout=2)
        redis_client.ping()
        logger.debug("Redis connection check passed for company %s", company_id)
    except Exception as redis_check_exc:
        logger.error(
            "Redis connection check failed for company %s: %s",
            company_id,
            redis_check_exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph sync queue is unavailable. Please ensure Redis is running and accessible.",
        ) from redis_check_exc
    
    try:
        logger.debug("Attempting to enqueue graph sync task for company %s", company_id)
        
        # Run apply_async in executor with timeout to prevent hanging
        # apply_async is a blocking call that may hang if broker is slow
        def enqueue_task():
            """Enqueue task synchronously in a thread."""
            return sync_company_knowledge_graph.apply_async(
                args=[str(company_id), period_start.isoformat(), period.value],
                countdown=0,
                expires=None,
                connection_retry=False,  # Disable retry to fail fast
                connection_retry_on_startup=False,
            )
        
        # Use asyncio.wait_for to set timeout for apply_async
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="celery-enqueue")
        
        try:
            task = await asyncio.wait_for(
                loop.run_in_executor(executor, enqueue_task),
                timeout=10.0  # 10 seconds timeout for enqueueing
            )
        except asyncio.TimeoutError:
            logger.error(
                "Timeout while enqueueing graph sync for company %s (exceeded 10 seconds)",
                company_id,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timeout. The analytics queue may be unavailable or slow. Please check Celery worker status.",
            )
        finally:
            executor.shutdown(wait=False)
        
        # Verify task was created
        if not task or not task.id:
            logger.error("Task was created but has no ID for company %s", company_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create task. Please try again later.",
            )
        
        logger.info("Successfully enqueued graph sync task %s for company %s", task.id, company_id)
        return {"status": "queued", "task_id": task.id}
        
    except HTTPException:
        # Re-raise HTTP exceptions (timeout, etc.)
        raise
    except (KombuOperationalError, redis_exceptions.RedisError, redis_exceptions.ConnectionError) as exc:
        logger.error(
            "Failed to enqueue graph sync for company %s: %s",
            company_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph sync queue is unavailable. Please ensure Celery worker and Redis are running.",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error while enqueueing graph sync for company %s: %s",
            company_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue graph sync. Please try again later.",
        ) from exc


@router.get(
    "/change-log",
    response_model=AnalyticsChangeLogResponse,
    summary="Get analytics change log events",
)
async def get_change_log(
    company_id: UUID = Query(..., description="Company identifier"),
    period: AnalyticsPeriod = Query(
        default=AnalyticsPeriod.DAILY,
        description="Analysis period (reserved for future filtering)",
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Opaque pagination cursor from previous page",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    source_types: Optional[Sequence[SourceType]] = Query(default=None),
    topics: Optional[Sequence[NewsTopic]] = Query(default=None),
    sentiments: Optional[Sequence[SentimentLabel]] = Query(default=None),
    min_priority: Optional[float] = Query(default=None),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsFacade = Depends(get_analytics_facade),
) -> AnalyticsChangeLogResponse:
    del period  # Reserved for future use

    if topics or sentiments or min_priority is not None:
        logger.debug(
            "Change log filter parameters (topics/sentiments/min_priority) "
            "are currently not implemented for backend filtering",
        )

    cursor_detected_at: Optional[datetime] = None
    cursor_event_id: Optional[UUID] = None
    if cursor:
        try:
            cursor_detected_at, cursor_event_id = _decode_change_log_cursor(cursor)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    events, has_more, total = await analytics.get_change_log(
        company_id=company_id,
        limit=limit,
        cursor_detected_at=cursor_detected_at,
        cursor_event_id=cursor_event_id,
        source_types=source_types,
    )

    next_cursor: Optional[str] = None
    if has_more and events:
        last_event = events[-1]
        next_cursor = _encode_change_log_cursor(last_event.detected_at, last_event.id)

    return AnalyticsChangeLogResponse(
        events=events,
        next_cursor=next_cursor,
        total=total,
    )


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
    logger.info(
        "Fetching report presets for user %s (email: %s)",
        current_user.id,
        current_user.email,
    )
    stmt = (
        select(UserReportPreset)
        .where(UserReportPreset.user_id == current_user.id)
        .order_by(UserReportPreset.created_at.desc())
    )
    result = await db.execute(stmt)
    presets = list(result.scalars().all())
    logger.info(
        "Found %d report presets for user %s (email: %s)",
        len(presets),
        current_user.id,
        current_user.email,
    )
    if len(presets) == 0:
        # Check if there are any presets in the database at all
        total_stmt = select(UserReportPreset)
        total_result = await db.execute(total_stmt)
        total_presets = list(total_result.scalars().all())
        logger.debug(
            "Total presets in database: %d (for all users)",
            len(total_presets),
        )
    response = [
        ReportPresetResponse.model_validate(preset, from_attributes=True)
        for preset in presets
    ]
    return response


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
    logger.debug(
        "Creating report preset for user %s: name=%s",
        current_user.id,
        payload.name,
    )
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
    logger.info(
        "Created report preset for user %s: id=%s, name=%s",
        current_user.id,
        preset.id,
        preset.name,
    )
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
    analytics: AnalyticsFacade = Depends(get_analytics_facade),
) -> ComparisonResponse:
    return await analytics.build_comparison(payload, user=current_user)


@router.post(
    "/export",
    response_model=AnalyticsExportResponse,
    summary="Build analytics export payload",
)
async def build_export_payload(
    payload: AnalyticsExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsFacade = Depends(get_analytics_facade),
) -> AnalyticsExportResponse:
    return await analytics.build_export_payload(payload, user=current_user)


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo:
        return value
    return value.replace(tzinfo=timezone.utc)


def _snapshot_to_response(snapshot) -> CompanyAnalyticsSnapshotResponse:
    # Обрабатываем случай, когда snapshot не сохранен в БД (нет ID)
    snapshot_id = getattr(snapshot, 'id', None)
    components_list = getattr(snapshot, 'components', None) or []
    
    return CompanyAnalyticsSnapshotResponse(
        id=snapshot_id,
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
        metric_breakdown=getattr(snapshot, 'metric_breakdown', None) or {},
        components=[
            ImpactComponentResponse(
                id=getattr(component, 'id', None),
                component_type=component.component_type,
                weight=component.weight,
                score_contribution=component.score_contribution,
                metadata=getattr(component, 'metadata_json', None) or {},
            )
            for component in components_list
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


