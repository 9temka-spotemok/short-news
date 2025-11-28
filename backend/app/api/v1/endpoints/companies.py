"""
Companies endpoints
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from loguru import logger
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from uuid import UUID as UUIDType

from app.core.database import get_db
from app.models.company import Company
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





