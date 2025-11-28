"""
Adaptive crawl scheduling service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CrawlMode,
    CrawlRun,
    CrawlSchedule,
    CrawlScope,
    CrawlStatus,
    SourceProfile,
    SourceType,
    Company,
)


class CrawlScheduleService:
    """Service responsible for managing dynamic crawl schedules."""

    DEFAULT_SOURCE_FREQUENCIES: Dict[SourceType, int] = {
        SourceType.BLOG: 15 * 60,
        SourceType.NEWS_SITE: 10 * 60,
        SourceType.TWITTER: 5 * 60,
        SourceType.GITHUB: 30 * 60,
        SourceType.REDDIT: 20 * 60,
        SourceType.PRESS_RELEASE: 60 * 60,
        # Social media sources - check more frequently due to high activity
        SourceType.FACEBOOK: 10 * 60,
        SourceType.INSTAGRAM: 10 * 60,
        SourceType.LINKEDIN: 15 * 60,
        SourceType.YOUTUBE: 20 * 60,
        SourceType.TIKTOK: 10 * 60,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def default_frequency_for_source(cls, source_type: SourceType) -> int:
        """Return default frequency for a given source type."""
        return cls.DEFAULT_SOURCE_FREQUENCIES.get(source_type, 30 * 60)

    async def get_schedule(self, scope: CrawlScope, scope_value: str) -> Optional[CrawlSchedule]:
        """Fetch schedule for given scope."""
        result = await self.db.execute(
            select(CrawlSchedule).where(
                and_(CrawlSchedule.scope == scope, CrawlSchedule.scope_value == scope_value)
            )

        )
        return result.scalar_one_or_none()

    async def list_active_schedules(self) -> List[CrawlSchedule]:
        """Return all enabled schedules ordered by priority."""
        result = await self.db.execute(
            select(CrawlSchedule).where(CrawlSchedule.enabled == True).order_by(CrawlSchedule.priority.desc())
        )
        return list(result.scalars().all())

    async def upsert_schedule(
        self,
        *,
        scope: CrawlScope,
        scope_value: str,
        mode: CrawlMode,
        frequency_seconds: int,
        jitter_seconds: int = 300,
        max_retries: int = 3,
        retry_backoff_seconds: int = 60,
        enabled: bool = True,
        priority: int = 0,
        metadata: Optional[dict] = None,
    ) -> CrawlSchedule:
        """Create or update a schedule."""
        stmt = insert(CrawlSchedule).values(
            scope=scope,
            scope_value=scope_value,
            mode=mode,
            frequency_seconds=frequency_seconds,
            jitter_seconds=jitter_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            enabled=enabled,
            priority=priority,
            metadata=metadata or {},
            last_applied_at=datetime.now(timezone.utc),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["scope", "scope_value"],
            set_={
                "mode": stmt.excluded.mode,
                "frequency_seconds": stmt.excluded.frequency_seconds,
                "jitter_seconds": stmt.excluded.jitter_seconds,
                "max_retries": stmt.excluded.max_retries,
                "retry_backoff_seconds": stmt.excluded.retry_backoff_seconds,
                "enabled": stmt.excluded.enabled,
                "priority": stmt.excluded.priority,
                "metadata": stmt.excluded.metadata,
                "last_applied_at": stmt.excluded.last_applied_at,
            },
        )
        await self.db.execute(stmt)
        await self.db.commit()

        schedule = await self.get_schedule(scope, scope_value)
        assert schedule, "Failed to upsert crawl schedule"
        return schedule

    async def ensure_source_profile(
        self,
        *,
        company_id: Union[str, UUID],
        source_type: SourceType,
        mode: Optional[CrawlMode] = None,
        schedule: Optional[CrawlSchedule] = None,
    ) -> SourceProfile:
        """Ensure source profile exists and returns it."""
        company_uuid = company_id if isinstance(company_id, UUID) else UUID(str(company_id))
        result = await self.db.execute(
            select(SourceProfile).where(
                and_(
                    SourceProfile.company_id == company_uuid,
                    SourceProfile.source_type == source_type,
                )
            )
        )
        profile = result.scalar_one_or_none()

        if profile:
            updated = False
            if mode and profile.mode != mode:
                profile.mode = mode
                updated = True
            if schedule and profile.schedule_id != schedule.id:
                profile.schedule_id = schedule.id
                updated = True
            if updated:
                await self.db.commit()
                await self.db.refresh(profile)
            return profile

        schedule_id = schedule.id if schedule else None
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        profile = SourceProfile(
            company_id=company_uuid,
            source_type=source_type,
            mode=mode or CrawlMode.ALWAYS_UPDATE,
            schedule_id=schedule_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def record_run_start(self, profile: SourceProfile, schedule: Optional[CrawlSchedule]) -> CrawlRun:
        """Record start of crawl run."""
        now = datetime.now(timezone.utc)
        run = CrawlRun(
            profile_id=profile.id,
            schedule_id=schedule.id if schedule else None,
            status=CrawlStatus.RUNNING,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(run)
        profile.last_run_at = now
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def record_run_result(
        self,
        run: CrawlRun,
        *,
        success: bool,
        item_count: int,
        change_detected: bool,
        error_message: Optional[str] = None,
    ) -> CrawlRun:
        """Update crawl run with final status and adjust profile counters."""
        finish_time = datetime.now(timezone.utc)

        run.finished_at = finish_time
        run.item_count = item_count
        run.change_detected = change_detected
        run.status = CrawlStatus.SUCCESS if success else CrawlStatus.FAILED
        run.error_message = error_message

        profile = run.profile
        if success:
            profile.last_success_at = finish_time
            profile.consecutive_failures = 0
            profile.consecutive_no_change = 0 if change_detected else profile.consecutive_no_change + 1
        else:
            profile.last_error_at = finish_time
            profile.consecutive_failures += 1

        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def compute_effective_schedule(
        self,
        *,
        company_id: Union[str, UUID],
        source_type: SourceType,
    ) -> Tuple[int, CrawlMode, Optional[CrawlSchedule]]:
        """
        Resolve effective frequency and mode for a company/source combination.

        Priority order:
        1. Specific SOURCE schedule (explicit source id)
        2. COMPANY scope schedule
        3. SOURCE_TYPE schedule
        4. Defaults
        """
        # Specific source (company + source type)
        company_str = str(company_id)
        source_scope_value = f"{company_str}:{source_type.value}"
        schedule = await self.get_schedule(CrawlScope.SOURCE, source_scope_value)
        if schedule and schedule.enabled:
            return schedule.frequency_seconds, schedule.mode, schedule

        # Company-level
        schedule = await self.get_schedule(CrawlScope.COMPANY, company_str)
        if schedule and schedule.enabled:
            return schedule.frequency_seconds, schedule.mode, schedule

        # Source type
        schedule = await self.get_schedule(CrawlScope.SOURCE_TYPE, source_type.value)
        if schedule and schedule.enabled:
            return schedule.frequency_seconds, schedule.mode, schedule

        # Default fallback
        return self.default_frequency_for_source(source_type), CrawlMode.ALWAYS_UPDATE, None

    async def reapply_schedule(self, schedule: CrawlSchedule) -> None:
        """Update last applied timestamp and notify background workers if needed."""
        schedule.last_applied_at = datetime.now(timezone.utc)
        await self.db.commit()
        logger.info(
            "Reapplied crawl schedule %s (scope=%s:%s)",
            schedule.id,
            schedule.scope,
            schedule.scope_value,
        )

    async def hydrate_profiles(self) -> int:
        """
        Ensure profiles exist for all companies and supported source types.

        Returns number of profiles created in the process.
        """
        result = await self.db.execute(select(Company.id))
        company_ids = result.scalars().all()

        created = 0
        for company_id in company_ids:
            for source_type in SourceType:
                _, mode, schedule = await self.compute_effective_schedule(
                    company_id=company_id,
                    source_type=source_type,
                )
                profile = await self.ensure_source_profile(
                    company_id=company_id,
                    source_type=source_type,
                    mode=mode,
                    schedule=schedule,
                )
                if profile.created_at == profile.updated_at:  # freshly created
                    created += 1

        return created


async def load_effective_celery_schedule(db_factory, base_schedule: Dict[str, dict]) -> Dict[str, dict]:
    """
    Attempt to hydrate Celery beat schedule with DB-backed crawl schedules.

    Returns merged schedule; falls back to provided base schedule on failure.
    """
    try:
        async with db_factory() as session:  # type: AsyncSession
            service = CrawlScheduleService(session)
            dynamic_entries = await service.list_active_schedules()

            schedule_entries = dict(base_schedule)
            for entry in dynamic_entries:
                name = f"crawl-{entry.scope.value}-{entry.scope_value}"
                schedule_entries[name] = {
                    "task": "app.tasks.scraping.scrape_ai_blogs",
                    "schedule": entry.frequency_seconds,
                    "options": {
                        "queue": "scraping",
                        "headers": {
                            "crawl_scope": entry.scope.value,
                            "crawl_scope_value": entry.scope_value,
                            "crawl_mode": entry.mode.value,
                        },
                    },
                }
            
            if dynamic_entries:
                logger.info(
                    "Loaded %d dynamic crawl schedule(s) into beat schedule",
                    len(dynamic_entries)
                )
            else:
                logger.debug("No dynamic crawl schedules found, using base schedule only")
            
            return schedule_entries
    except Exception as exc:
        error_type = type(exc).__name__
        error_msg = str(exc)
        
        # Provide more specific error information
        if "connection" in error_msg.lower() or "connect" in error_msg.lower():
            logger.warning(
                "Failed to load dynamic crawl schedule (database connection issue): {}: {}. "
                "Using base schedule. This is normal if database is not ready yet.",
                error_type,
                error_msg
            )
        elif "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
            logger.warning(
                "Failed to load dynamic crawl schedule (table/relation not found): {}: {}. "
                "Using base schedule. This may indicate a migration is needed.",
                error_type,
                error_msg
            )
        else:
            logger.warning(
                "Failed to load dynamic crawl schedule, using defaults: {}: {}",
                error_type,
                error_msg,
                exc_info=True
            )
        return base_schedule



