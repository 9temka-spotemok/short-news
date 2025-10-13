"""
Full import script: Import companies from CSV and scrape their news
"""

import asyncio
from pathlib import Path
from loguru import logger
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import the other scripts
from scripts.import_competitors_from_csv import parse_csv_file, import_companies_to_db
from scripts.scrape_all_companies import get_all_companies, save_news_items
from app.scrapers.universal_scraper import UniversalBlogScraper


async def main():
    """Run full import process"""
    
    print("\n" + "="*70)
    print("  FULL IMPORT PROCESS - Companies & News")
    print("="*70 + "\n")
    
    # Step 1: Import companies from CSV
    print("STEP 1: Importing companies from CSV...")
    print("-"*70)
    
    csv_path = Path(__file__).parent.parent.parent / '.playwright-mcp' / 'Копия-SKOUR-Competitor-Matrix---✦-Skour-Competitors.csv'
    
    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return
    
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
    
    scraper = UniversalBlogScraper()
    
    try:
        news_items = await scraper.scrape_multiple_companies(
            companies,
            max_articles_per_company=5
        )
        
        print(f"\n[SUCCESS] Scraped {len(news_items)} total news items")
        
        # Step 4: Save news to database
        if news_items:
            print(f"\nSTEP 4: Saving news items to database...")
            print("-"*70)
            
            save_result = await save_news_items(news_items)
            
            print(f"\n[SUCCESS] Save Results:")
            print(f"   - Total scraped: {len(news_items)} news items")
            print(f"   - Saved: {save_result['saved']} new items")
            print(f"   - Skipped: {save_result['skipped']} duplicates")
            print(f"   - Errors: {save_result['errors']} failed items")
        else:
            print(f"\n[WARNING] No news items were scraped")
        
        # Final summary
        print("\n" + "="*70)
        print("  [SUCCESS] IMPORT PROCESS COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"\nSummary:")
        print(f"   - Companies in database: {import_result['total']}")
        print(f"   - News items scraped: {len(news_items)}")
        print(f"   - News items saved: {save_result.get('saved', 0)}")
        print("\n")
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())

