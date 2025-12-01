"""
Диагностический скрипт для проверки персонализации.

Проверяет:
1. Есть ли у пользователя компании в БД
2. Есть ли новости для этих компаний
3. Правильно ли работает фильтрация
4. Проблемы с типами данных (UUID vs string)

Использование:
    poetry run python scripts/diagnose_personalization.py <user_email>
"""

import sys
import asyncio
from pathlib import Path
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_async_session
from app.models import User, Company, NewsItem
from app.core.access_control import get_user_company_ids


async def diagnose_user_personalization(email: str):
    """Диагностика персонализации для конкретного пользователя."""
    async for db in get_async_session():
        try:
            print(f"\n{'='*80}")
            print(f"🔍 Диагностика персонализации для пользователя: {email}")
            print(f"{'='*80}\n")
            
            # 1. Найти пользователя
            user_result = await db.execute(
                select(User).where(User.email == email)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                print(f"❌ Пользователь {email} не найден")
                return
            
            print(f"✅ Пользователь найден:")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Активен: {'Да' if user.is_active else 'Нет'}")
            
            # 2. Получить компании пользователя через access_control
            print(f"\n📋 Проверка компаний через get_user_company_ids():")
            company_ids = await get_user_company_ids(user, db)
            print(f"   Количество компаний: {len(company_ids)}")
            if company_ids:
                print(f"   Company IDs (UUID): {[str(cid) for cid in company_ids]}")
                print(f"   Company IDs (типы): {[type(cid).__name__ for cid in company_ids]}")
            else:
                print(f"   ⚠️ У пользователя нет компаний!")
                print(f"   💡 Решение: Пользователь должен пройти онбординг или создать компании")
            
            # 3. Проверить компании напрямую в БД
            print(f"\n📋 Проверка компаний напрямую в БД:")
            companies_result = await db.execute(
                select(Company).where(Company.user_id == user.id)
            )
            companies = companies_result.scalars().all()
            print(f"   Количество компаний в БД: {len(companies)}")
            for company in companies:
                print(f"   - {company.name} (ID: {company.id}, user_id: {company.user_id})")
            
            if len(companies) != len(company_ids):
                print(f"   ⚠️ ПРОБЛЕМА: Несоответствие количества компаний!")
                print(f"      get_user_company_ids вернул: {len(company_ids)}")
                print(f"      Прямой запрос вернул: {len(companies)}")
            
            # 4. Проверить новости для этих компаний
            if company_ids:
                print(f"\n📰 Проверка новостей для компаний пользователя:")
                
                # Конвертируем UUID в строки для сравнения
                company_ids_str = [str(cid) for cid in company_ids]
                
                # Проверка 1: через UUID
                news_count_uuid = await db.execute(
                    select(func.count(NewsItem.id))
                    .where(NewsItem.company_id.in_(company_ids))
                )
                count_uuid = news_count_uuid.scalar() or 0
                print(f"   Новостей (фильтр по UUID): {count_uuid}")
                
                # Проверка 2: через строки (как в репозитории)
                uuid_ids = [UUID(cid) for cid in company_ids_str]
                news_count_str = await db.execute(
                    select(func.count(NewsItem.id))
                    .where(NewsItem.company_id.in_(uuid_ids))
                )
                count_str = news_count_str.scalar() or 0
                print(f"   Новостей (фильтр по строкам→UUID): {count_str}")
                
                # Проверка 3: детальный список
                news_result = await db.execute(
                    select(NewsItem, Company.name)
                    .join(Company, NewsItem.company_id == Company.id)
                    .where(NewsItem.company_id.in_(company_ids))
                    .limit(10)
                )
                news_items = news_result.all()
                print(f"   Первые 10 новостей:")
                if news_items:
                    for news, company_name in news_items:
                        print(f"   - {news.title[:50]}... (Company: {company_name}, ID: {news.company_id})")
                else:
                    print(f"   - Новостей не найдено")
                
                if count_uuid == 0 and count_str == 0:
                    print(f"\n   ⚠️ ПРОБЛЕМА: У компаний пользователя нет новостей!")
                    print(f"   Возможные причины:")
                    print(f"   1. Новости еще не собраны для этих компаний (scraper не работал)")
                    print(f"   2. company_id в news_items не совпадает с ID компаний")
                    print(f"   3. Новости привязаны к другим компаниям")
                    print(f"   4. Проблема с типами данных (UUID vs string)")
                elif count_uuid != count_str:
                    print(f"\n   ⚠️ ПРОБЛЕМА: Несоответствие результатов фильтрации!")
                    print(f"      UUID фильтр: {count_uuid}")
                    print(f"      String→UUID фильтр: {count_str}")
            else:
                print(f"\n   ⚠️ Невозможно проверить новости - у пользователя нет компаний")
            
            # 5. Проверить глобальные компании
            print(f"\n🌐 Проверка глобальных компаний:")
            global_companies_result = await db.execute(
                select(Company).where(Company.user_id.is_(None))
            )
            global_companies = global_companies_result.scalars().all()
            print(f"   Количество глобальных компаний: {len(global_companies)}")
            
            if global_companies:
                global_company_ids = [c.id for c in global_companies]
                global_news_count = await db.execute(
                    select(func.count(NewsItem.id))
                    .where(NewsItem.company_id.in_(global_company_ids))
                )
                count = global_news_count.scalar() or 0
                print(f"   Новостей от глобальных компаний: {count}")
            
            # 6. Проверить все новости в системе
            print(f"\n📊 Общая статистика:")
            all_news_count = await db.execute(
                select(func.count(NewsItem.id))
            )
            total_news = all_news_count.scalar() or 0
            print(f"   Всего новостей в системе: {total_news}")
            
            # Новости без компании
            news_without_company = await db.execute(
                select(func.count(NewsItem.id))
                .where(NewsItem.company_id.is_(None))
            )
            count_no_company = news_without_company.scalar() or 0
            print(f"   Новостей без компании: {count_no_company}")
            
            # 7. Рекомендации
            print(f"\n💡 Рекомендации:")
            if len(company_ids) == 0:
                print(f"   1. Пользователь должен пройти онбординг для создания компаний")
                print(f"   2. Или создать компании вручную через API /companies/")
            elif count_uuid == 0:
                print(f"   1. Запустить scraper для сбора новостей по компаниям пользователя")
                print(f"   2. Проверить, что company_id в news_items совпадает с ID компаний")
                print(f"   3. Проверить логи scraper на наличие ошибок")
            else:
                print(f"   ✅ Всё выглядит нормально! У пользователя есть компании и новости.")
            
            print(f"\n{'='*80}\n")
            
            break
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: poetry run python scripts/diagnose_personalization.py <user_email>")
        print("Пример: poetry run python scripts/diagnose_personalization.py user@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    asyncio.run(diagnose_user_personalization(email))




