"""
Report generation tasks
"""

from celery import current_task
from loguru import logger
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from urllib.parse import urlparse

from app.celery_app import celery_app
from app.core.celery_async import run_async_task
from app.core.database import AsyncSessionLocal
from app.domains.reports.repositories import ReportRepository
from app.domains.news.scrapers import CompanyContext, NewsScraperRegistry
from app.domains.news.repositories import NewsRepository
from app.models import Company, Report, ReportStatus
from app.models.news import NewsItem, NewsCategory, SourceType
from app.services.company_info_extractor import extract_company_info
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload


@celery_app.task(bind=True)
def generate_company_report(self, report_id: str, query: str, user_id: str):
    """
    Генерирует отчёт о компании асинхронно.
    
    Args:
        report_id: UUID отчёта
        query: Название компании или URL
        user_id: UUID пользователя
        
    Шаги:
    1. Разрешить query (URL или название компании)
    2. Найти/создать компанию через существующую логику scan_company
    3. Собрать данные:
       - Новости компании
       - Категории новостей с количеством
       - Источники с количеством новостей
       - Pricing информация из description
    4. Сохранить отчёт в БД
    5. Обновить статус: processing -> ready / error
    """
    logger.info(f"Starting report generation for report_id={report_id}, query={query}")
    
    try:
        result = run_async_task(_generate_company_report_async(report_id, query, user_id))
        logger.info(f"Report generation completed for report_id={report_id}")
        return result
    except Exception as e:
        logger.error(f"Report generation failed for report_id={report_id}: {e}")
        # Обновить статус на error
        run_async_task(_update_report_status_async(report_id, ReportStatus.ERROR, str(e)))
        raise self.retry(exc=e, countdown=60, max_retries=2)


