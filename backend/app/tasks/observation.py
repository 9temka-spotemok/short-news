"""
Celery tasks for competitor observation setup
"""

from loguru import logger
from typing import List, Dict, Any
from uuid import UUID

from app.celery_app import celery_app
from app.core.celery_async import run_async_task
from app.core.celery_database import CelerySessionLocal
from app.models import OnboardingSession, Company, CompetitorMonitoringMatrix
from app.services.social_media_extractor import SocialMediaExtractor
from app.services.website_structure_monitor import WebsiteStructureMonitor
from app.services.marketing_change_detector import MarketingChangeDetector
from app.services.seo_signal_collector import SEOSignalCollector
from app.scrapers.press_release_scraper import PressReleaseScraper
from app.domains.news.facade import NewsFacade
from sqlalchemy import select
from datetime import datetime, timezone


@celery_app.task(bind=True)
def setup_competitor_observation(self, session_token: str, company_ids: List[str]):
    """
    Главная задача настройки наблюдения за конкурентами.
    
    Координирует все подзадачи:
    1. Поиск соцсетей конкурентов
    2. Парсинг сайтов (структурные изменения)
    3. Сбор новостей + пресс-релизов
    4. Отслеживание маркетинговых изменений
    5. Сбор сигналов SEO/SEM
    6. Формирование матрицы мониторинга
    
    Args:
        session_token: Токен сессии онбординга
        company_ids: Список ID компаний для наблюдения
    
    Returns:
        Dict с результатами настройки наблюдения
    """
    logger.info(f"Starting observation setup for session {session_token[:8]}... with {len(company_ids)} companies")
    
    try:
        # Передаем self (task instance) в async функцию для обновления прогресса
        result = run_async_task(_setup_competitor_observation_async(self, session_token, company_ids))
        logger.info(f"Observation setup completed for session {session_token[:8]}...")
        return result
        
    except Exception as e:
        logger.error(f"Observation setup failed for session {session_token[:8]}...: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _setup_competitor_observation_async(task_instance, session_token: str, company_ids: List[str]) -> Dict[str, Any]:
    """
    Async реализация настройки наблюдения.
    
    Args:
        task_instance: Экземпляр Celery задачи для обновления прогресса
        session_token: Токен сессии онбординга
        company_ids: Список ID компаний для наблюдения
    """
    async with CelerySessionLocal() as db:
        # Получить сессию онбординга
        result = await db.execute(
            select(OnboardingSession).where(
                OnboardingSession.session_token == session_token
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError(f"Onboarding session not found: {session_token[:8]}...")
        
        total_companies = len(company_ids)
        completed = 0
        errors = []
        
        # Обновить статус в сессии
        if not session.observation_config:
            session.observation_config = {}
        
        session.observation_config.update({
            "status": "processing",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "total_companies": total_companies,
            "completed_companies": 0,
            "current_step": "initializing"
        })
        await db.commit()
        
        # Обновить прогресс через Celery
        if task_instance:
            task_instance.update_state(
                state='PROGRESS',
                meta={
                    'progress': 0,
                    'message': 'Инициализация наблюдения...',
                    'current_step': 'initializing',
                    'total': total_companies,
                    'completed': 0
                }
            )
        
        logger.info(f"Processing {total_companies} companies for observation setup")
        
        # Обработать каждую компанию
        for idx, company_id_str in enumerate(company_ids):
            try:
                company_uuid = UUID(company_id_str)
                
                # Получить компанию
                company_result = await db.execute(
                    select(Company).where(Company.id == company_uuid)
                )
                company = company_result.scalar_one_or_none()
                
                if not company:
                    logger.warning(f"Company not found: {company_id_str}")
                    errors.append({"company_id": company_id_str, "error": "Company not found"})
                    continue
                
                logger.info(f"Processing company {company.name} ({company_id_str})")
                
                # Обновить прогресс
                progress = int((idx / total_companies) * 100)
                step_name = f"Обработка компании {company.name} ({idx + 1}/{total_companies})"
                
                if task_instance:
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress,
                            'message': step_name,
                            'current_step': 'processing_company',
                            'current_company': company.name,
                            'total': total_companies,
                            'completed': idx
                        }
                    )
                
                # Обновить статус в сессии
                session.observation_config.update({
                    "current_step": "processing_company",
                    "current_company": company.name,
                    "completed_companies": idx,
                    "progress": progress
                })
                await db.commit()
                
                # Шаг 1: Поиск соцсетей
                logger.info(f"Step 1/5: Discovering social media for {company.name}")
                if task_instance:
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress + 5,
                            'message': f'Поиск соцсетей для {company.name}...',
                            'current_step': 'discovering_social_media',
                            'current_company': company.name,
                            'total': total_companies,
                            'completed': idx
                        }
                    )
                # Реальный вызов поиска соцсетей
                await discover_social_media_async(db, company_id_str, company)
                
                # Шаг 2: Парсинг структуры сайта
                logger.info(f"Step 2/5: Capturing website structure for {company.name}")
                if task_instance:
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress + 10,
                            'message': f'Парсинг структуры сайта {company.name}...',
                            'current_step': 'capturing_structure',
                            'current_company': company.name,
                            'total': total_companies,
                            'completed': idx
                        }
                    )
                # Реальный вызов парсинга структуры сайта (базовая реализация)
                await capture_website_structure_async(db, company_id_str, company)
                
                # Шаг 3: Сбор пресс-релизов
                logger.info(f"Step 3/5: Scraping press releases for {company.name}")
                if task_instance:
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress + 15,
                            'message': f'Сбор пресс-релизов для {company.name}...',
                            'current_step': 'scraping_press_releases',
                            'current_company': company.name,
                            'total': total_companies,
                            'completed': idx
                        }
                    )
                # Реальный вызов сбора пресс-релизов (базовая реализация)
                await scrape_press_releases_async(db, company_id_str, company)
                
                # Шаг 4: Отслеживание маркетинга
                logger.info(f"Step 4/5: Detecting marketing changes for {company.name}")
                if task_instance:
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress + 20,
                            'message': f'Отслеживание маркетинга для {company.name}...',
                            'current_step': 'detecting_marketing',
                            'current_company': company.name,
                            'total': total_companies,
                            'completed': idx
                        }
                    )
                # Реальный вызов отслеживания маркетинга (базовая реализация)
                await detect_marketing_changes_async(db, company_id_str, company)
                
                # Шаг 5: Сбор SEO сигналов
                logger.info(f"Step 5/5: Collecting SEO signals for {company.name}")
                if task_instance:
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress + 25,
                            'message': f'Сбор SEO сигналов для {company.name}...',
                            'current_step': 'collecting_seo',
                            'current_company': company.name,
                            'total': total_companies,
                            'completed': idx
                        }
                    )
                # Реальный вызов сбора SEO сигналов (базовая реализация)
                await collect_seo_signals_async(db, company_id_str, company)
                
                completed += 1
                logger.info(f"Completed observation setup for {company.name}")
                
            except Exception as e:
                logger.error(f"Error processing company {company_id_str}: {e}")
                errors.append({"company_id": company_id_str, "error": str(e)})
                continue
        
        # Финальный шаг: Формирование матрицы мониторинга
        logger.info("Final step: Building monitoring matrix")
        if task_instance:
            task_instance.update_state(
                state='PROGRESS',
                meta={
                    'progress': 95,
                    'message': 'Формирование матрицы мониторинга...',
                    'current_step': 'building_matrix',
                    'total': total_companies,
                    'completed': completed
                }
            )
        # Реальный вызов формирования матрицы мониторинга
        await build_monitoring_matrix_async(db, company_ids)
        
        # Обновить финальный статус
        final_status = "completed" if len(errors) == 0 else "completed_with_errors"
        session.observation_config.update({
            "status": final_status,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "completed_companies": completed,
            "progress": 100,
            "current_step": "completed",
            "errors": errors if errors else None
        })
        await db.commit()
        
        if task_instance:
            task_instance.update_state(
                state='SUCCESS',
                meta={
                    'progress': 100,
                    'message': 'Наблюдение настроено успешно!',
                    'current_step': 'completed',
                    'total': total_companies,
                    'completed': completed,
                    'errors': len(errors)
                }
            )
        
        logger.info(f"Observation setup completed: {completed}/{total_companies} companies, {len(errors)} errors")
        
        return {
            "status": final_status,
            "total_companies": total_companies,
            "completed_companies": completed,
            "errors": errors,
            "message": f"Наблюдение настроено для {completed} из {total_companies} компаний"
        }


