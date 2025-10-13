"""
Simple script to fix news categories without complex imports
"""

import asyncio
import asyncpg
import os
from typing import Dict, List


def determine_category(title: str, company: str) -> str:
    """Determine news category based on title content"""
    title_lower = title.lower()
    
    # Technical updates
    if any(keyword in title_lower for keyword in [
        'api', 'technical', 'update', 'improvement', 'performance', 
        'optimization', 'infrastructure', 'system', 'backend'
    ]):
        return 'technical_update'
    
    # Product updates
    if any(keyword in title_lower for keyword in [
        'release', 'launch', 'new feature', 'product', 'version', 
        'update', 'announcement', 'introducing'
    ]):
        return 'product_update'
    
    # Strategic announcements
    if any(keyword in title_lower for keyword in [
        'strategy', 'partnership', 'collaboration', 'acquisition', 
        'investment', 'funding', 'business', 'market'
    ]):
        return 'strategic_announcement'
    
    # Research papers
    if any(keyword in title_lower for keyword in [
        'research', 'paper', 'study', 'analysis', 'findings', 
        'publication', 'journal'
    ]):
        return 'research_paper'
    
    # Security updates
    if any(keyword in title_lower for keyword in [
        'security', 'safety', 'privacy', 'protection', 'vulnerability'
    ]):
        return 'security_update'
    
    # Model releases
    if any(keyword in title_lower for keyword in [
        'model', 'gpt', 'claude', 'gemini', 'llama', 'training', 
        'dataset', 'weights'
    ]):
        return 'model_release'
    
    # Company-specific defaults
    company_defaults = {
        'OpenAI': 'product_update',
        'Anthropic': 'product_update', 
        'Google': 'technical_update',
        'Meta': 'product_update',
        'Hugging Face': 'technical_update',
        'Mistral AI': 'product_update',
        'Cohere': 'technical_update',
        'Stability AI': 'product_update',
        'Perplexity AI': 'product_update'
    }
    
    return company_defaults.get(company, 'product_update')


async def fix_categories():
    """Fix news categories"""
    # Database connection
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'shot_news'),
        user=os.getenv('DB_USER', 'shot_news'),
        password=os.getenv('DB_PASSWORD', 'shot_news_dev')
    )
    
    try:
        # Get news items that need fixing
        rows = await conn.fetch("""
            SELECT n.id, n.title, c.name as company_name
            FROM news_items n
            LEFT JOIN companies c ON n.company_id = c.id
            WHERE n.category IS NULL OR n.category = 'product_update'
        """)
        
        print(f"Found {len(rows)} news items to fix")
        
        updated_count = 0
        
        for row in rows:
            new_category = determine_category(row['title'], row['company_name'] or 'Unknown')
            
            await conn.execute(
                "UPDATE news_items SET category = $1 WHERE id = $2",
                new_category, row['id']
            )
            
            updated_count += 1
            print(f"Updated: '{row['title'][:50]}...' -> {new_category}")
        
        print(f"✅ Updated {updated_count} news items")
        
        # Show category distribution
        categories = await conn.fetch("""
            SELECT category, COUNT(*) as count
            FROM news_items 
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)
        
        print("\nCategory distribution:")
        for cat in categories:
            print(f"  {cat['category']}: {cat['count']}")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(fix_categories())