async def _generate_company_report_async(report_id: str, query: str, user_id: str) -> Dict[str, Any]:
    """Async implementation of report generation."""
    async with AsyncSessionLocal() as db:
        report_repo = ReportRepository(db)
        
        # Получить отчёт
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Проверить, что отчёт принадлежит пользователю
        if str(report.user_id) != user_id:
            raise ValueError(f"Report {report_id} does not belong to user {user_id}")
        
        # Определить, является ли query URL или названием компании
        is_url = False
        website_url = None
        company_name = query
        
        try:
            parsed = urlparse(query)
            if parsed.scheme and parsed.netloc:
                is_url = True
                website_url = query
                company_name = parsed.netloc.replace('www.', '').split('.')[0].title()
        except Exception:
            pass
        
        company = None
        company_id = None
        
        if is_url:
            # Если это URL, сканируем компанию
            logger.info(f"Scanning company from URL: {website_url}")
            
            try:
                # Извлечь информацию о компании
                company_info = await extract_company_info(website_url)
                company_name = company_info.get("name") or company_name
                
                # Нормализовать URL для поиска существующей компании
                normalized_url = _normalize_url(website_url)
                
                # Поиск существующей компании - только пользовательские или глобальные
                from uuid import UUID as UUIDType
                user_uuid = UUIDType(user_id)
                user_filter = or_(
                    Company.user_id == user_uuid,
                    Company.user_id.is_(None)  # Глобальные компании
                )
                result = await db.execute(
                    select(Company).where(
                        or_(
                            func.lower(func.replace(Company.website, 'www.', '')) == normalized_url.lower(),
                            Company.name.ilike(f"%{company_name}%")
                        ),
                        user_filter
                    )
                )
                existing_company = result.scalar_one_or_none()
                
                if existing_company:
                    company = existing_company
                    company_id = str(company.id)
                    logger.info(f"Found existing company: {company.name}")
                else:
                    # Создать новую компанию - привязать к пользователю для изоляции данных
                    from uuid import UUID as UUIDType
                    user_uuid = UUIDType(user_id)
                    company = Company(
                        name=company_name,
                        website=website_url,
                        description=company_info.get("description"),
                        logo_url=company_info.get("logo_url"),
                        category=company_info.get("category"),
                        user_id=user_uuid  # Привязка к пользователю для изоляции данных
                    )
                    db.add(company)
                    await db.flush()
                    await db.refresh(company)
                    company_id = str(company.id)
                    logger.info(f"Created new company: {company.name} for user {user_id}")
                
                # Проверить, есть ли уже новости в БД (для быстрого отчёта достаточно 5)
                news_repo = NewsRepository(db)
                existing_news_count = await db.execute(
                    select(func.count(NewsItem.id))
                    .where(NewsItem.company_id == company.id)
                )
                existing_count = existing_news_count.scalar() or 0
                
                # Если новостей уже достаточно (>= 5), пропускаем скрапинг для ускорения
                # Если новостей меньше 5, делаем быстрый скрапинг только 5 статей
                if existing_count < 5:
                    logger.info(f"Company {company.id} has only {existing_count} news items, scraping 5 more for quick report")
                    
                    # Сканировать новости компании в быстром режиме
                    context = CompanyContext(
                        id=company.id,
                        name=company.name,
                        website=company.website,
                        news_page_url=None,
                    )
                    registry = NewsScraperRegistry()
                    provider = registry.get_provider(context)
                    
                    try:
                        # Быстрый режим: только 5 статей, минимальные задержки
                        scraped_items = await provider.scrape_company(
                            context,
                            max_articles=5,  # Только 5 статей для быстрого отчёта
                            source_overrides=None,
                        )
                        
                        # Сохранить новости
                        saved_count = 0
                        
                        for item in scraped_items:
                            # Проверить, существует ли новость
                            existing = await news_repo.fetch_by_url(item.source_url)
                            if existing:
                                continue
                            
                            # Создать новость
                            try:
                                news_item = NewsItem(
                                    title=item.title,
                                    content=item.content,
                                    summary=item.summary,
                                    source_url=item.source_url,
                                    source_type=item.source_type,
                                    category=item.category,
                                    company_id=company.id,
                                    published_at=item.published_at or datetime.now(timezone.utc),
                                )
                                db.add(news_item)
                                saved_count += 1
                            except Exception as e:
                                logger.warning(f"Failed to save news item {item.source_url}: {e}")
                                continue
                        
                        await db.commit()
                        logger.info(f"Saved {saved_count} news items for company {company.id}")
                    finally:
                        if provider:
                            await provider.close()
                else:
                    logger.info(f"Company {company.id} already has {existing_count} news items, skipping scraping for quick report")
            except Exception as e:
                logger.error(f"Failed to scan company from URL: {e}")
                raise
        
        else:
            # Если это название компании, ищем в БД
            logger.info(f"Searching for company by name: {query}")
            
            result = await db.execute(
                select(Company).where(Company.name.ilike(f"%{query}%"))
            )
            company = result.scalar_one_or_none()
            
            if company:
                company_id = str(company.id)
                logger.info(f"Found company: {company.name}")
            else:
                # Компания не найдена, но продолжаем создание отчёта
                logger.warning(f"Company not found for query: {query}")
        
        # Собрать данные для отчёта
        company_data = None
        categories = []
        sources = []
        news_items = []
        pricing_info = None
        competitors = []
        
        if company_id and company:
            # Полная информация о компании
            company_data = {
                "id": str(company.id),
                "name": company.name,
                "website": company.website,
                "description": company.description,
                "logo_url": company.logo_url,
                "category": company.category,
                "twitter_handle": company.twitter_handle,
                "github_org": company.github_org,
                "created_at": company.created_at.isoformat() if company.created_at else None,
            }
            
            # Загрузить новости компании (только последние 5 для быстрого отчёта)
            result = await db.execute(
                select(NewsItem)
                .where(NewsItem.company_id == company.id)
                .order_by(NewsItem.published_at.desc())
                .limit(5)  # Только 5 последних новостей для быстрого отчёта
                .options(selectinload(NewsItem.company))
            )
            news_items_db = result.scalars().all()
            
            # Подсчитать категории
            category_counts: Dict[str, int] = {}
            for news in news_items_db:
                if news.category:
                    cat_key = news.category.value
                    category_counts[cat_key] = category_counts.get(cat_key, 0) + 1
            
            categories = [
                {
                    "category": cat,
                    "technicalCategory": cat,
                    "count": count
                }
                for cat, count in category_counts.items()
            ]
            
            # Подсчитать источники
            source_counts: Dict[str, Dict[str, Any]] = {}
            for news in news_items_db:
                source_url = news.source_url
                source_type = news.source_type.value if news.source_type else "blog"
                
                # Извлечь базовый URL источника
                try:
                    parsed = urlparse(source_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                except Exception:
                    base_url = source_url
                
                if base_url not in source_counts:
                    source_counts[base_url] = {
                        "url": base_url,
                        "type": source_type,
                        "count": 0
                    }
                source_counts[base_url]["count"] += 1
            
            sources = list(source_counts.values())
            
            # Преобразовать новости в формат для API (только 5 последних)
            news_items = [
                {
                    "id": str(news.id),
                    "title": news.title,
                    "summary": news.summary,
                    "source_url": news.source_url,
                    "category": news.category.value if news.category else None,
                    "published_at": news.published_at.isoformat() if news.published_at else None,
                    "created_at": news.created_at.isoformat() if news.created_at else None,
                }
                for news in news_items_db[:5]  # Только 5 последних новостей для быстрого отчёта
            ]
            
            # Извлечь pricing информацию из description компании
            if company and company.description:
                description_lower = company.description.lower()
                if any(keyword in description_lower for keyword in ['pricing', 'price', '$', 'cost', 'plan']):
                    pricing_info = {
                        "description": company.description,
                        "news": [
                            news for news in news_items
                            if news.get("category") == "pricing_change" or
                            any(keyword in (news.get("title", "") + " " + (news.get("summary", ""))).lower()
                                for keyword in ['price', 'pricing', '$', 'cost', 'plan'])
                        ][:5]  # Ограничение pricing новостей до 5
                    }
            
            # Получить конкурентов (только 5 для быстрого отчёта)
            if company_id:
                try:
                    from app.services.competitor_service import CompetitorAnalysisService
                    from uuid import UUID as UUIDType
                    competitor_service = CompetitorAnalysisService(db)
                    company_uuid = UUIDType(company_id)
                    date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
                    date_to = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    suggestions_list = await competitor_service.suggest_competitors(
                        company_uuid,
                        limit=5,  # Только 5 конкурентов для быстрого отчёта
                        date_from=date_from,
                        date_to=date_to
                    )
                    if suggestions_list:
                        competitors = [
                            {
                                "company": suggestion["company"],
                                "similarity_score": suggestion["similarity_score"],
                                "common_categories": suggestion["common_categories"],
                                "reason": suggestion["reason"]
                            }
                            for suggestion in suggestions_list[:5]
                        ]
                        logger.info(f"Found {len(competitors)} competitors for company {company_id}")
                except Exception as e:
                    logger.warning(f"Failed to get competitors for company {company_id}: {e}")
                    # Не прерываем генерацию отчёта из-за ошибки конкурентов
        
        # Собрать все данные отчёта в словарь
        report_data = {
            "company": company_data,
            "categories": categories if categories else None,
            "news": news_items if news_items else None,
            "sources": sources if sources else None,
            "pricing": pricing_info,
            "competitors": competitors if competitors else None,
        }
        
        # Обновить отчёт с данными через update_report_data
        company_uuid = None
        if company_id:
            from uuid import UUID as UUIDType
            try:
                company_uuid = UUIDType(company_id)
            except ValueError:
                logger.warning(f"Invalid company_id format: {company_id}")
        
        await report_repo.update_report_data(
            report_id,
            report_data,
            company_id=company_uuid,
            status=ReportStatus.READY,
            completed_at=datetime.now(timezone.utc)
        )
        
        await db.commit()
        
        logger.info(f"Report {report_id} generation completed successfully with data saved to report_data")
        
        return {
            "status": "ready",
            "report_id": report_id,
            "company_id": company_id
        }


async def _update_report_status_async(
    report_id: str,
    status: ReportStatus,
    error_message: str | None = None
) -> None:
    """Update report status asynchronously."""
    async with AsyncSessionLocal() as db:
        report_repo = ReportRepository(db)
        await report_repo.update_status(
            report_id,
            status,
            error_message=error_message,
            completed_at=datetime.now(timezone.utc) if status == ReportStatus.ERROR else None
        )
        await db.commit()


def _normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower().replace('www.', '')
    path = parsed.path.rstrip('/')
    normalized = f"{parsed.scheme}://{netloc}{path}"
    return normalized