async def discover_social_media_async(db, company_id_str: str, company: Company) -> Dict[str, Any]:
    """
    Async функция для поиска соцсетей компании.
    
    Args:
        db: Database session
        company_id_str: ID компании (строка)
        company: Объект Company
        
    Returns:
        Словарь с результатами поиска
    """
    extractor = SocialMediaExtractor()
    
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Извлечь соцсети
        social_urls = await extractor.extract_social_media_from_website(company.website)
        
        # Обновить модель Company
        if social_urls.get('facebook'):
            company.facebook_url = social_urls['facebook']
        if social_urls.get('instagram'):
            company.instagram_url = social_urls['instagram']
        if social_urls.get('linkedin'):
            company.linkedin_url = social_urls['linkedin']
        if social_urls.get('youtube'):
            company.youtube_url = social_urls['youtube']
        if social_urls.get('tiktok'):
            company.tiktok_url = social_urls['tiktok']
        if social_urls.get('twitter'):
            # Twitter уже есть в модели как twitter_handle
            # Можно обновить, если нужно
            pass
        
        await db.commit()
        
        # Обновить или создать CompetitorMonitoringMatrix
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if not matrix:
            matrix = CompetitorMonitoringMatrix(
                company_id=company.id,
                monitoring_config={},
                social_media_sources={},
                website_sources={},
                news_sources={},
                marketing_sources={},
                seo_signals={},
                last_updated=datetime.now(timezone.utc)
            )
            db.add(matrix)
        
        # Обновить social_media_sources
        matrix.social_media_sources = {
            **matrix.social_media_sources,
            **{k: {"url": v, "discovered_at": datetime.now(timezone.utc).isoformat()} 
               for k, v in social_urls.items() if v}
        }
        matrix.last_updated = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"Discovered {sum(1 for v in social_urls.values() if v)} social media URLs for {company.name}")
        
        return social_urls
        
    except Exception as e:
        logger.error(f"Error discovering social media for company {company_id_str}: {e}")
        return {}
    finally:
        await extractor.close()


