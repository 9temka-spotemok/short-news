#!/usr/bin/env python3
"""
Диагностический скрипт для проверки системы аналитики.
Проверяет инфраструктуру, данные и готовность к пересчёту.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models import (
    Company,
    CompanyAnalyticsSnapshot,
    NewsItem,
    CompetitorChangeEvent,
    ChangeProcessingStatus,
    AnalyticsPeriod,
)


async def check_infrastructure():
    """Проверка инфраструктуры (Redis, Celery)."""
    print("=" * 60)
    print("🔧 ПРОВЕРКА ИНФРАСТРУКТУРЫ")
    print("=" * 60)
    
    try:
        from redis import Redis
        from app.core.config import settings
        
        redis_client = Redis.from_url(settings.CELERY_BROKER_URL or "redis://localhost:6379/0")
        result = redis_client.ping()
        if result:
            print("✅ Redis доступен")
        else:
            print("❌ Redis не отвечает")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        return False
    
    print("⚠️  Проверка Celery worker требует запуска команды:")
    print("   celery -A app.celery_app inspect active")
    print()
    return True


async def check_company_data(session: AsyncSession, company_id: UUID):
    """Проверка данных для компании."""
    print("=" * 60)
    print(f"📊 ПРОВЕРКА ДАННЫХ ДЛЯ КОМПАНИИ {company_id}")
    print("=" * 60)
    
    # Проверка существования компании
    company_result = await session.execute(select(Company).where(Company.id == company_id))
    company = company_result.scalar_one_or_none()
    
    if not company:
        print(f"❌ Компания {company_id} не найдена в БД")
        return False
    
    print(f"✅ Компания найдена: {company.name}")
    print()
    
    # Проверка новостей
    news_count_result = await session.execute(
        select(func.count(NewsItem.id)).where(NewsItem.company_id == company_id)
    )
    news_count = news_count_result.scalar_one()
    
    news_with_sentiment_result = await session.execute(
        select(func.count(NewsItem.id)).where(
            NewsItem.company_id == company_id,
            NewsItem.sentiment.isnot(None)
        )
    )
    news_with_sentiment = news_with_sentiment_result.scalar_one()
    
    news_with_priority_result = await session.execute(
        select(func.count(NewsItem.id)).where(
            NewsItem.company_id == company_id,
            NewsItem.priority_score.isnot(None)
        )
    )
    news_with_priority = news_with_priority_result.scalar_one()
    
    print(f"📰 Новости:")
    print(f"   Всего: {news_count}")
    print(f"   С sentiment: {news_with_sentiment}")
    print(f"   С priority_score: {news_with_priority}")
    
    if news_count == 0:
        print("   ⚠️  Нет новостей для компании")
    elif news_with_sentiment < news_count * 0.8:
        print("   ⚠️  Многие новости без sentiment (нужна NLP обработка)")
    else:
        print("   ✅ Новости готовы для аналитики")
    print()
    
    # Проверка change events
    change_events_count_result = await session.execute(
        select(func.count(CompetitorChangeEvent.id)).where(
            CompetitorChangeEvent.company_id == company_id
        )
    )
    change_events_count = change_events_count_result.scalar_one()
    
    change_events_success_result = await session.execute(
        select(func.count(CompetitorChangeEvent.id)).where(
            CompetitorChangeEvent.company_id == company_id,
            CompetitorChangeEvent.processing_status == ChangeProcessingStatus.SUCCESS
        )
    )
    change_events_success = change_events_success_result.scalar_one()
    
    print(f"🔄 Change Events:")
    print(f"   Всего: {change_events_count}")
    print(f"   Со статусом SUCCESS: {change_events_success}")
    
    if change_events_success == 0:
        print("   ⚠️  Нет успешно обработанных change events")
    else:
        print("   ✅ Change events готовы для аналитики")
    print()
    
    return True


async def check_snapshots(session: AsyncSession, company_id: UUID):
    """Проверка существующих snapshots."""
    print("=" * 60)
    print(f"📸 ПРОВЕРКА SNAPSHOTS")
    print("=" * 60)
    
    # Проверка snapshots по периодам
    for period in [AnalyticsPeriod.DAILY, AnalyticsPeriod.WEEKLY, AnalyticsPeriod.MONTHLY]:
        snapshot_result = await session.execute(
            select(func.count(CompanyAnalyticsSnapshot.id)).where(
                CompanyAnalyticsSnapshot.company_id == company_id,
                CompanyAnalyticsSnapshot.period == period.value
            )
        )
        count = snapshot_result.scalar_one()
        
        if count > 0:
            # Получить последний snapshot
            latest_result = await session.execute(
                select(CompanyAnalyticsSnapshot)
                .where(
                    CompanyAnalyticsSnapshot.company_id == company_id,
                    CompanyAnalyticsSnapshot.period == period.value
                )
                .order_by(CompanyAnalyticsSnapshot.period_start.desc())
                .limit(1)
            )
            latest = latest_result.scalar_one_or_none()
            
            if latest:
                print(f"✅ {period.value.upper()}: {count} snapshots")
                print(f"   Последний: {latest.period_start.date()} - impact_score: {latest.impact_score:.2f}")
                print(f"   Новости: {latest.news_total}, Pricing: {latest.pricing_changes}, Features: {latest.feature_updates}")
        else:
            print(f"❌ {period.value.upper()}: нет snapshots")
        print()
    
    return True


async def check_recent_data(session: AsyncSession, company_id: UUID):
    """Проверка свежести данных."""
    print("=" * 60)
    print("📅 ПРОВЕРКА СВЕЖЕСТИ ДАННЫХ")
    print("=" * 60)
    
    now = datetime.now(timezone.utc)
    last_30_days = now - timedelta(days=30)
    
    # Новости за последние 30 дней
    recent_news_result = await session.execute(
        select(func.count(NewsItem.id)).where(
            NewsItem.company_id == company_id,
            NewsItem.published_at >= last_30_days.replace(tzinfo=None)
        )
    )
    recent_news = recent_news_result.scalar_one()
    
    print(f"📰 Новости за последние 30 дней: {recent_news}")
    
    # Change events за последние 30 дней
    recent_events_result = await session.execute(
        select(func.count(CompetitorChangeEvent.id)).where(
            CompetitorChangeEvent.company_id == company_id,
            CompetitorChangeEvent.detected_at >= last_30_days.replace(tzinfo=None),
            CompetitorChangeEvent.processing_status == ChangeProcessingStatus.SUCCESS
        )
    )
    recent_events = recent_events_result.scalar_one()
    
    print(f"🔄 Change events за последние 30 дней: {recent_events}")
    print()
    
    if recent_news == 0 and recent_events == 0:
        print("⚠️  Нет свежих данных за последние 30 дней")
        print("   Snapshot будет создан с нулевыми значениями")
    elif recent_news > 0 or recent_events > 0:
        print("✅ Есть свежие данные для создания snapshot")
    
    return True


async def main():
    """Главная функция диагностики."""
    if len(sys.argv) < 2:
        print("Использование: python diagnose_analytics.py <company_id>")
        print("Пример: python diagnose_analytics.py 75eee989-a419-4220-bdc6-810c4854a1fe")
        sys.exit(1)
    
    try:
        company_id = UUID(sys.argv[1])
    except ValueError:
        print(f"❌ Неверный формат UUID: {sys.argv[1]}")
        sys.exit(1)
    
    print()
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ АНАЛИТИКИ")
    print()
    
    # Проверка инфраструктуры
    infra_ok = await check_infrastructure()
    if not infra_ok:
        print("❌ Проблемы с инфраструктурой. Исправьте их перед продолжением.")
        return
    
    # Проверка данных
    async for session in get_async_session():
        try:
            await check_company_data(session, company_id)
            await check_snapshots(session, company_id)
            await check_recent_data(session, company_id)
            
            print("=" * 60)
            print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
            print("=" * 60)
            print()
            print("📋 РЕКОМЕНДАЦИИ:")
            print()
            print("1. Если нет snapshots - запустите пересчёт:")
            print(f"   POST /api/v2/analytics/companies/{company_id}/recompute?period=daily&lookback=60")
            print()
            print("2. Если нет новостей - запустите скрейпер для компании")
            print()
            print("3. Если нет change events - проверьте обработку изменений конкурентов")
            print()
            print("4. Проверьте логи Celery worker:")
            print("   docker logs shot-news-celery-worker --tail=50")
            print()
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(main())




