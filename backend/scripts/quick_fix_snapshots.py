"""
Быстрый скрипт для запуска пересчёта аналитики и создания snapshots.
"""
import asyncio
import sys
from uuid import UUID
from app.core.database import get_async_session
from app.domains.analytics import AnalyticsFacade
from app.models import AnalyticsPeriod
from sqlalchemy import select
from app.models import Company


async def recompute_analytics_for_company(company_id: UUID, period: AnalyticsPeriod = AnalyticsPeriod.DAILY, lookback: int = 60):
    """Запустить пересчёт аналитики для компании"""
    async for session in get_async_session():
        try:
            facade = AnalyticsFacade(session)
            
            print(f"🔄 Запуск пересчёта аналитики для компании {company_id}...")
            print(f"   Period: {period.value}, Lookback: {lookback} дней")
            
            snapshots = await facade.refresh_company_snapshots(
                company_id=company_id,
                period=period,
                lookback=lookback
            )
            
            print(f"✅ Создано snapshots: {len(snapshots)}")
            
            if snapshots:
                latest = snapshots[-1]
                print(f"   Latest snapshot:")
                print(f"   - Period: {latest.period.value}")
                print(f"   - Start: {latest.period_start}")
                print(f"   - Impact Score: {latest.impact_score:.2f}")
                print(f"   - Trend Delta: {latest.trend_delta:.2f}")
            
            await session.commit()
            return snapshots
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка при пересчёте: {e}")
            raise
        finally:
            await session.close()


async def recompute_all_companies(period: AnalyticsPeriod = AnalyticsPeriod.DAILY, lookback: int = 30, limit: int = None):
    """Запустить пересчёт для всех компаний"""
    async for session in get_async_session():
        try:
            stmt = select(Company.id, Company.name)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            companies = result.all()
            
            print(f"📊 Найдено компаний: {len(companies)}")
            
            facade = AnalyticsFacade(session)
            
            for company_id, company_name in companies:
                try:
                    print(f"\n🔄 Обработка: {company_name} ({company_id})")
                    snapshots = await facade.refresh_company_snapshots(
                        company_id=company_id,
                        period=period,
                        lookback=lookback
                    )
                    print(f"   ✅ Создано snapshots: {len(snapshots)}")
                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")
                    continue
            
            await session.commit()
        finally:
            await session.close()


async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python quick_fix_snapshots.py <company_id> [period] [lookback]")
        print("  python quick_fix_snapshots.py all [period] [lookback] [limit]")
        print("\nПримеры:")
        print("  python quick_fix_snapshots.py 75eee989-a419-4220-bdc6-810c4854a1fe")
        print("  python quick_fix_snapshots.py 75eee989-a419-4220-bdc6-810c4854a1fe daily 60")
        print("  python quick_fix_snapshots.py all daily 30 10")
        sys.exit(1)
    
    company_arg = sys.argv[1]
    period_str = sys.argv[2] if len(sys.argv) > 2 else "daily"
    lookback = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    try:
        period = AnalyticsPeriod(period_str.lower())
    except ValueError:
        print(f"❌ Неверный period: {period_str}. Допустимые: daily, weekly, monthly")
        sys.exit(1)
    
    if company_arg.lower() == "all":
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
        await recompute_all_companies(period=period, lookback=lookback, limit=limit)
    else:
        try:
            company_id = UUID(company_arg)
        except ValueError:
            print(f"❌ Неверный UUID компании: {company_arg}")
            sys.exit(1)
        
        await recompute_analytics_for_company(company_id, period=period, lookback=lookback)


if __name__ == "__main__":
    asyncio.run(main())