async def capture_website_structure_async(db, company_id_str: str, company: Company) -> Dict[str, Any]:
    """
    Async функция для захвата структуры сайта.
    
    Args:
        db: Database session
        company_id_str: ID компании (строка)
        company: Объект Company
        
    Returns:
        Словарь с результатами захвата структуры
    """
    monitor = WebsiteStructureMonitor()
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Захватить снимок структуры через WebsiteStructureMonitor
        snapshot = await monitor.capture_website_snapshot(company.website)
        
        if not snapshot:
            logger.warning(f"Failed to capture snapshot for {company.name}")
            return {}
        
        # Получить или создать матрицу мониторинга
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if not matrix:
            matrix = CompetitorMonitoringMatrix(
                company_id=company.id,
                monitoring_config={},
                social_media_sources={},
                website_sources={},
                news_sources={},
                marketing_sources={},
                seo_signals={},
                last_updated=datetime.now(timezone.utc)
            )
            db.add(matrix)
        
        # Сохранить снимок в website_sources
        if not matrix.website_sources:
            matrix.website_sources = {}
        
        # Сохранить текущий снимок
        snapshots = matrix.website_sources.get("snapshots", [])
        snapshots.append(snapshot)
        
        # Оставить только последние 10 снимков
        if len(snapshots) > 10:
            snapshots = snapshots[-10:]
        
        matrix.website_sources.update({
            "snapshots": snapshots,
            "current_snapshot": snapshot,
            "last_snapshot_at": snapshot.get("captured_at"),
            "website_url": company.website,
            "status": "captured",
            "key_pages_count": len([p for p in snapshot.get("key_pages", []) if p.get("found")]),
        })
        matrix.last_updated = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"Captured website structure for {company.name}: {len(snapshot.get('key_pages', []))} key pages found")
        return {
            "status": "captured",
            "website": company.website,
            "key_pages_found": len([p for p in snapshot.get("key_pages", []) if p.get("found")]),
            "navigation_links": len(snapshot.get("navigation", {}).get("links", [])),
        }
        
    except Exception as e:
        logger.error(f"Error capturing website structure for company {company_id_str}: {e}")
        return {}
    finally:
        await monitor.close()


async def scrape_press_releases_async(db, company_id_str: str, company: Company) -> Dict[str, Any]:
    """
    Async функция для сбора пресс-релизов.
    
    Args:
        db: Database session
        company_id_str: ID компании (строка)
        company: Объект Company
        
    Returns:
        Словарь с результатами сбора пресс-релизов
    """
    scraper = PressReleaseScraper()
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Найти страницу с пресс-релизами
        press_release_url = await scraper.find_press_release_page(company.website)
        
        if not press_release_url:
            logger.info(f"No press release page found for {company.name}")
            return {"status": "not_found", "count": 0}
        
        # Парсить пресс-релизы
        press_releases = await scraper.scrape_press_releases(press_release_url, limit=20)
        
        if not press_releases:
            logger.info(f"No press releases found for {company.name}")
            return {"status": "no_releases", "count": 0}
        
        # Сохранить через NewsIngestionService
        from app.models.news import SourceType, NewsCategory
        from app.utils.datetime_utils import parse_iso_datetime, to_naive_utc
        
        news_facade = NewsFacade(db)
        created_count = 0
        skipped_count = 0
        
        for release in press_releases:
            try:
                # Подготовить данные для NewsIngestionService
                news_data = {
                    "title": release.get("title", ""),
                    "source_url": release.get("url", ""),
                    "source_type": SourceType.PRESS_RELEASE.value,
                    "category": NewsCategory.STRATEGIC_ANNOUNCEMENT.value,
                    "summary": release.get("summary") or release.get("content", "")[:500],
                    "content": release.get("content", ""),
                    "published_at": release.get("published_at"),
                    "company_id": str(company.id),
                }
                
                # Создать новость
                news_item = await news_facade.ingestion_service.create_news_item(news_data)
                
                if hasattr(news_item, "_was_created") and news_item._was_created:
                    created_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logger.warning(f"Error creating news item for press release {release.get('url')}: {e}")
                skipped_count += 1
                continue
        
        # Обновить матрицу мониторинга
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if not matrix:
            matrix = CompetitorMonitoringMatrix(
                company_id=company.id,
                monitoring_config={},
                social_media_sources={},
                website_sources={},
                news_sources={},
                marketing_sources={},
                seo_signals={},
                last_updated=datetime.now(timezone.utc)
            )
            db.add(matrix)
        
        if not matrix.news_sources:
            matrix.news_sources = {}
        
        matrix.news_sources.update({
            "last_scraped_at": datetime.now(timezone.utc).isoformat(),
            "press_release_url": press_release_url,
            "press_releases_count": len(press_releases),
            "status": "scraped"
        })
        matrix.last_updated = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"Scraped press releases for {company.name}: {created_count} created, {skipped_count} skipped")
        return {
            "status": "completed",
            "count": len(press_releases),
            "created": created_count,
            "skipped": skipped_count,
        }
        
    except Exception as e:
        logger.error(f"Error scraping press releases for company {company_id_str}: {e}")
        return {}
    finally:
        await scraper.close()


