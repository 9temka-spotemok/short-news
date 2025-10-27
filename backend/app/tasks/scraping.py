"""
Web scraping tasks
"""

import asyncio
from celery import current_task
from loguru import logger
import nest_asyncio
from typing import List, Dict

from app.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models import Company, NewsItem, SourceType
from app.scrapers.universal_scraper import UniversalBlogScraper
from app.scrapers.real_scrapers import AINewsScraper
from sqlalchemy import select
from datetime import datetime, timedelta

# Apply nest_asyncio for async in Celery
nest_asyncio.apply()


@celery_app.task(bind=True)
def scrape_ai_blogs(self):
    """
    Scrape AI company blogs for new content
    """
    logger.info("Starting AI blogs scraping task")
    
    try:
        # Apply nest_asyncio and run async function
        result = asyncio.run(_scrape_ai_blogs_async())
        logger.info(f"AI blogs scraping completed: {result['scraped_count']} items scraped")
        return result
        
    except Exception as e:
        logger.error(f"AI blogs scraping failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _scrape_ai_blogs_async():
    """Async implementation of blog scraping"""
    scraper = UniversalBlogScraper()
    
    try:
        # Get all companies from database
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Company))
            companies = result.scalars().all()
        
        logger.info(f"Found {len(companies)} companies to scrape")
        
        # Prepare company list for scraper
        company_list = [
            {'name': c.name, 'website': c.website}
            for c in companies
        ]
        
        # Scrape blogs
        all_news = await scraper.scrape_multiple_companies(
            company_list,
            max_articles_per_company=5
        )
        
        # Save to database
        async with AsyncSessionLocal() as db:
            saved_count = 0
            
            for news_data in all_news:
                # Find company
                result = await db.execute(
                    select(Company).where(Company.name == news_data['company_name'])
                )
                company = result.scalar_one_or_none()
                
                if not company:
                    continue
                
                # Check if news already exists
                existing = await db.execute(
                    select(NewsItem).where(NewsItem.source_url == news_data['source_url'])
                )
                if existing.scalar_one_or_none():
                    continue
                
                # Create news item
                news_item = NewsItem(
                    title=news_data['title'],
                    content=news_data.get('content', news_data['summary']),
                    summary=news_data['summary'],
                    source_url=news_data['source_url'],
                    source_type=news_data['source_type'],
                    category=news_data['category'],
                    company_id=company.id,
                    published_at=news_data['published_at']
                )
                
                db.add(news_item)
                saved_count += 1
            
            await db.commit()
        
        return {"status": "success", "scraped_count": saved_count}
        
    finally:
        await scraper.close()


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
