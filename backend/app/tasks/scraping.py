"""
Web scraping tasks
"""

from celery import current_task
from loguru import logger
from typing import List
from uuid import UUID

from app.celery_app import celery_app
from app.core.celery_async import run_async_task
from app.core.database import AsyncSessionLocal
from app.domains.news import NewsFacade
from app.domains.news.scrapers.interfaces import CompanyContext
from app.models import Company
from app.models.news import SourceType
from app.scrapers.real_scrapers import AINewsScraper
from app.services.crawl_schedule_service import CrawlScheduleService
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

@celery_app.task(bind=True)
def scrape_ai_blogs(self):
    """
    Plan scraping tasks for AI company blogs.

    This task no longer scrapes directly. Instead, it schedules individual
    per-company tasks so that work can be distributed across workers.
    """
    logger.info("Starting AI blogs scraping planner task")
    
    try:
        result = run_async_task(_scrape_ai_blogs_plan_async())
        logger.info(
            "AI blogs scraping planner queued %d company task(s)",
            result["task_count"],
        )
        return result
        
    except Exception as e:
        logger.error(f"AI blogs scraping planner failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _scrape_ai_blogs_plan_async():
    """Async planner implementation for blog scraping."""
    async with AsyncSessionLocal() as db:
        # Пропускаем глобальные компании (user_id is None) для разгрузки системы
        result = await db.execute(
            select(Company)
            .where(
                Company.website.isnot(None),
                Company.user_id.isnot(None)  # Только компании пользователей, не глобальные
            )
            .order_by(Company.created_at.desc())
        )
        companies = result.scalars().all()

        logger.info(f"Planner found {len(companies)} companies with websites (excluding global companies)")

        schedule_service = CrawlScheduleService(db)
        now_utc = datetime.now(timezone.utc)
        due_companies: List[Company] = []

        for company in companies:
            try:
                frequency_seconds, mode, schedule = await schedule_service.compute_effective_schedule(
                    company_id=company.id,
                    source_type=SourceType.BLOG,
                )
                profile = await schedule_service.ensure_source_profile(
                    company_id=company.id,
                    source_type=SourceType.BLOG,
                    mode=mode,
                    schedule=schedule,
                )

                jitter_seconds = schedule.jitter_seconds if schedule else 0
                last_run_at = profile.last_run_at or datetime.fromtimestamp(0, timezone.utc)
                next_run_at = last_run_at + timedelta(seconds=frequency_seconds + jitter_seconds)

                if profile.last_run_at is None or now_utc >= next_run_at:
                    due_companies.append(company)
                else:
                    logger.debug(
                        "Skipping company %s (%s); next run at %s (freq=%ss jitter=%ss)",
                        company.id,
                        company.name,
                        next_run_at.isoformat(),
                        frequency_seconds,
                        jitter_seconds,
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to evaluate schedule for company %s (%s): %s",
                    company.id,
                    company.name,
                    exc,
                )
                continue

        if not due_companies:
            logger.info("No companies due for scraping at this time")
            return {"status": "idle", "task_count": 0, "task_ids": []}

        logger.info(
            "Planner determined %d company(ies) are due for scraping",
            len(due_companies),
        )

        queued_task_ids: List[str] = []
        for company in due_companies:
            task = scrape_company_news.delay(str(company.id))
            queued_task_ids.append(task.id)
            logger.debug(
                "Queued scrape_company_news for company %s (%s) task_id=%s",
                company.id,
                company.name,
                task.id,
            )

        return {
            "status": "queued",
            "task_count": len(queued_task_ids),
            "task_ids": queued_task_ids,
        }


@celery_app.task(bind=True)
def scrape_company_news(self, company_id: str):
    """
    Scrape news for a single company.
    """
    logger.info(f"Scraping news for company {company_id}")
    
    try:
        result = run_async_task(_scrape_company_news_async(company_id))
        logger.info(
            "Completed scraping for company %s: %s items (status=%s)",
            company_id,
            result.get("ingested", 0),
            result.get("status"),
        )
        return result
        
    except Exception as e:
        logger.error(f"Scraping failed for company {company_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _scrape_company_news_async(company_id: str, max_articles: int = 5):
    """Async implementation for scraping a single company's news."""
    async with AsyncSessionLocal() as db:
        company_uuid = UUID(company_id)
        result = await db.execute(select(Company).where(Company.id == company_uuid))
        company = result.scalar_one_or_none()

        if not company:
            logger.warning(f"Company {company_id} not found")
            return {"status": "error", "message": "Company not found"}

        # Пропускаем глобальные компании (user_id is None) для разгрузки системы
        if company.user_id is None:
            logger.info(f"Company {company_id} ({company.name}) is global (user_id is None), skipping news parsing")
            return {"status": "skipped", "reason": "global_company"}

        if not company.website:
            logger.warning(f"Company {company_id} has no website; skipping")
            return {"status": "skipped", "reason": "no_website"}

        facade = NewsFacade(db)
        schedule_service = CrawlScheduleService(db)

        frequency_seconds, mode, schedule = await schedule_service.compute_effective_schedule(
            company_id=company.id,
            source_type=SourceType.BLOG,
        )
        profile = await schedule_service.ensure_source_profile(
            company_id=company.id,
            source_type=SourceType.BLOG,
            mode=mode,
            schedule=schedule,
        )
        crawl_run = await schedule_service.record_run_start(profile, schedule)

        context = CompanyContext(
            id=company.id,
            name=company.name or "",
            website=company.website,
            news_page_url=getattr(company, "news_page_url", None),
        )

        try:
            ingested = await facade.scraper_service.ingest_company_news(
                context,
                max_articles=max_articles,
            )
            await schedule_service.record_run_result(
                crawl_run,
                success=True,
                item_count=ingested,
                change_detected=ingested > 0,
            )
            return {
                "status": "success",
                "company_id": company_id,
                "ingested": ingested,
                "frequency_seconds": frequency_seconds,
            }
        except Exception as exc:
            await schedule_service.record_run_result(
                crawl_run,
                success=False,
                item_count=0,
                change_detected=False,
                error_message=str(exc),
            )
            logger.error(
                "Error scraping company %s (%s): %s",
                company_id,
                company.name,
                exc,
            )
            raise


@celery_app.task(bind=True)
def fetch_social_media(self):
    """
    Fetch content from social media platforms
    """
    logger.info("Starting social media fetching task")
    
    try:
        # TODO: Implement social media fetching
        # 1. Fetch Twitter/X posts from AI companies
        # 2. Fetch Reddit posts from AI communities
        # 3. Process and classify content
        # 4. Store in database
        
        logger.info("Social media fetching completed successfully")
        return {"status": "success", "fetched_count": 0}
        
    except Exception as e:
        logger.error(f"Social media fetching failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def monitor_github(self):
    """
    Monitor GitHub repositories for updates
    """
    logger.info("Starting GitHub monitoring task")
    
    try:
        # TODO: Implement GitHub monitoring
        # 1. Check for new releases in AI repositories
        # 2. Monitor star growth and activity
        # 3. Process significant changes
        # 4. Store in database
        
        logger.info("GitHub monitoring completed successfully")
        return {"status": "success", "monitored_count": 0}
        
    except Exception as e:
        logger.error(f"GitHub monitoring failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def cleanup_old_data(self):
    """
    Cleanup old data to maintain performance
    """
    logger.info("Starting data cleanup task")
    
    try:
        # TODO: Implement data cleanup
        # 1. Remove old news items (>6 months)
        # 2. Clean up temporary files
        # 3. Optimize database indexes
        # 4. Update statistics
        
        logger.info("Data cleanup completed successfully")
        return {"status": "success", "cleaned_count": 0}
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def scan_company_sources_initial(self, company_id: str):
    """
    Первичное сканирование всех возможных источников компании.
    
    Проверяет все возможные URL источников (даже те, что возвращают 404)
    и сохраняет результаты в SourceHealthService для последующего исключения
    неработающих источников.
    
    Args:
        company_id: UUID компании в виде строки
    """
    logger.info(f"Starting initial source scan for company {company_id}")
    
    try:
        result = run_async_task(_scan_company_sources_initial_async(company_id))
        logger.info(
            f"Initial source scan completed for company {company_id}: "
            f"{result['checked_urls']} URLs checked, "
            f"{result['disabled_urls']} URLs disabled"
        )
        return result
        
    except Exception as e:
        logger.error(f"Initial source scan failed for company {company_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _scan_company_sources_initial_async(company_id: str):
    """Async implementation of initial source scanning"""
    from uuid import UUID
    from app.domains.news.services.source_health_service import SourceHealthService
    from app.scrapers.universal_scraper import UniversalBlogScraper
    from app.scrapers.config_loader import ScraperConfigRegistry
    from app.models.news import SourceType
    import httpx
    
    async with AsyncSessionLocal() as db:
        # Получаем компанию
        result = await db.execute(
            select(Company).where(Company.id == UUID(company_id))
        )
        company = result.scalar_one_or_none()
        
        if not company:
            logger.warning(f"Company {company_id} not found")
            return {
                "status": "error",
                "message": "Company not found",
                "checked_urls": 0,
                "disabled_urls": 0,
            }
        
        # Пропускаем глобальные компании (user_id is None) для разгрузки системы
        if company.user_id is None:
            logger.info(f"Company {company_id} ({company.name}) is global (user_id is None), skipping source scan")
            return {
                "status": "skipped",
                "message": "Global company - news parsing disabled",
                "checked_urls": 0,
                "disabled_urls": 0,
            }
        
        if not company.website:
            logger.warning(f"Company {company_id} has no website")
            return {
                "status": "error",
                "message": "Company has no website",
                "checked_urls": 0,
                "disabled_urls": 0,
            }
        
        # Инициализируем сервисы
        health_service = SourceHealthService(db)
        scraper = UniversalBlogScraper()
        config_registry = ScraperConfigRegistry()
        
        # Получаем все возможные URL источников
        source_configs = config_registry.get_sources(
            company_name=company.name or "",
            website=company.website,
            manual_url=None,
            overrides=None,
        )
        
        # Также добавляем эвристические URL
        from urllib.parse import urlparse
        parsed = urlparse(company.website)
        if parsed.scheme and parsed.netloc:
            base_domain = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
            heuristic_urls = [
                f"{base_domain}/blog",
                f"{base_domain}/blogs",
                f"{base_domain}/blog/",
                f"{base_domain}/blogs/",
                f"{base_domain}/news",
                f"{base_domain}/news/",
                f"{base_domain}/insights",
                f"{base_domain}/updates",
                f"{base_domain}/press",
                f"{base_domain}/newsroom",
                f"{base_domain}/press-releases",
                f"{base_domain}/company/blog",
                f"{base_domain}/company/news",
                f"{base_domain}/resources/blog",
                f"{base_domain}/hub/blog",
            ]
        else:
            heuristic_urls = []
        
        # Собираем все уникальные URL
        all_urls = set()
        for source_config in source_configs:
            for url in source_config.urls:
                normalized = scraper._normalize_url(str(url))
                all_urls.add(normalized)
        
        for url in heuristic_urls:
            normalized = scraper._normalize_url(url)
            all_urls.add(normalized)
        
        logger.info(
            f"Checking {len(all_urls)} unique URLs for company {company_id} "
            f"({company.name})"
        )
        
        # Проверяем каждый URL
        checked_count = 0
        disabled_count = 0
        company_uuid = UUID(company_id)
        
        # Используем httpx для быстрой проверки статуса
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            for normalized_url in all_urls:
                checked_count += 1
                try:
                    # Быстрая проверка HEAD запросом (меньше трафика)
                    response = await client.head(normalized_url, timeout=5.0)
                    status = response.status_code
                    success = status == 200
                    items_count = 0  # Для HEAD запроса не знаем количество статей
                    
                    # Если HEAD не поддерживается, пробуем GET
                    if status == 405:  # Method Not Allowed
                        response = await client.get(normalized_url, timeout=5.0)
                        status = response.status_code
                        success = status == 200
                        # Простая проверка наличия контента
                        if success and response.text:
                            # Проверяем наличие признаков статей
                            text_lower = response.text.lower()
                            if any(keyword in text_lower for keyword in ["article", "post", "blog", "news"]):
                                items_count = 1  # Предполагаем, что есть контент
                    
                    # Записываем результат в SourceHealthService
                    await health_service.record_result(
                        company_id=company_uuid,
                        source_url=normalized_url,
                        success=success,
                        status=status,
                        items_count=items_count,
                        source_type=SourceType.BLOG,
                    )
                    
                    if not success or items_count == 0:
                        logger.debug(
                            f"URL {normalized_url} for company {company_id}: "
                            f"status={status}, items={items_count}"
                        )
                        if status in (404, 410):
                            disabled_count += 1
                    
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    await health_service.record_result(
                        company_id=company_uuid,
                        source_url=normalized_url,
                        success=False,
                        status=status,
                        items_count=0,
                        source_type=SourceType.BLOG,
                    )
                    if status in (404, 410):
                        disabled_count += 1
                    logger.debug(
                        f"URL {normalized_url} returned {status} for company {company_id}"
                    )
                except Exception as exc:
                    logger.debug(
                        f"Failed to check URL {normalized_url} for company {company_id}: {exc}"
                    )
                    # Записываем как ошибку
                    await health_service.record_result(
                        company_id=company_uuid,
                        source_url=normalized_url,
                        success=False,
                        status=0,  # Unknown error
                        items_count=0,
                        source_type=SourceType.BLOG,
                    )
        
        await scraper.close()
        await db.commit()
        
        logger.info(
            f"Initial source scan completed for company {company_id}: "
            f"{checked_count} URLs checked, {disabled_count} URLs will be disabled "
            f"after reaching fail threshold"
        )
        
        return {
            "status": "success",
            "company_id": company_id,
            "checked_urls": checked_count,
            "disabled_urls": disabled_count,
        }