async def detect_marketing_changes_async(db, company_id_str: str, company: Company) -> Dict[str, Any]:
    """
    Async функция для отслеживания маркетинговых изменений.
    
    Args:
        db: Database session
        company_id_str: ID компании (строка)
        company: Объект Company
        
    Returns:
        Словарь с результатами отслеживания маркетинга
    """
    detector = MarketingChangeDetector()
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Получить или создать матрицу мониторинга
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if not matrix:
            matrix = CompetitorMonitoringMatrix(
                company_id=company.id,
                monitoring_config={},
                social_media_sources={},
                website_sources={},
                news_sources={},
                marketing_sources={},
                seo_signals={},
                last_updated=datetime.now(timezone.utc)
            )
            db.add(matrix)
        
        if not matrix.marketing_sources:
            matrix.marketing_sources = {}
        
        previous_marketing = matrix.marketing_sources
        
        # Найти ключевые страницы из website_sources
        website_sources = matrix.website_sources or {}
        current_snapshot = website_sources.get("current_snapshot", {})
        key_pages = current_snapshot.get("key_pages", [])
        
        pricing_url = next((p.get("url") for p in key_pages if p.get("type") == "pricing" and p.get("found")), None)
        features_url = next((p.get("url") for p in key_pages if p.get("type") == "features" and p.get("found")), None)
        careers_url = next((p.get("url") for p in key_pages if p.get("type") == "careers" and p.get("found")), None)
        
        events_created = 0
        from app.models import (
            CompetitorChangeEvent,
            SourceType,
            ChangeProcessingStatus,
            ChangeNotificationStatus,
        )
        
        # Детекция изменений баннеров
        previous_banners = previous_marketing.get("banners")
        banner_result = await detector.detect_banner_changes(company.website, previous_banners)
        if banner_result.get("has_changes"):
            current_banners = banner_result.get("current_banners", {})
            matrix.marketing_sources["banners"] = current_banners
            
            event = CompetitorChangeEvent(
                company_id=company.id,
                source_type=SourceType.BLOG,
                change_summary=f"Banner changes detected: {len(banner_result.get('changes', {}).get('added_banners', []))} added, {len(banner_result.get('changes', {}).get('removed_banners', []))} removed",
                changed_fields=[banner_result.get("changes", {})],
                raw_diff={"type": "banners", "changes": banner_result.get("changes", {})},
                detected_at=datetime.now(timezone.utc),
                processing_status=ChangeProcessingStatus.SUCCESS,
                notification_status=ChangeNotificationStatus.PENDING,
            )
            db.add(event)
            events_created += 1
        elif banner_result.get("current_banners"):
            matrix.marketing_sources["banners"] = banner_result.get("current_banners")
        
        # Детекция изменений цен
        if pricing_url:
            previous_pricing = previous_marketing.get("pricing")
            pricing_result = await detector.detect_pricing_changes(pricing_url, previous_pricing)
            if pricing_result.get("has_changes"):
                current_pricing = pricing_result.get("current_pricing", {})
                matrix.marketing_sources["pricing"] = current_pricing
                
                changes = pricing_result.get("changes", {})
                event = CompetitorChangeEvent(
                    company_id=company.id,
                    source_type=SourceType.BLOG,
                    change_summary=f"Pricing changes detected: {len(changes.get('price_changes', []))} price updates, {len(changes.get('added_plans', []))} new plans",
                    changed_fields=[changes],
                    raw_diff={"type": "pricing", "changes": changes},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            elif pricing_result.get("current_pricing"):
                matrix.marketing_sources["pricing"] = pricing_result.get("current_pricing")
        
        # Детекция новых продуктов
        if features_url:
            previous_products = previous_marketing.get("products")
            products_result = await detector.detect_new_products(features_url, previous_products)
            if products_result.get("has_changes"):
                current_products = products_result.get("current_products", {})
                matrix.marketing_sources["products"] = current_products
                
                new_products = products_result.get("new_products", [])
                event = CompetitorChangeEvent(
                    company_id=company.id,
                    source_type=SourceType.BLOG,
                    change_summary=f"New products detected: {len(new_products)} new products",
                    changed_fields=[{"new_products": new_products}],
                    raw_diff={"type": "products", "new_products": new_products},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            elif products_result.get("current_products"):
                matrix.marketing_sources["products"] = products_result.get("current_products")
        
        # Детекция новых вакансий
        if careers_url:
            previous_jobs = previous_marketing.get("job_postings")
            jobs_result = await detector.detect_job_postings(careers_url, previous_jobs)
            if jobs_result.get("has_changes"):
                current_jobs = jobs_result.get("current_jobs", {})
                matrix.marketing_sources["job_postings"] = current_jobs
                
                new_jobs = jobs_result.get("new_jobs", [])
                event = CompetitorChangeEvent(
                    company_id=company.id,
                    source_type=SourceType.BLOG,
                    change_summary=f"New job postings detected: {len(new_jobs)} new positions",
                    changed_fields=[{"new_jobs": new_jobs}],
                    raw_diff={"type": "job_postings", "new_jobs": new_jobs},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            elif jobs_result.get("current_jobs"):
                matrix.marketing_sources["job_postings"] = jobs_result.get("current_jobs")
        
        matrix.marketing_sources["last_checked_at"] = datetime.now(timezone.utc).isoformat()
        matrix.last_updated = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"Detected marketing changes for {company.name}: {events_created} events created")
        return {"status": "completed", "changes": events_created}
        
    except Exception as e:
        logger.error(f"Error detecting marketing changes for company {company_id_str}: {e}")
        return {}
    finally:
        await detector.close()


async def collect_seo_signals_async(db, company_id_str: str, company: Company) -> Dict[str, Any]:
    """
    Async функция для сбора SEO сигналов.
    
    Args:
        db: Database session
        company_id_str: ID компании (строка)
        company: Объект Company
        
    Returns:
        Словарь с результатами сбора SEO сигналов
    """
    collector = SEOSignalCollector()
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Собрать SEO сигналы
        signals = await collector.collect_seo_signals(company.website)
        
        if not signals:
            logger.warning(f"Failed to collect SEO signals for {company.name}")
            return {}
        
        # Получить или создать матрицу мониторинга
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if not matrix:
            matrix = CompetitorMonitoringMatrix(
                company_id=company.id,
                monitoring_config={},
                social_media_sources={},
                website_sources={},
                news_sources={},
                marketing_sources={},
                seo_signals={},
                last_updated=datetime.now(timezone.utc)
            )
            db.add(matrix)
        
        # Сохранить сигналы
        if not matrix.seo_signals:
            matrix.seo_signals = {}
        
        # Сохранить текущие сигналы
        previous_signals = matrix.seo_signals.get("current_signals")
        matrix.seo_signals.update({
            "current_signals": signals,
            "last_collected_at": signals.get("collected_at"),
            "meta_tags_count": len(signals.get("meta_tags", {}).get("og_tags", {})),
            "structured_data_count": len(signals.get("structured_data", [])),
            "robots_txt_exists": signals.get("robots_txt", {}).get("exists", False),
            "sitemap_exists": signals.get("sitemap", {}).get("exists", False),
        })
        
        # Сохранить историю (последние 5 снимков)
        history = matrix.seo_signals.get("history", [])
        history.append(signals)
        if len(history) > 5:
            history = history[-5:]
        matrix.seo_signals["history"] = history
        
        matrix.last_updated = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"Collected SEO signals for {company.name}: {len(signals.get('structured_data', []))} structured data items")
        return {
            "status": "collected",
            "meta_tags": bool(signals.get("meta_tags", {}).get("title")),
            "structured_data_count": len(signals.get("structured_data", [])),
            "robots_txt_exists": signals.get("robots_txt", {}).get("exists", False),
            "sitemap_exists": signals.get("sitemap", {}).get("exists", False),
        }
        
    except Exception as e:
        logger.error(f"Error collecting SEO signals for company {company_id_str}: {e}")
        return {}
    finally:
        await collector.close()


async def build_monitoring_matrix_async(db, company_ids: List[str]) -> Dict[str, Any]:
    """
    Async функция для формирования матрицы мониторинга.
    
    Args:
        db: Database session
        company_ids: Список ID компаний
        
    Returns:
        Словарь с результатами формирования матрицы
    """
    try:
        matrices_updated = 0
        
        for company_id_str in company_ids:
            try:
                company_uuid = UUID(company_id_str)
                
                matrix_result = await db.execute(
                    select(CompetitorMonitoringMatrix).where(
                        CompetitorMonitoringMatrix.company_id == company_uuid
                    )
                )
                matrix = matrix_result.scalar_one_or_none()
                
                if matrix:
                    # Обновить monitoring_config с итоговой информацией
                    matrix.monitoring_config.update({
                        "setup_completed_at": datetime.now(timezone.utc).isoformat(),
                        "social_media_count": len([k for k, v in (matrix.social_media_sources or {}).items() if v]),
                        "website_captured": bool(matrix.website_sources),
                        "news_scraped": bool(matrix.news_sources),
                        "marketing_monitored": bool(matrix.marketing_sources),
                        "seo_collected": bool(matrix.seo_signals)
                    })
                    matrix.last_updated = datetime.now(timezone.utc)
                    matrices_updated += 1
                
            except Exception as e:
                logger.error(f"Error building matrix for company {company_id_str}: {e}")
                continue
        
        await db.commit()
        
        logger.info(f"Built monitoring matrices for {matrices_updated} companies")
        return {"status": "completed", "matrices_updated": matrices_updated}
        
    except Exception as e:
        logger.error(f"Error building monitoring matrices: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task
def compare_website_structures(company_id: str):
    """
    Celery задача для сравнения структуры сайта компании.
    
    Сравнивает текущий снимок с предыдущим и создает события изменений.
    
    Args:
        company_id: ID компании (строка)
    """
    return run_async_task(_compare_website_structures_async(company_id))


async def _compare_website_structures_async(company_id: str) -> Dict[str, Any]:
    """
    Async функция для сравнения структуры сайта.
    
    Args:
        company_id: ID компании (строка)
        
    Returns:
        Словарь с результатами сравнения
    """
    monitor = WebsiteStructureMonitor()
    try:
        company_uuid = UUID(company_id)
        
        async with CelerySessionLocal() as db:
            # Получить компанию
            company_result = await db.execute(
                select(Company).where(Company.id == company_uuid)
            )
            company = company_result.scalar_one_or_none()
            
            if not company or not company.website:
                logger.warning(f"Company {company_id} not found or has no website")
                return {"status": "error", "error": "Company not found or no website"}
            
            # Получить матрицу мониторинга
            matrix_result = await db.execute(
                select(CompetitorMonitoringMatrix).where(
                    CompetitorMonitoringMatrix.company_id == company_uuid
                )
            )
            matrix = matrix_result.scalar_one_or_none()
            
            if not matrix or not matrix.website_sources:
                logger.warning(f"No monitoring matrix or snapshots for company {company_id}")
                return {"status": "error", "error": "No snapshots found"}
            
            snapshots = matrix.website_sources.get("snapshots", [])
            if len(snapshots) < 2:
                logger.info(f"Not enough snapshots for comparison (need at least 2, have {len(snapshots)})")
                return {"status": "skipped", "reason": "Not enough snapshots"}
            
            # Сравнить последние два снимка
            previous_snapshot = snapshots[-2]
            current_snapshot = snapshots[-1]
            
            # Захватить свежий снимок для сравнения
            fresh_snapshot = await monitor.capture_website_snapshot(company.website)
            if not fresh_snapshot:
                logger.warning(f"Failed to capture fresh snapshot for {company.name}")
                return {"status": "error", "error": "Failed to capture snapshot"}
            
            # Сравнить с предыдущим
            changes = await monitor.detect_structure_changes(previous_snapshot, fresh_snapshot)
            
            if not changes.get("has_changes"):
                logger.info(f"No changes detected for {company.name}")
                return {"status": "no_changes", "company_id": company_id}
            
            # Создать события изменений
            from app.models import (
                CompetitorChangeEvent,
                SourceType,
                ChangeProcessingStatus,
                ChangeNotificationStatus,
            )
            
            events_created = 0
            
            # Событие для изменений навигации
            if changes.get("navigation_changes", {}).get("has_changes"):
                nav_changes = changes["navigation_changes"]
                event = CompetitorChangeEvent(
                    company_id=company_uuid,
                    source_type=SourceType.BLOG,  # Используем BLOG как базовый тип для структуры сайта
                    change_summary=f"Navigation changes detected: {len(nav_changes.get('added', []))} added, {len(nav_changes.get('removed', []))} removed",
                    changed_fields=[nav_changes],  # changed_fields - это List[Dict]
                    raw_diff={"type": "navigation", "changes": nav_changes},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            
            # Событие для изменений ключевых страниц
            if changes.get("key_pages_changes", {}).get("has_changes"):
                pages_changes = changes["key_pages_changes"]
                event = CompetitorChangeEvent(
                    company_id=company_uuid,
                    source_type=SourceType.BLOG,
                    change_summary=f"Key pages changes: {len(pages_changes.get('new_pages', []))} new, {len(pages_changes.get('removed_pages', []))} removed",
                    changed_fields=[pages_changes],
                    raw_diff={"type": "key_pages", "changes": pages_changes},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            
            # Событие для изменений метаданных
            if changes.get("metadata_changes", {}).get("has_changes"):
                meta_changes = changes["metadata_changes"]
                event = CompetitorChangeEvent(
                    company_id=company_uuid,
                    source_type=SourceType.BLOG,
                    change_summary="Website metadata changes detected",
                    changed_fields=[meta_changes],
                    raw_diff={"type": "metadata", "changes": meta_changes},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            
            # Обновить текущий снимок в матрице
            snapshots = matrix.website_sources.get("snapshots", [])
            snapshots.append(fresh_snapshot)
            if len(snapshots) > 10:
                snapshots = snapshots[-10:]
            
            matrix.website_sources.update({
                "snapshots": snapshots,
                "current_snapshot": fresh_snapshot,
                "last_snapshot_at": fresh_snapshot.get("captured_at"),
            })
            matrix.last_updated = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"Compared website structures for {company.name}: {events_created} events created")
            return {
                "status": "completed",
                "company_id": company_id,
                "events_created": events_created,
                "has_changes": True,
            }
            
    except Exception as e:
        logger.error(f"Error comparing website structures for company {company_id}: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        await monitor.close()


@celery_app.task
def compare_seo_signals(company_id: str):
    """
    Celery задача для сравнения SEO сигналов компании.
    
    Сравнивает текущие сигналы с предыдущими и создает события изменений.
    
    Args:
        company_id: ID компании (строка)
    """
    return run_async_task(_compare_seo_signals_async(company_id))


async def _compare_seo_signals_async(company_id: str) -> Dict[str, Any]:
    """
    Async функция для сравнения SEO сигналов.
    
    Args:
        company_id: ID компании (строка)
        
    Returns:
        Словарь с результатами сравнения
    """
    collector = SEOSignalCollector()
    try:
        company_uuid = UUID(company_id)
        
        async with CelerySessionLocal() as db:
            # Получить компанию
            company_result = await db.execute(
                select(Company).where(Company.id == company_uuid)
            )
            company = company_result.scalar_one_or_none()
            
            if not company or not company.website:
                logger.warning(f"Company {company_id} not found or has no website")
                return {"status": "error", "error": "Company not found or no website"}
            
            # Получить матрицу мониторинга
            matrix_result = await db.execute(
                select(CompetitorMonitoringMatrix).where(
                    CompetitorMonitoringMatrix.company_id == company_uuid
                )
            )
            matrix = matrix_result.scalar_one_or_none()
            
            if not matrix or not matrix.seo_signals:
                logger.warning(f"No SEO signals found for company {company_id}")
                return {"status": "error", "error": "No SEO signals found"}
            
            # Собрать свежие сигналы
            fresh_signals = await collector.collect_seo_signals(company.website)
            if not fresh_signals:
                logger.warning(f"Failed to collect fresh SEO signals for {company.name}")
                return {"status": "error", "error": "Failed to collect signals"}
            
            # Получить предыдущие сигналы
            previous_signals = matrix.seo_signals.get("current_signals")
            if not previous_signals:
                logger.info(f"No previous SEO signals to compare for {company.name}")
                # Просто сохранить текущие
                matrix.seo_signals["current_signals"] = fresh_signals
                matrix.seo_signals["last_collected_at"] = fresh_signals.get("collected_at")
                matrix.last_updated = datetime.now(timezone.utc)
                await db.commit()
                return {"status": "skipped", "reason": "No previous signals"}
            
            # Сравнить сигналы
            changes = collector.compare_seo_signals(previous_signals, fresh_signals)
            
            if not changes.get("has_changes"):
                logger.info(f"No SEO changes detected for {company.name}")
                return {"status": "no_changes", "company_id": company_id}
            
            # Создать события изменений
            from app.models import (
                CompetitorChangeEvent,
                SourceType,
                ChangeProcessingStatus,
                ChangeNotificationStatus,
            )
            
            events_created = 0
            
            # Событие для изменений meta тегов
            if changes.get("meta_tags_changes", {}).get("has_changes"):
                meta_changes = changes["meta_tags_changes"]
                event = CompetitorChangeEvent(
                    company_id=company_uuid,
                    source_type=SourceType.BLOG,
                    change_summary="SEO meta tags changes detected",
                    changed_fields=[meta_changes],
                    raw_diff={"type": "meta_tags", "changes": meta_changes},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            
            # Событие для изменений structured data
            if changes.get("structured_data_changes", {}).get("has_changes"):
                struct_changes = changes["structured_data_changes"]
                event = CompetitorChangeEvent(
                    company_id=company_uuid,
                    source_type=SourceType.BLOG,
                    change_summary=f"Structured data changes: {struct_changes.get('current_count', 0)} items (was {struct_changes.get('previous_count', 0)})",
                    changed_fields=[struct_changes],
                    raw_diff={"type": "structured_data", "changes": struct_changes},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            
            # Событие для изменений sitemap
            if changes.get("sitemap_changes", {}).get("has_changes"):
                sitemap_changes = changes["sitemap_changes"]
                event = CompetitorChangeEvent(
                    company_id=company_uuid,
                    source_type=SourceType.BLOG,
                    change_summary=f"Sitemap changes detected: {len(sitemap_changes.get('added_urls', []))} URLs added, {len(sitemap_changes.get('removed_urls', []))} removed",
                    changed_fields=[sitemap_changes],
                    raw_diff={"type": "sitemap", "changes": sitemap_changes},
                    detected_at=datetime.now(timezone.utc),
                    processing_status=ChangeProcessingStatus.SUCCESS,
                    notification_status=ChangeNotificationStatus.PENDING,
                )
                db.add(event)
                events_created += 1
            
            # Обновить текущие сигналы
            history = matrix.seo_signals.get("history", [])
            history.append(fresh_signals)
            if len(history) > 5:
                history = history[-5:]
            
            matrix.seo_signals.update({
                "current_signals": fresh_signals,
                "last_collected_at": fresh_signals.get("collected_at"),
                "history": history,
            })
            matrix.last_updated = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"Compared SEO signals for {company.name}: {events_created} events created")
            return {
                "status": "completed",
                "company_id": company_id,
                "events_created": events_created,
                "has_changes": True,
            }
            
    except Exception as e:
        logger.error(f"Error comparing SEO signals for company {company_id}: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        await collector.close()


# ============================================================================
# Периодические задачи-оркестраторы для автоматического мониторинга
# ============================================================================

@celery_app.task
def periodic_compare_website_structures():
    """
    Периодическая задача для сравнения структуры сайтов всех компаний.
    
    Запускается через Celery Beat и обрабатывает все компании с активным мониторингом.
    """
    return run_async_task(_periodic_compare_website_structures_async())


async def _periodic_compare_website_structures_async() -> Dict[str, Any]:
    """
    Async функция для периодического сравнения структуры сайтов.
    
    Получает все компании с CompetitorMonitoringMatrix и запускает сравнение для каждой.
    """
    try:
        async with CelerySessionLocal() as db:
            # Получить все компании с матрицей мониторинга
            result = await db.execute(
                select(CompetitorMonitoringMatrix.company_id)
            )
            company_ids = [str(row[0]) for row in result.all()]
            
            if not company_ids:
                logger.info("No companies with monitoring matrix found")
                return {"status": "skipped", "reason": "No companies found", "count": 0}
            
            # Запустить задачу сравнения для каждой компании
            tasks_created = 0
            for company_id in company_ids:
                try:
                    compare_website_structures.delay(company_id)
                    tasks_created += 1
                except Exception as e:
                    logger.error(f"Error scheduling compare_website_structures for company {company_id}: {e}")
                    continue
            
            logger.info(f"Scheduled {tasks_created} website structure comparison tasks")
            return {
                "status": "completed",
                "companies_processed": tasks_created,
                "total_companies": len(company_ids),
            }
            
    except Exception as e:
        logger.error(f"Error in periodic_compare_website_structures: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task
def periodic_detect_marketing_changes():
    """
    Периодическая задача для детекции маркетинговых изменений всех компаний.
    
    Запускается через Celery Beat и обрабатывает все компании с активным мониторингом.
    """
    return run_async_task(_periodic_detect_marketing_changes_async())


async def _periodic_detect_marketing_changes_async() -> Dict[str, Any]:
    """
    Async функция для периодической детекции маркетинговых изменений.
    
    Получает все компании с CompetitorMonitoringMatrix и запускает детекцию для каждой.
    """
    try:
        async with CelerySessionLocal() as db:
            # Получить все компании с матрицей мониторинга
            result = await db.execute(
                select(CompetitorMonitoringMatrix.company_id)
            )
            company_ids = [str(row[0]) for row in result.all()]
            
            if not company_ids:
                logger.info("No companies with monitoring matrix found")
                return {"status": "skipped", "reason": "No companies found", "count": 0}
            
            # Запустить задачу детекции для каждой компании
            tasks_created = 0
            for company_id in company_ids:
                try:
                    # Использовать существующую async функцию
                    company_result = await db.execute(
                        select(Company).where(Company.id == UUID(company_id))
                    )
                    company = company_result.scalar_one_or_none()
                    
                    if company:
                        await detect_marketing_changes_async(db, company_id, company)
                        tasks_created += 1
                except Exception as e:
                    logger.error(f"Error detecting marketing changes for company {company_id}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Processed {tasks_created} companies for marketing changes detection")
            return {
                "status": "completed",
                "companies_processed": tasks_created,
                "total_companies": len(company_ids),
            }
            
    except Exception as e:
        logger.error(f"Error in periodic_detect_marketing_changes: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task
def periodic_compare_seo_signals():
    """
    Периодическая задача для сравнения SEO сигналов всех компаний.
    
    Запускается через Celery Beat и обрабатывает все компании с активным мониторингом.
    """
    return run_async_task(_periodic_compare_seo_signals_async())


async def _periodic_compare_seo_signals_async() -> Dict[str, Any]:
    """
    Async функция для периодического сравнения SEO сигналов.
    
    Получает все компании с CompetitorMonitoringMatrix и запускает сравнение для каждой.
    """
    try:
        async with CelerySessionLocal() as db:
            # Получить все компании с матрицей мониторинга
            result = await db.execute(
                select(CompetitorMonitoringMatrix.company_id)
            )
            company_ids = [str(row[0]) for row in result.all()]
            
            if not company_ids:
                logger.info("No companies with monitoring matrix found")
                return {"status": "skipped", "reason": "No companies found", "count": 0}
            
            # Запустить задачу сравнения для каждой компании
            tasks_created = 0
            for company_id in company_ids:
                try:
                    compare_seo_signals.delay(company_id)
                    tasks_created += 1
                except Exception as e:
                    logger.error(f"Error scheduling compare_seo_signals for company {company_id}: {e}")
                    continue
            
            logger.info(f"Scheduled {tasks_created} SEO signals comparison tasks")
            return {
                "status": "completed",
                "companies_processed": tasks_created,
                "total_companies": len(company_ids),
            }
            
    except Exception as e:
        logger.error(f"Error in periodic_compare_seo_signals: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task
def periodic_scrape_press_releases():
    """
    Периодическая задача для сбора пресс-релизов всех компаний.
    
    Запускается через Celery Beat и обрабатывает все компании с активным мониторингом.
    """
    return run_async_task(_periodic_scrape_press_releases_async())


async def _periodic_scrape_press_releases_async() -> Dict[str, Any]:
    """
    Async функция для периодического сбора пресс-релизов.
    
    Получает все компании с CompetitorMonitoringMatrix и запускает сбор для каждой.
    """
    try:
        async with CelerySessionLocal() as db:
            # Получить все компании с матрицей мониторинга
            result = await db.execute(
                select(CompetitorMonitoringMatrix.company_id)
            )
            company_ids = [str(row[0]) for row in result.all()]
            
            if not company_ids:
                logger.info("No companies with monitoring matrix found")
                return {"status": "skipped", "reason": "No companies found", "count": 0}
            
            # Запустить задачу сбора для каждой компании
            tasks_created = 0
            for company_id in company_ids:
                try:
                    # Использовать существующую async функцию
                    company_result = await db.execute(
                        select(Company).where(Company.id == UUID(company_id))
                    )
                    company = company_result.scalar_one_or_none()
                    
                    if company:
                        await scrape_press_releases_async(db, company_id, company)
                        tasks_created += 1
                except Exception as e:
                    logger.error(f"Error scraping press releases for company {company_id}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Processed {tasks_created} companies for press releases scraping")
            return {
                "status": "completed",
                "companies_processed": tasks_created,
                "total_companies": len(company_ids),
            }
            
    except Exception as e:
        logger.error(f"Error in periodic_scrape_press_releases: {e}")
        return {"status": "error", "error": str(e)}

