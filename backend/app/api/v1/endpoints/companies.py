"""
Companies endpoints
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from loguru import logger
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from uuid import UUID as UUIDType

from app.core.database import get_db
from app.models.company import Company
from app.models.competitor import CompetitorMonitoringMatrix, CompetitorChangeEvent
from app.models.news import (
    NewsItem,
    NewsCategory,
    SourceType,
    NewsTopic,
    SentimentLabel,
)
from app.services.company_info_extractor import extract_company_info
from app.api.dependencies import get_current_user, get_current_user_optional
from app.models import User
from app.schemas.monitoring import MonitoringChangesResponseSchema
from app.domains.news.scrapers import CompanyContext, NewsScraperRegistry
from app.tasks.scraping import scan_company_sources_initial
from app.core.access_control import invalidate_user_cache

router = APIRouter()


def normalize_url(url: str) -> str:
    """
    Normalize URL for comparison (remove www, trailing slash, etc.)
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL string
    """
    parsed = urlparse(url)
    netloc = (parsed.netloc or '').lower().replace('www.', '')
    path = parsed.path.rstrip('/') if parsed.path else ''
    scheme = parsed.scheme or 'https'
    normalized = f"{scheme}://{netloc}{path}"
    return normalized


async def _generate_quick_analysis_data(
    db: AsyncSession,
    query: str,
    include_competitors: bool = True,
    user_id: Optional[UUIDType] = None
) -> Dict[str, Any]:
    """
    Генерирует данные быстрого анализа компании из существующих данных БД.
    Использует алгоритм из CompanyAnalysisFlow (suggest_competitors).
    
    Args:
        db: Database session
        query: Company name or URL
        include_competitors: Whether to include competitors analysis
        user_id: User ID for data isolation (only show user's companies or global)
        
    Returns:
        Dictionary with report data: company, categories, news, sources, pricing, competitors
        
    Raises:
        ValueError: If company not found
    """
    # Определить, является ли query URL или названием
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
    
    # Build user filter for data isolation
    if user_id:
        # Authenticated user: show their companies and global companies
        user_filter = or_(
            Company.user_id == user_id,
            Company.user_id.is_(None)  # Global companies
        )
    else:
        # Anonymous user: only show global companies
        user_filter = Company.user_id.is_(None)
    
    # Найти компанию в БД
    company = None
    if is_url:
        # Нормализовать URL
        normalized_url = normalize_url(website_url)
        result = await db.execute(
            select(Company).where(
                or_(
                    func.lower(func.replace(Company.website, 'www.', '')) == normalized_url.lower(),
                    Company.name.ilike(f"%{company_name}%")
                ),
                user_filter
            ).limit(1)  # Ограничиваем до 1 результата чтобы избежать "Multiple rows"
        )
        company = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(Company).where(
                Company.name.ilike(f"%{query}%"),
                user_filter
            ).limit(1)  # Ограничиваем до 1 результата
        )
        company = result.scalar_one_or_none()
    
    if not company:
        raise ValueError(f"Company not found for query: {query}. Please add company first or use full URL.")
    
    # ========== СОБРАТЬ ВСЕ ДАННЫЕ ==========
    
    # 1. Полная информация о компании (ВСЕ поля)
    company_data = {
        "id": str(company.id),
        "name": company.name,
        "website": company.website,
        "description": company.description,
        "logo_url": company.logo_url,
        "category": company.category,
        "twitter_handle": company.twitter_handle,
        "github_org": company.github_org,
        "facebook_url": company.facebook_url,
        "instagram_url": company.instagram_url,
        "linkedin_url": company.linkedin_url,
        "youtube_url": company.youtube_url,
        "tiktok_url": company.tiktok_url,
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }
    
    # 2. Новости компании (последние 5)
    news_result = await db.execute(
        select(NewsItem)
        .where(NewsItem.company_id == company.id)
        .order_by(NewsItem.published_at.desc())
        .limit(5)
    )
    news_items_db = news_result.scalars().all()
    
    # 3. Категории новостей с количеством
    category_counts = {}
    for news in news_items_db:
        if news.category:
            # Безопасное извлечение значения категории (может быть enum или строка)
            cat_key = news.category.value if hasattr(news.category, 'value') else str(news.category)
            category_counts[cat_key] = category_counts.get(cat_key, 0) + 1
    
    categories = [
        {
            "category": cat,
            "technicalCategory": cat,
            "count": count
        }
        for cat, count in category_counts.items()
    ] if category_counts else None
    
    # 4. Источники новостей с количеством
    source_counts = {}
    for news in news_items_db:
        source_url = news.source_url
        # Безопасное извлечение значения source_type (может быть enum или строка)
        if news.source_type:
            source_type = news.source_type.value if hasattr(news.source_type, 'value') else str(news.source_type)
        else:
            source_type = "blog"
        
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
    
    sources = list(source_counts.values()) if source_counts else None
    
    # 5. Новости в формате для API (с summary)
    news_items = []
    for news in (news_items_db or []):
        # Безопасное извлечение значения категории
        category_value = None
        if news.category:
            category_value = news.category.value if hasattr(news.category, 'value') else str(news.category)
        
        news_items.append({
            "id": str(news.id),
            "title": news.title,
            "summary": news.summary,
            "source_url": news.source_url,
            "category": category_value,
            "published_at": news.published_at.isoformat() if news.published_at else None,
            "created_at": news.created_at.isoformat() if news.created_at else None,
        })
    
    news_items = news_items if news_items else None
    
    # 6. Pricing информация из description + новости о pricing
    pricing_info = None
    if company.description:
        description_lower = company.description.lower()
        if any(keyword in description_lower for keyword in ['pricing', 'price', '$', 'cost', 'plan']):
            pricing_news = [
                news for news in (news_items or [])
                if news.get("category") == "pricing_change" or
                any(keyword in (news.get("title", "") + " " + (news.get("summary", "") or "")).lower()
                    for keyword in ['price', 'pricing', '$', 'cost', 'plan'])
            ][:5]
            
            pricing_info = {
                "description": company.description,
                "news": pricing_news if pricing_news else None
            }
    
    # 7. Конкуренты (если запрошено) - используем алгоритм из CompanyAnalysisFlow
    competitors = None
    if include_competitors:
        try:
            from app.services.competitor_service import CompetitorAnalysisService
            competitor_service = CompetitorAnalysisService(db)
            company_uuid = UUIDType(str(company.id))
            date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
            date_to = datetime.now(timezone.utc).replace(tzinfo=None)
            
            suggestions_list = await competitor_service.suggest_competitors(
                company_uuid,
                limit=5,
                date_from=date_from,
                date_to=date_to
            )
            
            if suggestions_list:
                competitors = [
                    {
                        "company": suggestion.get("company", {}),
                        "similarity_score": suggestion.get("similarity_score", 0.0),
                        "common_categories": suggestion.get("common_categories", []),
                        "reason": suggestion.get("reason", "Similar company")
                    }
                    for suggestion in suggestions_list[:5]
                    if suggestion and isinstance(suggestion, dict)
                ]
                if competitors:
                    logger.info(f"Found {len(competitors)} competitors for company {company.id}")
        except ImportError as e:
            logger.warning(f"Could not import CompetitorAnalysisService: {e}")
            competitors = None
        except Exception as e:
            logger.warning(f"Failed to get competitors for company {company.id}: {e}", exc_info=True)
            # Не прерываем возврат отчёта из-за ошибки конкурентов
            competitors = None
    
    # Формируем данные отчёта
    return {
        "company": company_data,
        "categories": categories,
        "news": news_items,
        "sources": sources,
        "pricing": pricing_info,
        "competitors": competitors,
        "company_id": str(company.id),  # Для сохранения в report.company_id
    }


@router.get("/")
async def get_companies(
    search: Optional[str] = Query(None, description="Search companies by name"),
    limit: int = Query(100, ge=1, le=200, description="Number of companies to return"),
    offset: int = Query(0, ge=0, description="Number of companies to skip"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of companies with optional search.
    
    For authenticated users: Returns only companies from subscribed_companies (data isolation).
    For anonymous users: Returns only global companies (user_id is None).
    """
    logger.info(f"Companies request: search={search}, limit={limit}, offset={offset}, user={current_user.id if current_user else 'anonymous'}")
    
    try:
        from sqlalchemy import or_
        from app.models.preferences import UserPreferences
        
        # For authenticated users, show ONLY their own companies (user_id == current_user.id)
        # This is for "My Competitors" - companies that belong to the user
        # subscribed_companies is separate - it's for news filtering only
        if current_user:
            # Show only companies that belong to this user (data isolation)
            query = select(Company).where(Company.user_id == current_user.id).order_by(Company.name)
            logger.info(f"Filtering companies by user_id={current_user.id} for user {current_user.id}")
        else:
            # Anonymous user: only show global companies
            query = select(Company).where(Company.user_id.is_(None)).order_by(Company.name)
        
        # Apply search filter
        if search:
            query = query.where(Company.name.ilike(f"%{search}%"))
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        companies = result.scalars().all()
        
        # Get total count with same filters
        if current_user:
            count_query = select(func.count(Company.id)).where(Company.user_id == current_user.id)
        else:
            count_query = select(func.count(Company.id)).where(Company.user_id.is_(None))
        
        if search:
            count_query = count_query.where(Company.name.ilike(f"%{search}%"))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Convert to response format
        items = [
            {
                "id": str(company.id),
                "name": company.name,
                "website": company.website,
                "description": company.description,
                "category": company.category,
                "logo_url": company.logo_url
            }
            for company in companies
        ]
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve companies")


@router.get("/{company_id}/monitoring/matrix")
async def get_monitoring_matrix(
    company_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring matrix for a specific company.
    
    Returns the complete monitoring matrix including:
    - monitoring_config: General monitoring configuration
    - social_media_sources: Discovered social media accounts
    - website_sources: Website structure and key pages
    - news_sources: News and press release sources
    - marketing_sources: Marketing change tracking sources
    - seo_signals: SEO signals collected
    - last_updated: Timestamp of last update
    
    Only accessible if company belongs to current user or is global (user_id is None).
    """
    logger.info(f"Get monitoring matrix: company_id={company_id}, user={current_user.id if current_user else 'anonymous'}")
    
    try:
        from app.core.access_control import check_company_access
        
        # Validate company_id format
        try:
            company_uuid = UUIDType(company_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Check company access (returns None if no access, raises 404 for security)
        company = await check_company_access(company_id, current_user, db)
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get monitoring matrix for this company
        matrix_result = await db.execute(
            select(CompetitorMonitoringMatrix)
            .where(CompetitorMonitoringMatrix.company_id == company_uuid)
        )
        matrix = matrix_result.scalar_one_or_none()
        
        # If no matrix exists, return empty structure
        if not matrix:
            return {
                "company_id": company_id,
                "monitoring_config": {},
                "social_media_sources": {},
                "website_sources": {},
                "news_sources": {},
                "marketing_sources": {},
                "seo_signals": {},
                "last_updated": None,
            }
        
        # Return matrix data
        return {
            "company_id": str(matrix.company_id),
            "monitoring_config": matrix.monitoring_config or {},
            "social_media_sources": matrix.social_media_sources or {},
            "website_sources": matrix.website_sources or {},
            "news_sources": matrix.news_sources or {},
            "marketing_sources": matrix.marketing_sources or {},
            "seo_signals": matrix.seo_signals or {},
            "last_updated": matrix.last_updated.isoformat() if matrix.last_updated else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get monitoring matrix: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve monitoring matrix: {str(e)}")


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific company by ID.
    Only accessible if company belongs to current user or is global (user_id is None).
    
    ВАЖНО: Проверка доступа выполняется в SQL запросе для безопасности (не раскрывает информацию).
    """
    logger.info(f"Get company: {company_id}, user={current_user.id if current_user else 'anonymous'}")
    
    try:
        from app.core.access_control import check_company_access
        
        # Проверка доступа в SQL запросе (безопасно - всегда возвращает 404 для недоступных)
        company = await check_company_access(company_id, current_user, db)
        
        if not company:
            # Всегда возвращаем 404 для недоступных ресурсов (безопасность)
            raise HTTPException(status_code=404, detail="Company not found")
        
        return {
            "id": str(company.id),
            "name": company.name,
            "website": company.website,
            "description": company.description,
            "category": company.category,
            "logo_url": company.logo_url,
            "twitter_handle": company.twitter_handle,
            "github_org": company.github_org,
            "facebook_url": company.facebook_url,
            "instagram_url": company.instagram_url,
            "linkedin_url": company.linkedin_url,
            "youtube_url": company.youtube_url,
            "tiktok_url": company.tiktok_url,
            "created_at": company.created_at.isoformat() if company.created_at else None,
            "updated_at": company.updated_at.isoformat() if company.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get company: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve company")


@router.post("/scan")
async def scan_company(
    request: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Scan a company website for news and return preview
    
    TODO: Add async version with Celery task for large sites (>50 articles)
    TODO: Add progress tracking for long-running scans
    TODO: Add caching for repeated scans of same URL
    """
    website_url = request.get("website_url")
    news_page_url = request.get("news_page_url")  # Optional manual override
    
    if not website_url:
        raise HTTPException(status_code=400, detail="website_url is required")
    
    # Validate URL format
    try:
        parsed = urlparse(website_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    registry = NewsScraperRegistry()
    provider = None
    try:
        # Extract company name from URL as fallback
        parsed = urlparse(website_url)
        company_name_fallback = parsed.netloc.replace('www.', '').split('.')[0].title()
        
        # Extract company info from homepage
        logger.info(f"Extracting company info from {website_url}")
        company_info = await extract_company_info(website_url)
        company_name = company_info.get("name") or company_name_fallback
        
        # Scrape news with optional manual news page URL
        logger.info(f"Scraping news for {company_name}, news_page_url: {news_page_url}")
        source_overrides = request.get("sources")
        
        # Оптимизация: для ручного сканирования используем меньше статей (по умолчанию 10)
        max_articles = request.get("max_articles", 10)
        if max_articles > 50:
            max_articles = 50  # Ограничение максимума
        logger.info(f"Scanning with max_articles={max_articles}")

        # Оптимизация: если указан news_page_url, используем его напрямую с минимальными задержками
        if news_page_url and not source_overrides:
            source_overrides = [{
                "urls": [news_page_url],
                "source_type": "blog",
                "retry": {"attempts": 0},  # Без ретраев для скорости
                "min_delay": 1.0,  # Уменьшенная задержка (вместо 5.0)
                "max_articles": max_articles,
            }]
            logger.info(f"Using fast mode with news_page_url directly, min_delay=1.0")

        context = CompanyContext(
            id=None,
            name=company_name,
            website=website_url,
            news_page_url=news_page_url,
        )
        provider = registry.get_provider(context)
        scraped_items = await provider.scrape_company(
            context,
            max_articles=max_articles,
            source_overrides=source_overrides,
        )
        news_items = [
            {
                "title": item.title,
                "summary": item.summary,
                "content": item.content,
                "source_url": item.source_url,
                "source_type": item.source_type,
                "category": item.category,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "company_name": company_name,
            }
            for item in scraped_items
        ]
        
        # Оптимизация: сортируем по дате (самые свежие первыми) и ограничиваем количество
        # Статьи без даты идут в конец
        def get_sort_key(item: Dict[str, Any]) -> datetime:
            """Получить дату для сортировки, статьи без даты идут в конец"""
            if item.get("published_at"):
                try:
                    return datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return datetime.min
            return datetime.min
        
        news_items.sort(key=get_sort_key, reverse=True)
        # Убеждаемся, что не превышаем лимит после сортировки
        news_items = news_items[:max_articles]
        
        # Analyze results
        categories = {}
        source_types = {}
        for item in news_items:
            cat = item.get('category', 'other')
            categories[cat] = categories.get(cat, 0) + 1
            
            src_type = item.get('source_type', 'blog')
            source_types[src_type] = source_types.get(src_type, 0) + 1
        
        return {
            "company_preview": {
                "name": company_name,
                "website": website_url,
                "description": company_info.get("description"),
                "logo_url": company_info.get("logo_url"),
                "category": company_info.get("category")
            },
            "news_preview": {
                "total_found": len(news_items),
                "categories": categories,
                "source_types": source_types,
                "sample_items": news_items[:10]  # First 10 for preview
            },
            "all_news_items": news_items  # All items for final creation
        }
    except Exception as e:
        logger.error(f"Failed to scan company: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scan company: {str(e)}")
    finally:
        if provider:
            await provider.close()


@router.post("/")
async def create_company(
    request: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new company or update existing one with news items
    
    TODO: Add validation for company data
    TODO: Add rate limiting for company creation
    TODO: Add notification when company is added/updated
    """
    company_data = request.get("company")
    news_items_data = request.get("news_items", [])
    
    if not company_data:
        raise HTTPException(status_code=400, detail="company data is required")
    
    website_url = company_data.get("website")
    if not website_url:
        raise HTTPException(status_code=400, detail="website is required")
    
    try:
        # Normalize URL for comparison
        normalized_url = normalize_url(website_url)
        
        # Check for existing company by URL or name - only user's companies or global
        # User can only update their own companies or create new ones
        user_filter = or_(
            Company.user_id == current_user.id,
            Company.user_id.is_(None)  # Global companies
        )
        
        result = await db.execute(
            select(Company).where(
                or_(
                    func.lower(func.replace(Company.website, 'www.', '')) == normalized_url.lower(),
                    Company.name.ilike(f"%{company_data.get('name', '')}%")
                ),
                user_filter
            )
        )
        existing_company = result.scalar_one_or_none()
        
        if existing_company:
            # Update existing company - дополняем информацию
            # Only allow updating own companies or global companies
            if existing_company.user_id is not None and existing_company.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Cannot update company belonging to another user")
            
            logger.info(f"Updating existing company: {existing_company.name}")
            
            # Дополняем информацию, если она отсутствует
            if not existing_company.description and company_data.get("description"):
                existing_company.description = company_data["description"]
            
            if not existing_company.logo_url and company_data.get("logo_url"):
                existing_company.logo_url = company_data["logo_url"]
            
            if not existing_company.category and company_data.get("category"):
                existing_company.category = company_data["category"]
            
            # Обновляем поля соцсетей, если они предоставлены
            if company_data.get("facebook_url") is not None:
                existing_company.facebook_url = company_data["facebook_url"]
            if company_data.get("instagram_url") is not None:
                existing_company.instagram_url = company_data["instagram_url"]
            if company_data.get("linkedin_url") is not None:
                existing_company.linkedin_url = company_data["linkedin_url"]
            if company_data.get("youtube_url") is not None:
                existing_company.youtube_url = company_data["youtube_url"]
            if company_data.get("tiktok_url") is not None:
                existing_company.tiktok_url = company_data["tiktok_url"]
            
            # Обновляем website если он изменился (нормализованный)
            if normalize_url(existing_company.website or '') != normalized_url:
                existing_company.website = website_url
            
            await db.flush()
            company = existing_company
            action = "updated"
            # Инвалидируем кеш при обновлении компании
            if company.user_id:
                invalidate_user_cache(company.user_id)
        else:
            # Create new company - assign to current user
            logger.info(f"Creating new company: {company_data.get('name')} for user {current_user.id}")
            
            company = Company(
                name=company_data.get("name"),
                website=website_url,
                description=company_data.get("description"),
                logo_url=company_data.get("logo_url"),
                category=company_data.get("category"),
                twitter_handle=company_data.get("twitter_handle"),
                github_org=company_data.get("github_org"),
                facebook_url=company_data.get("facebook_url"),
                instagram_url=company_data.get("instagram_url"),
                linkedin_url=company_data.get("linkedin_url"),
                youtube_url=company_data.get("youtube_url"),
                tiktok_url=company_data.get("tiktok_url"),
                user_id=current_user.id  # Assign to current user for data isolation
            )
            db.add(company)
            await db.flush()
            await db.commit()  # Commit to get company.id
            action = "created"
            # Инвалидируем кеш при создании новой компании
            invalidate_user_cache(current_user.id)
            
            # Запускаем первичное сканирование источников для новой компании
            try:
                scan_company_sources_initial.delay(str(company.id))
                logger.info(f"Scheduled initial source scan for new company {company.id}")
            except Exception as e:
                logger.warning(f"Failed to schedule initial source scan: {e}")
        
        # Save news items
        saved_count = 0
        skipped_count = 0
        
        for news_data in news_items_data:
            # Check if news already exists
            existing_news = await db.execute(
                select(NewsItem).where(NewsItem.source_url == news_data.get("source_url"))
            )
            if existing_news.scalar_one_or_none():
                skipped_count += 1
                continue
            
            # Create news item
            try:
                # Parse published_at if it's a string
                published_at = news_data.get("published_at")
                if isinstance(published_at, str):
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                elif not isinstance(published_at, datetime):
                    published_at = datetime.now()
                
                priority_score = news_data.get("priority_score", 0.5)
                try:
                    priority_score = float(priority_score)
                except (TypeError, ValueError):
                    logger.warning(f"Invalid priority_score '{priority_score}' for {news_data.get('source_url')}, defaulting to 0.5")
                    priority_score = 0.5

                topic_value = news_data.get("topic")
                topic = None
                if topic_value:
                    try:
                        topic = NewsTopic(topic_value)
                    except ValueError:
                        logger.warning(f"Unknown topic '{topic_value}' for {news_data.get('source_url')}")

                sentiment_value = news_data.get("sentiment")
                sentiment = None
                if sentiment_value:
                    try:
                        sentiment = SentimentLabel(sentiment_value)
                    except ValueError:
                        logger.warning(f"Unknown sentiment '{sentiment_value}' for {news_data.get('source_url')}")

                news_item = NewsItem(
                    title=news_data.get("title", "Untitled"),
                    content=news_data.get("content"),
                    summary=news_data.get("summary"),
                    source_url=news_data.get("source_url"),
                    source_type=SourceType(news_data.get("source_type", "blog")),
                    category=NewsCategory(news_data.get("category", "product_update")) if news_data.get("category") else None,
                    company_id=company.id,
                    published_at=published_at,
                    priority_score=priority_score,
                    topic=topic,
                    sentiment=sentiment,
                    raw_snapshot_url=news_data.get("raw_snapshot_url")
                )
                db.add(news_item)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to create news item: {e}")
                skipped_count += 1
                continue
        
        await db.commit()
        
        return {
            "status": "success",
            "action": action,
            "company": {
                "id": str(company.id),
                "name": company.name,
                "website": company.website,
                "description": company.description,
                "logo_url": company.logo_url,
                "category": company.category
            },
            "news_stats": {
                "saved": saved_count,
                "skipped": skipped_count,
                "total": len(news_items_data)
            }
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create/update company: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create/update company: {str(e)}")


@router.post("/quick-analysis")
async def quick_company_analysis(
    request: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Быстрый анализ компании без скрапинга.
    Использует только существующие данные из БД.
    
    ВРЕМЕННОЕ РЕШЕНИЕ: Только БД данные для демонстрации.
    В БУДУЩЕМ: Будет поддерживать внешние сервисы для новых компаний.
    
    Request: { 
        "query": "AccuRanker" или "https://www.accuranker.com",
        "include_competitors": true
    }
    
    Response: Полная структура Report со всеми данными:
    - company (name, website, description, logo_url, category, twitter_handle, github_org)
    - categories (категории новостей с количеством)
    - news (последние 5 новостей)
    - sources (источники новостей)
    - pricing (информация о ценах из description + новости)
    - competitors (конкуренты, если include_competitors=true)
    """
    query = request.get("query", "").strip()
    include_competitors = request.get("include_competitors", False)
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        # Использовать общую функцию для генерации данных
        report_data = await _generate_quick_analysis_data(db, query, include_competitors, user_id=current_user.id)
        company_id = report_data.pop("company_id")  # Извлечь company_id отдельно
        
        # Формируем ответ в формате Report (ВСЕ данные)
        return {
            "id": f"quick-analysis-{company_id}",
            "query": query,
            "status": "ready",
            "company_id": company_id,
            **report_data,  # company, categories, news, sources, pricing, competitors
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            # Метаданные для будущего расширения
            "_metadata": {
                "data_source": "database",
                "is_temporary_solution": True,
                "note": "В будущем будет добавлена поддержка внешних сервисов для новых компаний"
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to analyze company: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze company: {str(e)}")


@router.get("/monitoring/status")
async def get_monitoring_status(
    company_ids: str = Query(..., description="Comma-separated list of company UUIDs"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring status for multiple companies.
    
    Returns status information including:
    - Active status
    - Source counts (social media, website pages, news, marketing, SEO)
    - Last check timestamps for each source type
    """
    try:
        # Parse company IDs from comma-separated string
        company_id_list = [cid.strip() for cid in company_ids.split(',') if cid.strip()]
        
        if not company_id_list:
            return {"statuses": []}
        
        # Validate UUIDs
        valid_company_ids = []
        for cid in company_id_list:
            try:
                valid_company_ids.append(UUIDType(cid))
            except ValueError:
                logger.warning(f"Invalid company ID format: {cid}")
                continue
        
        if not valid_company_ids:
            return {"statuses": []}
        
        # Build access filter
        if current_user:
            # Authenticated user: only their companies
            company_filter = Company.user_id == current_user.id
        else:
            # Anonymous user: only global companies
            company_filter = Company.user_id.is_(None)
        
        # Get companies with access check
        companies_result = await db.execute(
            select(Company)
            .where(
                Company.id.in_(valid_company_ids),
                company_filter
            )
        )
        companies = {str(c.id): c for c in companies_result.scalars().all()}
        
        # Get monitoring matrices for these companies
        matrices_result = await db.execute(
            select(CompetitorMonitoringMatrix)
            .where(CompetitorMonitoringMatrix.company_id.in_(valid_company_ids))
        )
        matrices = {str(m.company_id): m for m in matrices_result.scalars().all()}
        
        # Build response
        statuses = []
        for company_id in valid_company_ids:
            company_id_str = str(company_id)
            company = companies.get(company_id_str)
            
            if not company:
                # Skip companies user doesn't have access to
                continue
            
            matrix = matrices.get(company_id_str)
            
            # Count sources
            social_media_count = 0
            if matrix and matrix.social_media_sources:
                social_media_count = len([
                    k for k, v in matrix.social_media_sources.items()
                    if v and isinstance(v, dict) and v.get("url")
                ])
            
            website_pages_count = 0
            if matrix and matrix.website_sources:
                key_pages = matrix.website_sources.get("key_pages", [])
                if isinstance(key_pages, list):
                    website_pages_count = len(key_pages)
            
            news_sources_count = 0
            if matrix and matrix.news_sources:
                press_releases = matrix.news_sources.get("press_release_urls", [])
                blog_urls = matrix.news_sources.get("blog_urls", [])
                if isinstance(press_releases, list):
                    news_sources_count += len(press_releases)
                if isinstance(blog_urls, list):
                    news_sources_count += len(blog_urls)
            
            marketing_sources_count = 0
            if matrix and matrix.marketing_sources:
                banners = matrix.marketing_sources.get("banners", [])
                landing_pages = matrix.marketing_sources.get("landing_pages", [])
                products = matrix.marketing_sources.get("products", [])
                job_postings = matrix.marketing_sources.get("job_postings", [])
                if isinstance(banners, list):
                    marketing_sources_count += len(banners)
                if isinstance(landing_pages, list):
                    marketing_sources_count += len(landing_pages)
                if isinstance(products, list):
                    marketing_sources_count += len(products)
                if isinstance(job_postings, list):
                    marketing_sources_count += len(job_postings)
            
            seo_signals_count = 0
            if matrix and matrix.seo_signals:
                # Count if any SEO data exists
                if matrix.seo_signals.get("meta_tags") or matrix.seo_signals.get("structured_data"):
                    seo_signals_count = 1
            
            # Get last check timestamps
            last_checks = {
                "social_media": None,
                "website_structure": None,
                "press_releases": None,
                "marketing_changes": None,
                "seo_signals": None,
            }
            
            if matrix:
                # Social media last check
                if matrix.social_media_sources:
                    social_checks = [
                        v.get("last_checked") for v in matrix.social_media_sources.values()
                        if isinstance(v, dict) and v.get("last_checked")
                    ]
                    if social_checks:
                        last_checks["social_media"] = max(social_checks)
                
                # Website structure last check
                if matrix.website_sources and matrix.website_sources.get("last_snapshot_at"):
                    last_checks["website_structure"] = matrix.website_sources["last_snapshot_at"]
                
                # Press releases last check
                if matrix.news_sources and matrix.news_sources.get("last_scraped_at"):
                    last_checks["press_releases"] = matrix.news_sources["last_scraped_at"]
                
                # Marketing changes last check
                if matrix.marketing_sources and matrix.marketing_sources.get("last_checked_at"):
                    last_checks["marketing_changes"] = matrix.marketing_sources["last_checked_at"]
                
                # SEO signals last check
                if matrix.seo_signals and matrix.seo_signals.get("last_collected_at"):
                    last_checks["seo_signals"] = matrix.seo_signals["last_collected_at"]
            
            # Determine if monitoring is active
            is_active = matrix is not None and (
                social_media_count > 0 or
                website_pages_count > 0 or
                news_sources_count > 0 or
                marketing_sources_count > 0 or
                seo_signals_count > 0
            )
            
            statuses.append({
                "company_id": company_id_str,
                "company_name": company.name,
                "is_active": is_active,
                "last_updated": matrix.last_updated.isoformat() if matrix and matrix.last_updated else None,
                "sources_count": {
                    "social_media": social_media_count,
                    "website_pages": website_pages_count,
                    "news_sources": news_sources_count,
                    "marketing_sources": marketing_sources_count,
                    "seo_signals": seo_signals_count,
                },
                "last_checks": last_checks,
            })
        
        return {"statuses": statuses}
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve monitoring status: {str(e)}")


@router.get("/monitoring/stats")
async def get_monitoring_stats(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring statistics for user's companies.
    
    Returns:
    - total_companies: Total number of companies
    - active_monitoring: Number of companies with active monitoring
    - total_changes_detected: Total number of change events detected
    - changes_by_type: Count of changes grouped by source_type
    - last_24h_changes: Number of changes detected in last 24 hours
    """
    try:
        # Build access filter for companies
        if current_user:
            # Authenticated user: only their companies
            company_filter = Company.user_id == current_user.id
        else:
            # Anonymous user: only global companies
            company_filter = Company.user_id.is_(None)
        
        # Get total companies count
        total_companies_result = await db.execute(
            select(func.count(Company.id)).where(company_filter)
        )
        total_companies = total_companies_result.scalar() or 0
        
        # Get company IDs for further queries
        companies_result = await db.execute(
            select(Company.id).where(company_filter)
        )
        company_ids = [c for c in companies_result.scalars().all()]
        
        if not company_ids:
            return {
                "total_companies": 0,
                "active_monitoring": 0,
                "total_changes_detected": 0,
                "changes_by_type": {},
                "last_24h_changes": 0,
            }
        
        # Get active monitoring count (companies with monitoring matrix that has sources)
        matrices_result = await db.execute(
            select(CompetitorMonitoringMatrix)
            .join(Company, CompetitorMonitoringMatrix.company_id == Company.id)
            .where(company_filter)
        )
        matrices = matrices_result.scalars().all()
        
        active_monitoring = 0
        for matrix in matrices:
            has_sources = (
                (matrix.social_media_sources and len([
                    k for k, v in (matrix.social_media_sources or {}).items()
                    if v and isinstance(v, dict) and v.get("url")
                ]) > 0) or
                (matrix.website_sources and matrix.website_sources.get("key_pages") and 
                 len(matrix.website_sources.get("key_pages", [])) > 0) or
                (matrix.news_sources and (
                    len(matrix.news_sources.get("press_release_urls", [])) > 0 or
                    len(matrix.news_sources.get("blog_urls", [])) > 0
                )) or
                (matrix.marketing_sources and (
                    len(matrix.marketing_sources.get("banners", [])) > 0 or
                    len(matrix.marketing_sources.get("landing_pages", [])) > 0 or
                    len(matrix.marketing_sources.get("products", [])) > 0 or
                    len(matrix.marketing_sources.get("job_postings", [])) > 0
                )) or
                (matrix.seo_signals and (
                    matrix.seo_signals.get("meta_tags") or
                    matrix.seo_signals.get("structured_data")
                ))
            )
            if has_sources:
                active_monitoring += 1
        
        # Get total changes detected
        total_changes_result = await db.execute(
            select(func.count(CompetitorChangeEvent.id))
            .join(Company, CompetitorChangeEvent.company_id == Company.id)
            .where(company_filter)
        )
        total_changes_detected = total_changes_result.scalar() or 0
        
        # Get changes by type
        changes_by_type_result = await db.execute(
            select(
                CompetitorChangeEvent.source_type,
                func.count(CompetitorChangeEvent.id).label("count")
            )
            .join(Company, CompetitorChangeEvent.company_id == Company.id)
            .where(company_filter)
            .group_by(CompetitorChangeEvent.source_type)
        )
        changes_by_type = {}
        for row in changes_by_type_result.all():
            source_type = row.source_type
            # Convert enum to string if needed
            if hasattr(source_type, 'value'):
                source_type_str = source_type.value
            else:
                source_type_str = str(source_type)
            changes_by_type[source_type_str] = row.count
        
        # Get changes in last 24 hours
        last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        last_24h_changes_result = await db.execute(
            select(func.count(CompetitorChangeEvent.id))
            .join(Company, CompetitorChangeEvent.company_id == Company.id)
            .where(
                company_filter,
                CompetitorChangeEvent.detected_at >= last_24h
            )
        )
        last_24h_changes = last_24h_changes_result.scalar() or 0
        
        return {
            "total_companies": total_companies,
            "active_monitoring": active_monitoring,
            "total_changes_detected": total_changes_detected,
            "changes_by_type": changes_by_type,
            "last_24h_changes": last_24h_changes,
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve monitoring stats: {str(e)}")


@router.get("/monitoring/changes", response_model=MonitoringChangesResponseSchema)
async def get_monitoring_changes(
    company_ids: Optional[str] = Query(
        None,
        description="Comma-separated list of company UUIDs to filter by"
    ),
    change_types: Optional[str] = Query(
        None,
        description=(
            "Comma-separated list of change types. "
            "Typically comes from raw_diff['type'] values "
            "such as website_structure, marketing_banner, marketing_landing, "
            "marketing_product, marketing_jobs, seo_meta, seo_structure, pricing"
        ),
    ),
    date_from: Optional[datetime] = Query(
        None,
        description="Filter events from this date (ISO 8601 format)"
    ),
    date_to: Optional[datetime] = Query(
        None,
        description="Filter events to this date (ISO 8601 format)"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum number of results to return (1-500)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Offset for pagination"
    ),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring change events for companies.

    Returns change events detected by the monitoring system (pricing/features, website, marketing, etc.).

    Access control:
    - Authenticated users see events only for their companies (Company.user_id == current_user.id)
    - Anonymous users see events only for global companies (Company.user_id is NULL)

    Filtering:
    - Filter by specific companies using `company_ids`
    - Filter by change types using `change_types` (mapped from raw_diff['type'])
    - Filter by date range using `date_from` and `date_to`

    Pagination:
    - `limit` controls page size (default: 50, max: 500)
    - `offset` controls pagination offset
    - Response includes `total` count and `has_more` flag
    """
    try:
        from app.core.access_control import check_company_access  # noqa: F401  # kept for future per-company checks

        # Parse company IDs from comma-separated string
        company_id_list: list[UUIDType] = []
        if company_ids:
            for cid in company_ids.split(","):
                cid = cid.strip()
                if not cid:
                    continue
                try:
                    company_id_list.append(UUIDType(cid))
                except ValueError:
                    logger.warning(f"Invalid company ID format in monitoring/changes: {cid}")

        # Parse change types from comma-separated string
        change_type_list: list[str] = []
        if change_types:
            change_type_list = [ct.strip() for ct in change_types.split(",") if ct.strip()]

        # Build access filter for companies (data isolation)
        if current_user:
            # Authenticated user: only their companies
            company_filter = Company.user_id == current_user.id
        else:
            # Anonymous user: only global companies
            company_filter = Company.user_id.is_(None)

        # Base query joining companies for access control
        conditions = [company_filter]

        if company_id_list:
            conditions.append(CompetitorChangeEvent.company_id.in_(company_id_list))

        # Filter by change type from raw_diff['type'] when provided
        if change_type_list:
            type_conditions = []
            for ct in change_type_list:
                type_conditions.append(
                    CompetitorChangeEvent.raw_diff["type"].astext == ct
                )
            if type_conditions:
                conditions.append(or_(*type_conditions))

        # Date filters
        if date_from:
            conditions.append(CompetitorChangeEvent.detected_at >= date_from)
        if date_to:
            conditions.append(CompetitorChangeEvent.detected_at <= date_to)

        # Build main query
        base_query = (
            select(CompetitorChangeEvent)
            .join(Company, CompetitorChangeEvent.company_id == Company.id)
        )

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # Total count query
        count_query = (
            select(func.count(CompetitorChangeEvent.id))
            .join(Company, CompetitorChangeEvent.company_id == Company.id)
            .where(and_(*conditions)) if conditions else
            select(func.count(CompetitorChangeEvent.id))
        )

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply ordering and pagination
        events_query = (
            base_query
            .order_by(CompetitorChangeEvent.detected_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(events_query)
        events = result.scalars().all()

        # Map events to response format expected by frontend
        events_data = []
        for event in events:
            raw_diff = event.raw_diff or {}
            # Prefer explicit type from raw_diff, fallback to source_type
            raw_type = raw_diff.get("type")
            if raw_type:
                change_type = str(raw_type)
            else:
                source_type = event.source_type
                if hasattr(source_type, "value"):
                    change_type = source_type.value
                else:
                    change_type = str(source_type)

            events_data.append(
                {
                    "id": str(event.id),
                    "company_id": str(event.company_id),
                    "change_type": change_type,
                    "change_summary": event.change_summary,
                    "detected_at": event.detected_at.isoformat(),
                    # Frontend expects generic details object; we pass full raw_diff
                    "details": raw_diff,
                }
            )

        return {
            "events": events_data,
            "total": total,
            "has_more": (offset + limit) < total,
        }

    except Exception as e:
        logger.error(f"Failed to get monitoring changes: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve monitoring changes: {str(e)}",
        )
