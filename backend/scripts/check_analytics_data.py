"""
Скрипт для проверки данных аналитики.

Использование:
    python -m scripts.check_analytics_data <company_id>

Пример:
    python -m scripts.check_analytics_data 75eee989-a419-4220-bdc6-810c4854a1fe
"""

import asyncio
import sys
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models import (
    Company,
    CompanyAnalyticsSnapshot,
    NewsItem,
    CompetitorChangeEvent,
    AnalyticsGraphEdge,
)


async def check_analytics_data(company_id_str: str):
    """Проверяет данные аналитики для компании."""
    
    try:
        company_id = UUID(company_id_str)
    except ValueError:
        print(f"❌ Неверный формат UUID: {company_id_str}")
        return
    
    print(f"\n🔍 Проверка данных аналитики")
    print(f"   Company ID: {company_id}")
    print(f"{'='*60}\n")
    
    async for session in get_async_session():
        try:
            # 1. Проверка существования компании
            print("1️⃣  Проверка существования компании...")
            company_stmt = select(Company).where(Company.id == company_id)
            company_result = await session.execute(company_stmt)
            company = company_result.scalar_one_or_none()
            
            if not company:
                print(f"   ❌ Компания с ID {company_id} НЕ НАЙДЕНА в БД")
                return
            else:
                print(f"   ✅ Компания найдена: {company.name} (id={company.id})")
            
            # 2. Проверка новостей
            print(f"\n2️⃣  Проверка новостей для компании...")
            news_stmt = select(func.count(NewsItem.id)).where(NewsItem.company_id == company_id)
            news_result = await session.execute(news_stmt)
            news_count = news_result.scalar_one() or 0
            
            if news_count == 0:
                print(f"   ⚠️  Нет новостей для компании")
                print(f"   💡 Решение: Запустите скрейпер для компании")
            else:
                print(f"   ✅ Найдено новостей: {news_count}")
                
                # Проверка новостей за последние дни
                from datetime import datetime, timedelta, timezone
                now = datetime.now(tz=timezone.utc)
                yesterday = now - timedelta(days=1)
                
                recent_news_stmt = (
                    select(func.count(NewsItem.id))
                    .where(
                        NewsItem.company_id == company_id,
                        NewsItem.published_at >= yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                    )
                )
                recent_news_result = await session.execute(recent_news_stmt)
                recent_news_count = recent_news_result.scalar_one() or 0
                print(f"      Новостей за последние 24 часа: {recent_news_count}")
            
            # 3. Проверка событий
            print(f"\n3️⃣  Проверка событий для компании...")
            events_stmt = select(func.count(CompetitorChangeEvent.id)).where(
                CompetitorChangeEvent.company_id == company_id
            )
            events_result = await session.execute(events_stmt)
            events_count = events_result.scalar_one() or 0
            
            if events_count == 0:
                print(f"   ⚠️  Нет событий для компании")
            else:
                print(f"   ✅ Найдено событий: {events_count}")
            
            # 4. Проверка snapshots
            print(f"\n4️⃣  Проверка snapshots для компании...")
            snapshots_stmt = (
                select(CompanyAnalyticsSnapshot)
                .where(CompanyAnalyticsSnapshot.company_id == company_id)
                .order_by(CompanyAnalyticsSnapshot.period_start.desc())
                .limit(10)
            )
            snapshots_result = await session.execute(snapshots_stmt)
            snapshots = list(snapshots_result.scalars().all())
            
            if not snapshots:
                print(f"   ⚠️  Нет snapshots для компании")
                print(f"   💡 Решение: Запустите пересчет аналитики:")
                print(f"      POST /api/v2/analytics/companies/{company_id}/recompute?period=daily&lookback=30")
            else:
                print(f"   ✅ Найдено snapshots: {len(snapshots)}")
                
                # Группировка по периодам
                periods = {}
                for snap in snapshots:
                    period = snap.period
                    if period not in periods:
                        periods[period] = []
                    periods[period].append(snap)
                
                for period, period_snapshots in periods.items():
                    print(f"      {period}: {len(period_snapshots)} snapshots")
                    latest = period_snapshots[0]
                    print(f"         Последний: {latest.period_start} (id={latest.id})")
            
            # 5. Проверка графовых ребер
            print(f"\n5️⃣  Проверка графовых ребер для компании...")
            edges_stmt = (
                select(func.count(AnalyticsGraphEdge.id))
                .where(AnalyticsGraphEdge.company_id == company_id)
            )
            edges_result = await session.execute(edges_stmt)
            edges_count = edges_result.scalar_one() or 0
            
            if edges_count == 0:
                print(f"   ⚠️  Нет графовых ребер для компании")
                print(f"   💡 Решение: Запустите синхронизацию графа:")
                print(f"      POST /api/v2/analytics/companies/{company_id}/graph/sync")
            else:
                print(f"   ✅ Найдено графовых ребер: {edges_count}")
            
            # 6. Рекомендации
            print(f"\n{'='*60}")
            print(f"📋 Рекомендации:")
            
            if news_count == 0:
                print(f"   1. ❌ Нет новостей для компании")
                print(f"      → Запустите скрейпер для компании")
            
            if not snapshots:
                print(f"   2. ❌ Нет snapshots для компании")
                print(f"      → Запустите пересчет аналитики:")
                print(f"        POST /api/v2/analytics/companies/{company_id}/recompute?period=daily&lookback=30")
            
            if news_count > 0 and not snapshots:
                print(f"   3. ⚠️  Есть новости, но нет snapshots")
                print(f"      → Возможно, есть проблема с автоматическим созданием snapshot")
                print(f"      → Проверьте логи сервера при запросе /impact/latest")
            
            if edges_count == 0 and news_count > 0:
                print(f"   4. ⚠️  Есть новости, но нет графовых ребер")
                print(f"      → Запустите синхронизацию графа")
            
            if news_count > 0 and snapshots:
                print(f"   ✅ Данные аналитики выглядят нормально")
                print(f"   💡 Если фронтенд получает пустые данные, проверьте:")
                print(f"      → Правильность company_id в запросах")
                print(f"      → Логи сервера на наличие ошибок")
            
        finally:
            await session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python -m scripts.check_analytics_data <company_id>")
        print("Пример: python -m scripts.check_analytics_data 75eee989-a419-4220-bdc6-810c4854a1fe")
        sys.exit(1)
    
    company_id = sys.argv[1]
    asyncio.run(check_analytics_data(company_id))




