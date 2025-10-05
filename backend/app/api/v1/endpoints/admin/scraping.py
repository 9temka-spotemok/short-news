"""
Admin endpoints for scraping management
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.services.scraping_service import ScrapingService

router = APIRouter()


@router.get("/scrapers")
async def get_scrapers_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of all scrapers
    """
    try:
        scraping_service = ScrapingService(db)
        status = await scraping_service.get_all_scrapers_status()
        
        return {
            "scrapers": status,
            "total": len(status)
        }
        
    except Exception as e:
        logger.error(f"Failed to get scrapers status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scrapers status")


@router.post("/scrapers/{scraper_id}/run")
async def run_scraper(
    scraper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Run a specific scraper
    """
    try:
        scraping_service = ScrapingService(db)
        
        if scraper_id not in scraping_service.get_available_scrapers():
            raise HTTPException(status_code=404, detail=f"Scraper {scraper_id} not found")
        
        result = await scraping_service.run_scraper(scraper_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run scraper {scraper_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run scraper: {str(e)}")


@router.post("/scrapers/run-all")
async def run_all_scrapers(
    db: AsyncSession = Depends(get_db)
):
    """
    Run all available scrapers
    """
    try:
        scraping_service = ScrapingService(db)
        results = await scraping_service.run_all_scrapers()
        
        total_scraped = sum(r.get('scraped_count', 0) for r in results)
        total_saved = sum(r.get('saved_count', 0) for r in results)
        
        return {
            "results": results,
            "summary": {
                "total_scraped": total_scraped,
                "total_saved": total_saved,
                "scrapers_run": len(results)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to run all scrapers: {e}")
        raise HTTPException(status_code=500, detail="Failed to run scrapers")


@router.get("/scrapers/{scraper_id}/status")
async def get_scraper_status(
    scraper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of a specific scraper
    """
    try:
        scraping_service = ScrapingService(db)
        
        if scraper_id not in scraping_service.get_available_scrapers():
            raise HTTPException(status_code=404, detail=f"Scraper {scraper_id} not found")
        
        status = await scraping_service.get_scraper_status(scraper_id)
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scraper status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scraper status")
