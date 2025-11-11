"""
Import script for running inside Docker container
"""

import asyncio
from pathlib import Path
import sys

sys.path.append('/app')

from scripts.import_competitors_from_csv import parse_csv_file, import_companies_to_db
from scripts.scrape_all_companies import get_all_companies, ingest_company_news
from app.core.database import AsyncSessionLocal
from app.domains.news import NewsFacade


async def main():
    """Run full import process"""
    
    print("\n" + "="*70)
    print("  FULL IMPORT PROCESS - Companies & News")
    print("="*70 + "\n")
    
    # Step 1: Import companies from CSV
    print("STEP 1: Importing companies from CSV...")
    print("-"*70)
    
    # Try multiple possible paths
    csv_paths = [
        "/app/competitors.csv",
        "/app/.playwright-mcp/Копия-SKOUR-Competitor-Matrix---✦-Skour-Competitors.csv",
    ]
    
    csv_path = None
    for path in csv_paths:
        if Path(path).exists():
            csv_path = path
            break
    
    if not csv_path:
        print(f"[ERROR] CSV file not found in any of: {csv_paths}")
        return
    
    print(f"[INFO] Using CSV file: {csv_path}")
    
    companies_data = parse_csv_file(str(csv_path))
    import_result = await import_companies_to_db(companies_data)
    
    print(f"\n[SUCCESS] Import Results:")
    print(f"   - Added: {import_result['added']} companies")
    print(f"   - Skipped: {import_result['skipped']} companies (already exist)")
    print(f"   - Total in DB: {import_result['total']} companies")
    
    # Step 2: Get all companies with websites
    print(f"\nSTEP 2: Loading companies from database...")
    print("-"*70)
    
    companies = await get_all_companies()
    print(f"[SUCCESS] Found {len(companies)} companies with websites")
    
    # Step 3: Scrape news from all companies
    print(f"\nSTEP 3: Scraping news from all companies...")
    print("-"*70)
    print(f"   This may take a few minutes...\n")
    
    total_ingested = 0
    async with AsyncSessionLocal() as db:
        facade = NewsFacade(db)
        for company in companies:
            result = await ingest_company_news(facade, company, max_articles=5)
            total_ingested += result["ingested"]

    print(f"\n[SUCCESS] News ingestion completed: {total_ingested} items ingested")
    
    # Final summary
    print("\n" + "="*70)
    print("  [SUCCESS] IMPORT PROCESS COMPLETED SUCCESSFULLY!")
    print("="*70)
    print(f"\nSummary:")
    print(f"   - Companies in database: {import_result['total']}")
    print(f"   - News items ingested: {total_ingested}")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())


