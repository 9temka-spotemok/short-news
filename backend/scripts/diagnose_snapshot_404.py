"""
Скрипт для диагностики проблемы 404 при запросе snapshot.

Использование:
    python -m scripts.diagnose_snapshot_404 <company_id> [period]

Пример:
    python -m scripts.diagnose_snapshot_404 75eee989-a419-4220-bdc6-810c4854a1fe daily
"""

import asyncio
import sys
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models import AnalyticsPeriod, CompanyAnalyticsSnapshot, Company


async def diagnose_snapshot_404(company_id_str: str, period_str: str = "daily"):
    """Проверяет все возможные причины 404 для snapshot."""
    
    try:
        company_id = UUID(company_id_str)
    except ValueError:
        print(f"❌ Неверный формат UUID: {company_id_str}")
        return
    
    try:
        period = AnalyticsPeriod(period_str.lower())
    except ValueError:
        print(f"❌ Неверный период: {period_str}. Должен быть: daily, weekly, monthly")
        return
    
    print(f"\n🔍 Диагностика snapshot 404")
    print(f"   Company ID: {company_id}")
    print(f"   Period: {period.value}")
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
                print(f"   💡 Решение: Убедитесь, что компания существует")
                return
            else:
                print(f"   ✅ Компания найдена: {company.name} (id={company.id})")
            
            # 2. Проверка существования snapshots
            print(f"\n2️⃣  Проверка существования snapshots для периода '{period.value}'...")
            snapshot_stmt = (
                select(CompanyAnalyticsSnapshot)
                .where(
                    CompanyAnalyticsSnapshot.company_id == company_id,
                    CompanyAnalyticsSnapshot.period == period.value,
                )
                .order_by(CompanyAnalyticsSnapshot.period_start.desc())
                .limit(5)
            )
            snapshot_result = await session.execute(snapshot_stmt)
            snapshots = list(snapshot_result.scalars().all())
            
            if not snapshots:
                print(f"   ⚠️  Snapshots для периода '{period.value}' НЕ НАЙДЕНЫ")
                print(f"   💡 Эндпоинт попытается создать snapshot автоматически")
            else:
                print(f"   ✅ Найдено snapshots: {len(snapshots)}")
                for i, snap in enumerate(snapshots, 1):
                    print(f"      {i}. ID={snap.id}, period_start={snap.period_start}, period_end={snap.period_end}")
            
            # 3. Проверка всех snapshots для компании (любой период)
            print(f"\n3️⃣  Проверка всех snapshots для компании (любой период)...")
            all_snapshots_stmt = (
                select(CompanyAnalyticsSnapshot)
                .where(CompanyAnalyticsSnapshot.company_id == company_id)
                .order_by(CompanyAnalyticsSnapshot.period_start.desc())
                .limit(10)
            )
            all_result = await session.execute(all_snapshots_stmt)
            all_snapshots = list(all_result.scalars().all())
            
            if not all_snapshots:
                print(f"   ⚠️  НЕТ snapshots для этой компании вообще")
            else:
                print(f"   ✅ Всего snapshots для компании: {len(all_snapshots)}")
                periods = {}
                for snap in all_snapshots:
                    periods[snap.period] = periods.get(snap.period, 0) + 1
                print(f"      По периодам: {periods}")
            
            # 4. Проверка структуры таблицы
            print(f"\n4️⃣  Проверка структуры таблицы...")
            table_check = await session.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'company_analytics_snapshots'
                    ORDER BY ordinal_position
                """)
            )
            columns = table_check.fetchall()
            if columns:
                print(f"   ✅ Таблица существует, колонок: {len(columns)}")
            else:
                print(f"   ❌ Таблица 'company_analytics_snapshots' НЕ НАЙДЕНА")
                print(f"   💡 Решение: Запустите миграции БД")
            
            # 5. Проверка индексов
            print(f"\n5️⃣  Проверка индексов...")
            index_check = await session.execute(
                text("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = 'company_analytics_snapshots'
                """)
            )
            indexes = index_check.fetchall()
            if indexes:
                print(f"   ✅ Индексы найдены: {len(indexes)}")
                for idx_name, idx_def in indexes:
                    print(f"      - {idx_name}")
            else:
                print(f"   ⚠️  Индексы не найдены (может быть нормально)")
            
            # 6. Рекомендации
            print(f"\n{'='*60}")
            print(f"📋 Рекомендации:")
            
            if not snapshots:
                print(f"   1. Snapshot не существует для периода '{period.value}'")
                print(f"      → Эндпоинт должен автоматически создать его")
                print(f"      → Проверьте логи сервера на наличие ошибок при создании")
            
            if not all_snapshots:
                print(f"   2. Для компании нет snapshots вообще")
                print(f"      → Запустите пересчет аналитики: POST /api/v2/analytics/companies/{company_id}/recompute")
            
            print(f"\n   3. Проверьте логи сервера при запросе:")
            print(f"      → Должны быть записи: 'get_latest_snapshot called'")
            print(f"      → Затем: 'SnapshotService.get_latest_snapshot result'")
            print(f"      → Если snapshot не найден: 'Snapshot not found, attempting to create automatically'")
            
            print(f"\n   4. Если snapshot создается, но все равно 404:")
            print(f"      → Проверьте ошибки при сохранении в БД")
            print(f"      → Проверьте права доступа к БД")
            print(f"      → Проверьте ограничения (constraints) в таблице")
            
        finally:
            await session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python -m scripts.diagnose_snapshot_404 <company_id> [period]")
        print("Пример: python -m scripts.diagnose_snapshot_404 75eee989-a419-4220-bdc6-810c4854a1fe daily")
        sys.exit(1)
    
    company_id = sys.argv[1]
    period = sys.argv[2] if len(sys.argv) > 2 else "daily"
    
    asyncio.run(diagnose_snapshot_404(company_id, period))




