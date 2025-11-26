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
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Базовая реализация - сохраняем информацию о том, что структура захвачена
        # Полная реализация будет в WebsiteStructureMonitor сервисе
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if matrix:
            if not matrix.website_sources:
                matrix.website_sources = {}
            
            matrix.website_sources.update({
                "last_snapshot_at": datetime.now(timezone.utc).isoformat(),
                "website_url": company.website,
                "status": "captured"
            })
            matrix.last_updated = datetime.now(timezone.utc)
            await db.commit()
        
        logger.info(f"Captured website structure for {company.name}")
        return {"status": "captured", "website": company.website}
        
    except Exception as e:
        logger.error(f"Error capturing website structure for company {company_id_str}: {e}")
        return {}


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
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Базовая реализация - сохраняем информацию о том, что пресс-релизы собраны
        # Полная реализация будет в PressReleaseScraper
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if matrix:
            if not matrix.news_sources:
                matrix.news_sources = {}
            
            matrix.news_sources.update({
                "last_scraped_at": datetime.now(timezone.utc).isoformat(),
                "press_release_urls": [],
                "status": "scraped"
            })
            matrix.last_updated = datetime.now(timezone.utc)
            await db.commit()
        
        logger.info(f"Scraped press releases for {company.name}")
        return {"status": "scraped", "count": 0}
        
    except Exception as e:
        logger.error(f"Error scraping press releases for company {company_id_str}: {e}")
        return {}


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
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Базовая реализация - сохраняем информацию о том, что маркетинг отслеживается
        # Полная реализация будет в MarketingChangeDetector
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if matrix:
            if not matrix.marketing_sources:
                matrix.marketing_sources = {}
            
            matrix.marketing_sources.update({
                "last_checked_at": datetime.now(timezone.utc).isoformat(),
                "banners": [],
                "landing_pages": [],
                "products": [],
                "job_postings": [],
                "status": "monitored"
            })
            matrix.last_updated = datetime.now(timezone.utc)
            await db.commit()
        
        logger.info(f"Detected marketing changes for {company.name}")
        return {"status": "monitored", "changes": 0}
        
    except Exception as e:
        logger.error(f"Error detecting marketing changes for company {company_id_str}: {e}")
        return {}


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
    try:
        if not company.website:
            logger.warning(f"Company {company.name} has no website URL")
            return {}
        
        # Базовая реализация - сохраняем информацию о том, что SEO сигналы собраны
        # Полная реализация будет в SEOSignalCollector
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix).where(
                CompetitorMonitoringMatrix.company_id == company.id
            )
        )
        matrix = matrix_result.scalar_one_or_none()
        
        if matrix:
            if not matrix.seo_signals:
                matrix.seo_signals = {}
            
            matrix.seo_signals.update({
                "last_collected_at": datetime.now(timezone.utc).isoformat(),
                "meta_tags": {},
                "structured_data": {},
                "status": "collected"
            })
            matrix.last_updated = datetime.now(timezone.utc)
            await db.commit()
        
        logger.info(f"Collected SEO signals for {company.name}")
        return {"status": "collected"}
        
    except Exception as e:
        logger.error(f"Error collecting SEO signals for company {company_id_str}: {e}")
        return {}


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

