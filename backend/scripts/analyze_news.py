"""Analyze news in database"""

import sys
import asyncio
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.news import NewsItem
from app.models.company import Company

async def analyze_news():
    async with AsyncSessionLocal() as db:
        # Total count
        count_query = await db.execute(select(func.count(NewsItem.id)))
        total = count_query.scalar()
        print(f"\n📊 АНАЛИЗ НОВОСТЕЙ")
        print(f"{'='*50}")
        print(f"Всего новостей в базе: {total}")
        
        # By company
        print(f"\n📈 По компаниям:")
        news_query = await db.execute(
            select(NewsItem, Company)
            .join(Company, NewsItem.company_id == Company.id)
        )
        news_with_companies = news_query.all()
        
        companies = Counter()
        categories = Counter()
        sources = Counter()
        
        for news, company in news_with_companies:
            companies[company.name] += 1
            if news.category:
                categories[news.category.value] += 1
            sources[news.source_type.value] += 1
        
        for company_name, count in companies.most_common():
            print(f"  • {company_name}: {count} новостей")
        
        print(f"\n📂 По категориям:")
        for category, count in categories.most_common():
            print(f"  • {category}: {count} новостей")
        
        print(f"\n🌐 По источникам:")
        for source, count in sources.most_common():
            print(f"  • {source}: {count} новостей")
        
        # Recent news
        print(f"\n🆕 Последние 5 добавленных новостей:")
        recent_query = await db.execute(
            select(NewsItem, Company)
            .join(Company, NewsItem.company_id == Company.id)
            .order_by(NewsItem.created_at.desc())
            .limit(5)
        )
        recent_news = recent_query.all()
        
        for i, (news, company) in enumerate(recent_news, 1):
            print(f"\n  {i}. [{company.name}] {news.title[:60]}...")
            print(f"     Категория: {news.category.value if news.category else 'N/A'}")
            print(f"     URL: {news.source_url[:80]}...")
            print(f"     Опубликовано: {news.published_at.strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    asyncio.run(analyze_news())

