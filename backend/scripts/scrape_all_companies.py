"""
Scrape news from all companies in database
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import select
from loguru import logger

import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.company import Company
from app.models.news import NewsItem, SourceType, NewsCategory
from app.scrapers.universal_scraper import UniversalBlogScraper
from datetime import datetime


async def get_all_companies() -> List[Dict[str, str]]:
    """Get all companies from database"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Company).order_by(Company.name)
        )
        companies = result.scalars().all()
        
        return [
            {
                'id': str(company.id),
                'name': company.name,
                'website': company.website
            }
            for company in companies
            if company.website
        ]


async def save_news_items(news_items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save news items to database"""
    async with AsyncSessionLocal() as db:
        saved_count = 0
        skipped_count = 0
        error_count = 0
        
        for item in news_items:
            try:
                # Check if already exists
                result = await db.execute(
                    select(NewsItem).where(NewsItem.source_url == item['source_url'])
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Get company by name
                result = await db.execute(
                    select(Company).where(Company.name == item['company_name'])
                )
                company = result.scalar_one_or_none()
                
                if not company:
                    logger.warning(f"Company not found: {item['company_name']}")
                    error_count += 1
                    continue
                
                # Create news item
                news_item = NewsItem(
                    title=item['title'],
                    content=item['content'],
                    summary=item['summary'],
                    source_url=item['source_url'],
                    source_type=SourceType(item['source_type']),
                    company_id=company.id,
                    category=NewsCategory(item['category']) if item.get('category') else None,
                    published_at=item['published_at'],
                    priority_score=0.5
                )
                
                db.add(news_item)
                saved_count += 1
                logger.info(f"Saved news: {item['title'][:50]}...")
                
            except Exception as e:
                logger.error(f"Failed to save news item: {e}")
                error_count += 1
                continue
        
        await db.commit()
        
        return {
            'saved': saved_count,
            'skipped': skipped_count,
            'errors': error_count
        }


async def main():
    """Main function"""
    logger.info("Starting news scraping for all companies...")
    
    # Get all companies
    companies = await get_all_companies()
    logger.info(f"Found {len(companies)} companies with websites")
    
    if not companies:
        logger.warning("No companies found in database. Please run import_competitors_from_csv.py first.")
        return
    
    # Initialize scraper
    scraper = UniversalBlogScraper()
    
    try:
        # Scrape news from all companies (max 5 articles per company)
        logger.info(f"Starting to scrape news from {len(companies)} companies...")
        news_items = await scraper.scrape_multiple_companies(
            companies,
            max_articles_per_company=5
        )
        
        logger.info(f"Scraped {len(news_items)} total news items")
        
        # Save to database
        if news_items:
            logger.info("Saving news items to database...")
            result = await save_news_items(news_items)
            
            print(f"\n✅ Scraping Results:")
            print(f"   Total scraped: {len(news_items)} news items")
            print(f"   Saved: {result['saved']} items")
            print(f"   Skipped (duplicates): {result['skipped']} items")
            print(f"   Errors: {result['errors']} items")
        else:
            logger.warning("No news items were scraped")
            print(f"\n⚠️  No news items were scraped from {len(companies)} companies")
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())






