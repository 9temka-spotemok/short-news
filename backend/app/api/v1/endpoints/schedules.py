"""
Endpoints for managing crawl schedules and source profiles.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import CrawlScope, User
from app.schemas.crawl_schedule import (
    CrawlScheduleResponse,
    CrawlScheduleUpdateRequest,
)
from app.services.crawl_schedule_service import CrawlScheduleService

router = APIRouter()


@router.get(
    "/crawl",
    response_model=List[CrawlScheduleResponse],
    summary="List crawl schedules",
    tags=["Schedules"],
)
async def list_crawl_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CrawlScheduleResponse]:
    """Return all active crawl schedules."""
    logger.info("User %s requested crawl schedule listing", current_user.id)
    service = CrawlScheduleService(db)
    schedules = await service.list_active_schedules()
    return [
        CrawlScheduleResponse(
            id=schedule.id,
            scope=schedule.scope,
            scope_value=schedule.scope_value,
            mode=schedule.mode,
            frequency_seconds=schedule.frequency_seconds,
            jitter_seconds=schedule.jitter_seconds,
            max_retries=schedule.max_retries,
            retry_backoff_seconds=schedule.retry_backoff_seconds,
            enabled=schedule.enabled,
            priority=schedule.priority,
            metadata=schedule.metadata_json or {},
            run_window_start=schedule.run_window_start,
            run_window_end=schedule.run_window_end,
            last_applied_at=schedule.last_applied_at,
        )
        for schedule in schedules
    ]


@router.put(
    "/crawl/{scope}/{scope_value}",
    response_model=CrawlScheduleResponse,
    summary="Upsert crawl schedule",
    tags=["Schedules"],
)
async def upsert_crawl_schedule(
    payload: CrawlScheduleUpdateRequest,
    scope: str = Path(..., description="Crawl scope (source_type, company, source)"),
    scope_value: str = Path(..., description="Scope value identifier"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CrawlScheduleResponse:
    """Create or update schedule for given scope."""
    try:
        scope_enum = CrawlScope(scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported scope: {scope}") from exc

    logger.info(
        "User %s upserting crawl schedule scope=%s value=%s", current_user.id, scope, scope_value
    )

    service = CrawlScheduleService(db)
    schedule = await service.upsert_schedule(
        scope=scope_enum,
        scope_value=scope_value,
        mode=payload.mode,
        frequency_seconds=payload.frequency_seconds,
        jitter_seconds=payload.jitter_seconds,
        max_retries=payload.max_retries,
        retry_backoff_seconds=payload.retry_backoff_seconds,
        enabled=payload.enabled,
        priority=payload.priority,
        metadata=payload.metadata,
    )

    if payload.run_window_start or payload.run_window_end:
        schedule.run_window_start = payload.run_window_start
        schedule.run_window_end = payload.run_window_end
        await db.commit()
        await db.refresh(schedule)

    await service.reapply_schedule(schedule)

    return CrawlScheduleResponse(
        id=schedule.id,
        scope=schedule.scope,
        scope_value=schedule.scope_value,
        mode=schedule.mode,
        frequency_seconds=schedule.frequency_seconds,
        jitter_seconds=schedule.jitter_seconds,
        max_retries=schedule.max_retries,
        retry_backoff_seconds=schedule.retry_backoff_seconds,
        enabled=schedule.enabled,
        priority=schedule.priority,
        metadata=schedule.metadata_json or {},
        run_window_start=schedule.run_window_start,
        run_window_end=schedule.run_window_end,
        last_applied_at=schedule.last_applied_at,
    )


@router.post(
    "/crawl/hydrate",
    summary="Ensure source profiles exist",
    tags=["Schedules"],
)
async def hydrate_source_profiles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Ensure that source profiles exist for all companies and supported source types."""
    logger.info("User %s triggered source profile hydration", current_user.id)
    service = CrawlScheduleService(db)
    count = await service.hydrate_profiles()
    return {"status": "success", "created": count}


