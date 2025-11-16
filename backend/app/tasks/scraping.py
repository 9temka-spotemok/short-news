"""
Web scraping tasks
"""

import asyncio
import threading
from celery import current_task
from loguru import logger
from typing import List, Dict

from app.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.domains.news import NewsFacade
from app.domains.news.scrapers.interfaces import CompanyContext
from app.models import Company
from app.scrapers.real_scrapers import AINewsScraper
from sqlalchemy import select
from datetime import datetime, timedelta

_ASYNC_EVENT_LOOP = None
_ASYNC_LOCK = threading.Lock()


def _get_event_loop() -> asyncio.AbstractEventLoop:
    global _ASYNC_EVENT_LOOP
    if _ASYNC_EVENT_LOOP is None or _ASYNC_EVENT_LOOP.is_closed():
        _ASYNC_EVENT_LOOP = asyncio.new_event_loop()
    return _ASYNC_EVENT_LOOP


def _run_async(fn, *args, **kwargs):
    """Выполнить асинхронную корутину в выделенном event loop текущего процесса."""
    coro = fn(*args, **kwargs)
    with _ASYNC_LOCK:
        loop = _get_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        loop.run_until_complete(loop.shutdown_asyncgens())
    return result


@celery_app.task(bind=True)
def scrape_ai_blogs(self):
    """
    Scrape AI company blogs for new content
    """
    logger.info("Starting AI blogs scraping task")
    
    try:
        result = _run_async(_scrape_ai_blogs_async)
        logger.info(f"AI blogs scraping completed: {result['scraped_count']} items scraped")
        return result
        
    except Exception as e:
        logger.error(f"AI blogs scraping failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _scrape_ai_blogs_async():
    """Async implementation of blog scraping"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Company).order_by(Company.created_at.desc()))
        companies = result.scalars().all()

        logger.info(f"Found {len(companies)} companies to scrape")

        facade = NewsFacade(db)
        saved_count = 0

        for company in companies:
            context = CompanyContext(
                id=company.id,
                name=company.name or "",
                website=company.website,
                news_page_url=getattr(company, "news_page_url", None),
            )
            ingested = await facade.scraper_service.ingest_company_news(
                context,
                max_articles=5,
            )
            saved_count += ingested

        return {"status": "success", "scraped_count": saved_count}


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
