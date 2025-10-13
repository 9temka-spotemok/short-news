"""
Script to fix news categories by re-scraping and updating existing news
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update, func
from loguru import logger

from app.core.database import AsyncSessionLocal
from app.models.news import NewsItem, NewsCategory
from app.scrapers.real_scrapers import AINewsScraper


async def fix_news_categories():
    """Fix news categories by applying intelligent categorization"""
    logger.info("Starting news categories fix...")
    
    scraper = AINewsScraper()
    
    try:
        async with AsyncSessionLocal() as db:
            # Get all news items that need category fixing
            result = await db.execute(
                select(NewsItem).where(
                    NewsItem.category.is_(None) | 
                    (NewsItem.category == 'product_update')
                )
            )
            news_items = result.scalars().all()
            
            logger.info(f"Found {len(news_items)} news items to fix")
            
            updated_count = 0
            
            for item in news_items:
                try:
                    # Determine new category based on title
                    new_category = scraper._determine_category(item.title, item.company.name if item.company else 'Unknown')
                    
                    # Update the news item
                    await db.execute(
                        update(NewsItem)
                        .where(NewsItem.id == item.id)
                        .values(category=new_category)
                    )
                    
                    updated_count += 1
                    logger.info(f"Updated news item {item.id}: '{item.title[:50]}...' -> {new_category}")
                    
                except Exception as e:
                    logger.error(f"Failed to update news item {item.id}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"✅ Successfully updated {updated_count} news items")
            
            # Show category distribution
            result = await db.execute(
                select(NewsItem.category, func.count(NewsItem.id)).group_by(NewsItem.category)
            )
            categories = result.all()
            logger.info("Updated news categories distribution:")
            for category, count in categories:
                logger.info(f"  {category}: {count}")
            
            return {"status": "success", "updated": updated_count}
            
    except Exception as e:
        logger.error(f"Failed to fix news categories: {e}")
        raise
    finally:
        await scraper.close()


if __name__ == "__main__":
    result = asyncio.run(fix_news_categories())
    print(f"\n✅ News categories fix completed:")
    print(f"   Updated: {result['updated']}")
