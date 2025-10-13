"""
Import competitor companies from CSV file to database
"""

import asyncio
import csv
from pathlib import Path
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.company import Company


def parse_csv_file(csv_path: str) -> List[Dict[str, str]]:
    """Parse competitor CSV file and extract company data"""
    companies = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        # Find header row (row 8)
        header_idx = 7  # 0-indexed
        
        # Process data rows
        for i in range(8, len(rows)):
            row = rows[i]
            
            # Skip empty rows or end marker
            if len(row) < 5 or not row[1] or 'END OF SHEET' in str(row):
                continue
            
            try:
                # Extract data from columns
                no = row[1].strip() if len(row) > 1 else ""
                name = row[2].strip() if len(row) > 2 else ""
                website = row[4].strip() if len(row) > 4 else ""
                year_founded = row[7].strip() if len(row) > 7 else ""
                company_type = row[9].strip() if len(row) > 9 else ""
                pricing = row[11].strip() if len(row) > 11 else ""
                notes = row[12].strip() if len(row) > 12 else ""
                linkedin = row[14].strip() if len(row) > 14 else ""
                twitter = row[16].strip() if len(row) > 16 else ""
                
                # Skip if no name or website
                if not name or not website:
                    continue
                
                # Extract Twitter handle from URL
                twitter_handle = None
                if twitter:
                    if 'twitter.com/' in twitter or 'x.com/' in twitter:
                        twitter_handle = twitter.split('/')[-1].strip()
                    elif twitter.startswith('@'):
                        twitter_handle = twitter[1:]
                
                # Build description
                description_parts = []
                if company_type:
                    description_parts.append(f"{company_type}")
                if notes:
                    description_parts.append(notes)
                if pricing:
                    description_parts.append(f"Pricing: {pricing}")
                if year_founded:
                    description_parts.append(f"Founded: {year_founded}")
                
                description = ". ".join(description_parts) if description_parts else company_type
                
                company_data = {
                    'name': name,
                    'website': website,
                    'description': description[:500] if description else None,
                    'category': 'geo_competitor',  # GEO/LLM monitoring competitor
                    'twitter_handle': twitter_handle,
                }
                
                companies.append(company_data)
                logger.info(f"Parsed company: {name}")
                
            except Exception as e:
                logger.warning(f"Failed to parse row {i}: {e}")
                continue
    
    logger.info(f"Parsed {len(companies)} companies from CSV")
    return companies


async def import_companies_to_db(companies: List[Dict[str, str]]) -> Dict[str, int]:
    """Import companies to database"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Get existing companies
            result = await db.execute(select(Company))
            existing = result.scalars().all()
            existing_names = {c.name for c in existing}
            existing_websites = {c.website for c in existing}
            
            logger.info(f"Found {len(existing)} existing companies")
            
            # Add new companies
            added_count = 0
            skipped_count = 0
            
            for company_data in companies:
                try:
                    # Check if already exists (by name or website)
                    if company_data['name'] in existing_names:
                        logger.info(f"Skipping existing company (by name): {company_data['name']}")
                        skipped_count += 1
                        continue
                    
                    if company_data['website'] in existing_websites:
                        logger.info(f"Skipping existing company (by website): {company_data['name']}")
                        skipped_count += 1
                        continue
                    
                    # Create new company
                    company = Company(**company_data)
                    db.add(company)
                    await db.flush()  # Flush immediately to catch unique constraint errors
                    
                    # Update tracking sets
                    existing_names.add(company_data['name'])
                    existing_websites.add(company_data['website'])
                    
                    added_count += 1
                    logger.info(f"Added company: {company_data['name']}")
                    
                except Exception as e:
                    logger.warning(f"Failed to add company {company_data.get('name', 'Unknown')}: {e}")
                    await db.rollback()
                    # Start new transaction
                    await db.begin()
                    skipped_count += 1
                    continue
            
            await db.commit()
            
            logger.info(f"Successfully imported {added_count} new companies")
            logger.info(f"Skipped {skipped_count} existing companies")
            logger.info(f"Total companies in database: {len(existing) + added_count}")
            
            return {
                'status': 'success',
                'added': added_count,
                'skipped': skipped_count,
                'total': len(existing) + added_count
            }
            
        except Exception as e:
            logger.error(f"Failed to import companies: {e}")
            await db.rollback()
            raise


async def main():
    """Main function"""
    # Path to CSV file
    csv_path = Path(__file__).parent.parent.parent / '.playwright-mcp' / 'Копия-SKOUR-Competitor-Matrix---✦-Skour-Competitors.csv'
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    logger.info(f"Reading CSV file: {csv_path}")
    
    # Parse CSV
    companies = parse_csv_file(str(csv_path))
    
    # Import to database
    result = await import_companies_to_db(companies)
    
    logger.info(f"Import completed: {result}")
    print(f"\n✅ Import Results:")
    print(f"   Added: {result['added']} companies")
    print(f"   Skipped: {result['skipped']} companies")
    print(f"   Total: {result['total']} companies in database")


if __name__ == "__main__":
    asyncio.run(main())


