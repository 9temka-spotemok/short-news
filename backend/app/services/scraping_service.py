"""
Scraping service for managing scrapers
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.scrapers.openai_scraper import OpenAIScraper
from app.services.news_service import NewsService


class ScrapingService:
    """Service for managing web scrapers"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.news_service = NewsService(db)
        self.scrapers = {
            'openai_blog': OpenAIScraper(),
        }
    
    async def run_scraper(self, scraper_id: str) -> Dict[str, Any]:
        """
        Run a specific scraper
        """
        if scraper_id not in self.scrapers:
            raise ValueError(f"Unknown scraper: {scraper_id}")
        
        scraper = self.scrapers[scraper_id]
        logger.info(f"Starting scraper: {scraper_id}")
        
        try:
            # Run the scraper
            scraped_items = await scraper.scrape()
            logger.info(f"Scraper {scraper_id} found {len(scraped_items)} items")
            
            # Save items to database
            saved_count = 0
            for item in scraped_items:
                try:
                    await self.news_service.create_news_item(item)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save item: {e}")
                    continue
            
            logger.info(f"Scraper {scraper_id} saved {saved_count} items")
            
            return {
                'scraper_id': scraper_id,
                'scraped_count': len(scraped_items),
                'saved_count': saved_count,
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Scraper {scraper_id} failed: {e}")
            return {
                'scraper_id': scraper_id,
                'scraped_count': 0,
                'saved_count': 0,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def run_all_scrapers(self) -> List[Dict[str, Any]]:
        """
        Run all available scrapers
        """
        results = []
        
        for scraper_id in self.scrapers.keys():
            try:
                result = await self.run_scraper(scraper_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to run scraper {scraper_id}: {e}")
                results.append({
                    'scraper_id': scraper_id,
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    async def get_scraper_status(self, scraper_id: str) -> Dict[str, Any]:
        """
        Get status of a specific scraper
        """
        if scraper_id not in self.scrapers:
            return {'status': 'not_found'}
        
        scraper = self.scrapers[scraper_id]
        
        try:
            # Test scraper by fetching a simple page
            test_url = scraper.base_url
            soup = await scraper.fetch_page(test_url)
            
            return {
                'scraper_id': scraper_id,
                'status': 'active' if soup else 'error',
                'base_url': scraper.base_url,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'scraper_id': scraper_id,
                'status': 'error',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    async def get_all_scrapers_status(self) -> List[Dict[str, Any]]:
        """
        Get status of all scrapers
        """
        results = []
        
        for scraper_id in self.scrapers.keys():
            status = await self.get_scraper_status(scraper_id)
            results.append(status)
        
        return results
    
    async def close_all_scrapers(self):
        """
        Close all scraper sessions
        """
        for scraper in self.scrapers.values():
            try:
                await scraper.close()
            except Exception as e:
                logger.error(f"Failed to close scraper: {e}")
    
    def get_available_scrapers(self) -> List[str]:
        """
        Get list of available scraper IDs
        """
        return list(self.scrapers.keys())
