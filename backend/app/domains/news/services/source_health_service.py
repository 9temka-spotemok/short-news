"""
Service for tracking source health and managing dead URLs.

Tracks URLs that consistently return 404 or empty responses and disables them
to prevent unnecessary requests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl import SourceProfile
from app.models.news import SourceType


class SourceHealthService:
    """
    Service for managing source health tracking.
    
    Stores dead URLs in SourceProfile.metadata_json['dead_urls'] with structure:
    {
        "normalized_url": {
            "status": "disabled" | "recovering" | "healthy",
            "fail_count": 5,
            "last_error": "404 Not Found" | "Empty response",
            "disabled_until": "2025-01-20T12:00:00Z" | null,  # null для постоянных отключений
            "permanent": true | false,  # true для 404/410 (навсегда), false для пустых ответов (временно)
            "last_success": "2025-01-15T10:00:00Z"
        }
    }
    
    Логика отключения:
    - 404/410: отключаются навсегда (permanent=true, disabled_until=null)
    - Пустые ответы: отключаются временно на 24 часа (permanent=false, disabled_until=дата)
    """

    FAIL_THRESHOLD = 5  # Number of consecutive failures before disabling
    DISABLE_DURATION_HOURS = 24  # Hours to keep URL disabled (for empty responses only)
    # 404/410 errors are disabled permanently (no expiration)

    def __init__(self, session: AsyncSession):
        """
        Initialize source health service.
        
        Args:
            session: Database session
        """
        self._session = session

    async def get_dead_urls(self, company_id: UUID) -> Set[str]:
        """
        Get set of disabled URLs for a company.
        
        Args:
            company_id: Company UUID
            
        Returns:
            Set of normalized URLs that should be skipped
        """
        profiles = await self._get_source_profiles(company_id)
        dead_urls: Set[str] = set()
        now = datetime.now(timezone.utc)

        for profile in profiles:
            metadata = profile.metadata_json or {}
            dead_urls_data = metadata.get("dead_urls", {})

            for normalized_url, url_data in dead_urls_data.items():
                status = url_data.get("status", "healthy")
                
                if status == "disabled":
                    # Проверяем, является ли отключение постоянным (404/410)
                    is_permanent = url_data.get("permanent", False)
                    
                    if is_permanent:
                        # Постоянное отключение (404/410) - всегда пропускаем
                        dead_urls.add(normalized_url)
                        logger.debug(
                            f"URL {normalized_url} is permanently disabled (404/410) "
                            f"for company {company_id}"
                        )
                    else:
                        # Временное отключение (пустые ответы) - проверяем срок
                        disabled_until_str = url_data.get("disabled_until")
                        if disabled_until_str:
                            try:
                                disabled_until = datetime.fromisoformat(
                                    disabled_until_str.replace("Z", "+00:00")
                                )
                                if disabled_until > now:
                                    # URL is still disabled
                                    dead_urls.add(normalized_url)
                                    logger.debug(
                                        f"URL {normalized_url} is disabled until {disabled_until} "
                                        f"for company {company_id}"
                                    )
                                else:
                                    # Disable period expired, mark as recovering
                                    logger.debug(
                                        f"Disable period expired for {normalized_url}, "
                                        f"marking as recovering"
                                    )
                                    url_data["status"] = "recovering"
                                    url_data["disabled_until"] = None
                                    await self._save_profile_metadata(profile, metadata)
                            except (ValueError, AttributeError) as exc:
                                logger.warning(
                                    f"Failed to parse disabled_until for {normalized_url}: {exc}"
                                )
                                # Remove invalid entry
                                dead_urls_data.pop(normalized_url, None)
                                await self._save_profile_metadata(profile, metadata)
                        else:
                            # Нет disabled_until, но статус disabled - считаем постоянным
                            dead_urls.add(normalized_url)
                            logger.debug(
                                f"URL {normalized_url} is disabled (no expiration) "
                                f"for company {company_id}"
                            )

        # Обновляем метрику количества отключенных URL
        try:
            from app.instrumentation.celery_metrics import _metrics
            _metrics.update_dead_urls_count(str(company_id), len(dead_urls))
        except Exception:
            pass

        return dead_urls

    async def record_result(
        self,
        company_id: UUID,
        source_url: str,
        success: bool,
        status: int,
        items_count: int,
        source_type: Optional[SourceType] = None,
    ) -> None:
        """
        Record result of a source fetch attempt.
        
        Args:
            company_id: Company UUID
            source_url: Source URL (will be normalized)
            success: Whether fetch was successful
            status: HTTP status code
            items_count: Number of items found
            source_type: Optional source type for filtering profiles
        """
        from app.scrapers.universal_scraper import UniversalBlogScraper

        # Normalize URL
        scraper = UniversalBlogScraper()
        normalized_url = scraper._normalize_url(source_url)
        await scraper.close()

        # Get or create source profile
        profile = await self._get_or_create_profile(company_id, source_type)

        metadata = profile.metadata_json or {}
        dead_urls = metadata.setdefault("dead_urls", {})

        url_data = dead_urls.setdefault(normalized_url, {
            "status": "healthy",
            "fail_count": 0,
            "last_error": None,
            "disabled_until": None,
            "last_success": None,
            "permanent": False,  # Флаг постоянного отключения (для 404/410)
        })

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        if success and items_count > 0:
            # Success - reset fail count and mark as healthy
            # Если URL был отключен, но теперь работает - снимаем отключение
            url_data["status"] = "healthy"
            url_data["fail_count"] = 0
            url_data["last_success"] = now_iso
            url_data["disabled_until"] = None
            url_data["last_error"] = None
            url_data["permanent"] = False  # Снимаем постоянное отключение, если было
            logger.info(
                f"URL {normalized_url} succeeded, resetting fail count and re-enabling "
                f"for company {company_id}"
            )
        elif status in (404, 410):
            # 404/410 - постоянная ошибка, отключаем навсегда
            url_data["fail_count"] = url_data.get("fail_count", 0) + 1
            url_data["last_error"] = f"{status} Not Found"

            if url_data["fail_count"] >= self.FAIL_THRESHOLD:
                # Отключаем навсегда (permanent)
                url_data["status"] = "disabled"
                url_data["permanent"] = True
                url_data["disabled_until"] = None  # Нет срока истечения
                logger.info(
                    f"URL {normalized_url} permanently disabled (404/410) for company {company_id} "
                    f"(fail_count={url_data['fail_count']})"
                )
            else:
                url_data["status"] = "recovering" if url_data.get("status") == "disabled" else "healthy"
                logger.debug(
                    f"URL {normalized_url} returned 404/410 (fail_count={url_data['fail_count']}/"
                    f"{self.FAIL_THRESHOLD}) for company {company_id}"
                )
        elif items_count == 0:
            # Пустой ответ - временная проблема, отключаем на 24 часа
            url_data["fail_count"] = url_data.get("fail_count", 0) + 1
            url_data["last_error"] = "Empty response"

            if url_data["fail_count"] >= self.FAIL_THRESHOLD:
                # Отключаем временно (на 24 часа)
                url_data["status"] = "disabled"
                url_data["permanent"] = False
                disabled_until = now + timedelta(hours=self.DISABLE_DURATION_HOURS)
                url_data["disabled_until"] = disabled_until.isoformat()
                logger.info(
                    f"URL {normalized_url} temporarily disabled (empty response) for company {company_id} "
                    f"(fail_count={url_data['fail_count']}, disabled_until={disabled_until})"
                )
            else:
                url_data["status"] = "recovering" if url_data.get("status") == "disabled" else "healthy"
                logger.debug(
                    f"URL {normalized_url} returned empty response (fail_count={url_data['fail_count']}/"
                    f"{self.FAIL_THRESHOLD}) for company {company_id}"
                )
        else:
            # Other error - don't count as failure for dead URL tracking
            logger.debug(
                f"URL {normalized_url} returned status {status} for company {company_id}, "
                f"not counting as dead URL failure"
            )

        await self._save_profile_metadata(profile, metadata)

    async def should_skip_url(self, company_id: UUID, source_url: str) -> bool:
        """
        Check if URL should be skipped.
        
        Args:
            company_id: Company UUID
            source_url: Source URL (will be normalized)
            
        Returns:
            True if URL should be skipped
        """
        from app.scrapers.universal_scraper import UniversalBlogScraper

        # Normalize URL
        scraper = UniversalBlogScraper()
        normalized_url = scraper._normalize_url(source_url)
        await scraper.close()

        dead_urls = await self.get_dead_urls(company_id)
        return normalized_url in dead_urls

    async def _get_source_profiles(
        self, company_id: UUID, source_type: Optional[SourceType] = None
    ) -> list[SourceProfile]:
        """Get source profiles for company."""
        query = select(SourceProfile).where(SourceProfile.company_id == company_id)
        if source_type:
            query = query.where(SourceProfile.source_type == source_type)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def _get_or_create_profile(
        self, company_id: UUID, source_type: Optional[SourceType] = None
    ) -> SourceProfile:
        """Get or create source profile."""
        from app.models.news import SourceType as ST

        # Default to BLOG if not specified
        if source_type is None:
            source_type = ST.BLOG

        result = await self._session.execute(
            select(SourceProfile).where(
                SourceProfile.company_id == company_id,
                SourceProfile.source_type == source_type,
            )
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            from app.models.crawl import CrawlMode

            profile = SourceProfile(
                company_id=company_id,
                source_type=source_type,
                mode=CrawlMode.ALWAYS_UPDATE,
                metadata_json={},
            )
            self._session.add(profile)
            await self._session.flush()

        return profile

    async def _save_profile_metadata(self, profile: SourceProfile, metadata: Dict) -> None:
        """Save updated metadata to profile."""
        profile.metadata_json = metadata
        await self._session.commit()
        await self._session.refresh(profile)

