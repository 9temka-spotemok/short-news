"""
Scrape news from all companies in database
"""

import asyncio
from pathlib import Path
from typing import Dict, List
from uuid import UUID

from loguru import logger
from sqlalchemy import select

import sys

sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.domains.news import NewsFacade
from app.domains.news.scrapers import CompanyContext
from app.models.company import Company


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


async def ingest_company_news(
    facade: NewsFacade,
    company_entry: Dict[str, str],
    max_articles: int,
) -> Dict[str, int]:
    context = CompanyContext(
        id=UUID(company_entry["id"]),
        name=company_entry["name"],
        website=company_entry["website"],
    )
    ingested = await facade.scraper_service.ingest_company_news(
        context,
        max_articles=max_articles,
    )
    return {
        "company_id": company_entry["id"],
        "ingested": ingested,
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
    
    async with AsyncSessionLocal() as db:
        facade = NewsFacade(db)
        total_ingested = 0
        for entry in companies:
            result = await ingest_company_news(facade, entry, max_articles=5)
            total_ingested += result["ingested"]
            logger.info(
                "Ingested %s items for company %s",
                result["ingested"],
                entry["name"],
            )

    print("\n✅ Scraping Results:")
    print(f"   Companies processed: {len(companies)}")
    print(f"   News items ingested: {total_ingested}")


if __name__ == "__main__":
    asyncio.run(main())






