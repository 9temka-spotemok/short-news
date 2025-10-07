"""
Script to populate database with real AI news
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from loguru import logger

from app.core.database import AsyncSessionLocal
from app.models.company import Company
from app.models.news import NewsItem, NewsCategory, SourceType
from app.scrapers.real_scrapers import AINewsScraper


async def get_company_by_name(db, name: str):
    """Get company by name"""
    result = await db.execute(
        select(Company).where(Company.name == name)
    )
    return result.scalar_one_or_none()


async def populate_news():
    """Populate database with real news"""
    logger.info("Starting news population...")
    
    scraper = AINewsScraper()
    
    try:
        # Scrape all news
        news_data = await scraper.scrape_all()
        logger.info(f"Scraped {len(news_data)} news items")
        
        async with AsyncSessionLocal() as db:
            added_count = 0
            
            for item in news_data:
                try:
                    # Check if already exists
                    result = await db.execute(
                        select(NewsItem).where(NewsItem.source_url == item['source_url'])
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        logger.debug(f"News already exists: {item['title'][:50]}")
                        continue
                    
                    # Get company
                    company = await get_company_by_name(db, item['company_name'])
                    if not company:
                        logger.warning(f"Company not found: {item['company_name']}")
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
                    )
                    
                    db.add(news_item)
                    added_count += 1
                    logger.info(f"Added news: {item['title'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"Failed to add news item: {e}")
                    continue
            
            await db.commit()
            logger.info(f"✅ Successfully added {added_count} news items")
            
            # Get final count
            result = await db.execute(select(NewsItem))
            total = len(result.scalars().all())
            logger.info(f"Total news items in database: {total}")
            
            return {"status": "success", "added": added_count, "total": total}
            
    except Exception as e:
        logger.error(f"Failed to populate news: {e}")
        raise
    finally:
        await scraper.close()


if __name__ == "__main__":
    result = asyncio.run(populate_news())
    print(f"\n✅ News population completed:")
    print(f"   Added: {result['added']}")
    print(f"   Total: {result['total']}")

