"""
Companies endpoints
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from loguru import logger
from urllib.parse import urlparse
from datetime import datetime

from app.core.database import get_db
from app.models.company import Company
from app.models.news import (
    NewsItem,
    NewsCategory,
    SourceType,
    NewsTopic,
    SentimentLabel,
)
from app.scrapers.universal_scraper import UniversalBlogScraper
from app.services.company_info_extractor import extract_company_info
from app.api.dependencies import get_current_user
from app.models import User

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
    netloc = parsed.netloc.lower().replace('www.', '')
    path = parsed.path.rstrip('/')
    normalized = f"{parsed.scheme}://{netloc}{path}"
    return normalized


@router.get("/")
async def get_companies(
    search: Optional[str] = Query(None, description="Search companies by name"),
    limit: int = Query(100, ge=1, le=200, description="Number of companies to return"),
    offset: int = Query(0, ge=0, description="Number of companies to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of companies with optional search
    """
    logger.info(f"Companies request: search={search}, limit={limit}, offset={offset}")
    
    try:
        # Build query
        query = select(Company).order_by(Company.name)
        
        # Apply search filter
        if search:
            query = query.where(Company.name.ilike(f"%{search}%"))
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        companies = result.scalars().all()
        
        # Get total count
        count_query = select(func.count(Company.id))
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
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific company by ID
    """
    logger.info(f"Get company: {company_id}")
    
    try:
        from uuid import UUID
        
        # Parse UUID
        try:
            uuid_obj = UUID(company_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company ID format")
        
        # Get company
        result = await db.execute(
            select(Company).where(Company.id == uuid_obj)
        )
        company = result.scalar_one_or_none()
        
        if not company:
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
    
    scraper = UniversalBlogScraper()
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
        news_items = await scraper.scrape_company_blog(
            company_name=company_name,
            website=website_url,
            news_page_url=news_page_url,
            max_articles=50,  # Limit for quick preview
            source_overrides=source_overrides if isinstance(source_overrides, list) else None,
        )
        
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
        await scraper.close()


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
        
        # Check for existing company by URL or name
        result = await db.execute(
            select(Company).where(
                or_(
                    func.lower(func.replace(Company.website, 'www.', '')) == normalized_url.lower(),
                    Company.name.ilike(f"%{company_data.get('name', '')}%")
                )
            )
        )
        existing_company = result.scalar_one_or_none()
        
        if existing_company:
            # Update existing company - дополняем информацию
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
        else:
            # Create new company
            logger.info(f"Creating new company: {company_data.get('name')}")
            
            company = Company(
                name=company_data.get("name"),
                website=website_url,
                description=company_data.get("description"),
                logo_url=company_data.get("logo_url"),
                category=company_data.get("category"),
                twitter_handle=company_data.get("twitter_handle"),
                github_org=company_data.get("github_org")
            )
            db.add(company)
            await db.flush()
            action = "created"
        
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





