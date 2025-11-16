#!/usr/bin/env python3
"""
Скрипт для обработки всех новостей компании через NLP.
Добавляет sentiment, topic, priority_score для новостей без этих полей.
"""

import asyncio
import sys
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models import NewsItem
from app.services.nlp_service import PIPELINE


async def process_company_news(company_id: UUID, limit: int = None):
    """Обработать все новости компании через NLP."""
    async for session in get_async_session():
        try:
            # Найти новости без sentiment или topic
            stmt = select(NewsItem).where(
                NewsItem.company_id == company_id,
                (NewsItem.sentiment.is_(None) | NewsItem.topic.is_(None))
            )
            
            if limit:
                stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            news_items = list(result.scalars().all())
            
            if not news_items:
                print(f"✅ Все новости компании {company_id} уже обработаны")
                return
            
            print(f"📰 Найдено {len(news_items)} новостей для обработки")
            print()
            
            processed = 0
            errors = 0
            
            for i, news in enumerate(news_items, 1):
                try:
                    print(f"[{i}/{len(news_items)}] Обработка: {news.title[:50]}...")
                    
                    # Классифицировать новость
                    result = await PIPELINE.classify_news(session, str(news.id))
                    
                    if result.get("sentiment") and result.get("priority_score"):
                        processed += 1
                        print(f"   ✅ sentiment={result.get('sentiment')}, topic={result.get('topic')}, priority={result.get('priority_score'):.2f}")
                    else:
                        print(f"   ⚠️  Результат: {result}")
                        
                except Exception as e:
                    errors += 1
                    print(f"   ❌ Ошибка: {e}")
                    continue
            
            print()
            print("=" * 60)
            print(f"✅ Обработано: {processed}/{len(news_items)}")
            if errors > 0:
                print(f"❌ Ошибок: {errors}")
            print("=" * 60)
            
        finally:
            await session.close()


async def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        print("Использование: python process_company_news_nlp.py <company_id> [limit]")
        print("Пример: python process_company_news_nlp.py 75eee989-a419-4220-bdc6-810c4854a1fe 100")
        sys.exit(1)
    
    try:
        company_id = UUID(sys.argv[1])
    except ValueError:
        print(f"❌ Неверный формат UUID: {sys.argv[1]}")
        sys.exit(1)
    
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    print()
    print("🔍 ОБРАБОТКА НОВОСТЕЙ ЧЕРЕЗ NLP")
    print(f"Компания: {company_id}")
    if limit:
        print(f"Лимит: {limit} новостей")
    print()
    
    await process_company_news(company_id, limit)


if __name__ == "__main__":
    asyncio.run(main())




