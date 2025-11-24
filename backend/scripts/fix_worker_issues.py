#!/usr/bin/env python3
"""
Скрипт для комплексного исправления всех проблем в базе данных, связанных с worker сервисом.
Исправляет:
- Создает enum типы (newstopic, sentimentlabel)
- Добавляет колонки в news_items (topic, sentiment, raw_snapshot_url)
- Исправляет тип interested_categories с character varying[] на newscategory[]
- Проверяет валидность данных
- Выводит итоговую диагностику

Использование:
    # Локально:
    cd backend
    python scripts/fix_worker_issues.py
    
    # Или через модульный импорт:
    python -m scripts.fix_worker_issues
    
    # Через Railway CLI (из корня проекта):
    railway run --service web -- python scripts/fix_worker_issues.py
    
    # Или через модульный импорт:
    railway run --service web -- python -m scripts.fix_worker_issues
    
    # Или с переходом в директорию:
    railway run --service web -- sh -c "cd /app && python scripts/fix_worker_issues.py"
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from loguru import logger


async def create_enum_types(session):
    """Создать enum типы, если их нет."""
    logger.info("Проверка и создание enum типов...")
    
    # 1. Создать newstopic
    try:
        await session.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'newstopic') THEN
                    CREATE TYPE newstopic AS ENUM (
                        'product', 'strategy', 'finance', 'technology', 'security',
                        'research', 'community', 'talent', 'regulation', 'market', 'other'
                    );
                END IF;
            END $$;
        """))
        await session.commit()
        logger.success("✅ Enum type newstopic проверен/создан")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании newstopic: {e}")
        await session.rollback()
        return False
    
    # 2. Создать sentimentlabel
    try:
        await session.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sentimentlabel') THEN
                    CREATE TYPE sentimentlabel AS ENUM (
                        'positive', 'neutral', 'negative', 'mixed'
                    );
                END IF;
            END $$;
        """))
        await session.commit()
        logger.success("✅ Enum type sentimentlabel проверен/создан")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании sentimentlabel: {e}")
        await session.rollback()
        return False
    
    # 3. Проверить newscategory
    try:
        result = await session.execute(text("""
            SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'newscategory')
        """))
        exists = result.scalar()
        if exists:
            logger.success("✅ Enum type newscategory существует")
        else:
            logger.warning("⚠️  Enum type newscategory не найден (может вызвать ошибки)")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке newscategory: {e}")
        return False
    
    return True


async def add_news_items_columns(session):
    """Добавить колонки в news_items, если их нет."""
    logger.info("Проверка и добавление колонок в news_items...")
    
    columns_to_add = [
        ("topic", "newstopic", "ALTER TABLE news_items ADD COLUMN topic newstopic;"),
        ("sentiment", "sentimentlabel", "ALTER TABLE news_items ADD COLUMN sentiment sentimentlabel;"),
        ("raw_snapshot_url", "VARCHAR(1000)", "ALTER TABLE news_items ADD COLUMN raw_snapshot_url VARCHAR(1000);"),
    ]
    
    for column_name, column_type, alter_query in columns_to_add:
        try:
            # Проверить, существует ли колонка
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'news_items' 
                    AND column_name = :column_name
                )
            """), {"column_name": column_name})
            exists = result.scalar()
            
            if exists:
                logger.info(f"  ✅ Колонка {column_name} уже существует")
            else:
                # Добавить колонку
                await session.execute(text(alter_query))
                await session.commit()
                logger.success(f"  ✅ Колонка {column_name} добавлена")
        except Exception as e:
            logger.error(f"  ❌ Ошибка при работе с колонкой {column_name}: {e}")
            await session.rollback()
            return False
    
    return True


async def fix_interested_categories_type(session):
    """Исправить тип interested_categories с character varying[] на newscategory[]."""
    logger.info("Проверка и исправление типа interested_categories...")
    
    try:
        # Проверить текущий тип
        result = await session.execute(text("""
            SELECT 
                udt_name AS array_type,
                (SELECT typname FROM pg_type WHERE oid = (
                    SELECT typelem FROM pg_type WHERE typname = (
                        SELECT udt_name FROM information_schema.columns 
                        WHERE table_name = 'user_preferences' AND column_name = 'interested_categories'
                    )
                )) AS array_element_type
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'user_preferences' 
            AND column_name = 'interested_categories'
        """))
        row = result.first()
        
        if not row:
            logger.warning("⚠️  Колонка interested_categories не найдена")
            return True
        
        current_type, element_type = row
        
        if element_type == 'newscategory':
            logger.success("✅ Тип interested_categories уже правильный (newscategory[])")
            return True
        
        logger.info(f"  Текущий тип: {current_type} (элемент: {element_type})")
        logger.info("  Исправление типа на newscategory[]...")
        
        # Изменить тип
        await session.execute(text("""
            ALTER TABLE user_preferences 
            ALTER COLUMN interested_categories TYPE newscategory[] 
            USING interested_categories::text[]::newscategory[];
        """))
        await session.commit()
        logger.success("✅ Тип interested_categories исправлен на newscategory[]")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при исправлении типа interested_categories: {e}")
        await session.rollback()
        return False


async def validate_data(session):
    """Проверить валидность данных."""
    logger.info("Проверка валидности данных...")
    
    # 1. Проверить interested_categories
    try:
        result = await session.execute(text("""
            WITH user_categories AS (
                SELECT unnest(interested_categories) AS cat
                FROM user_preferences
                WHERE interested_categories IS NOT NULL
                AND array_length(interested_categories, 1) > 0
            )
            SELECT COUNT(*) 
            FROM user_categories uc
            WHERE NOT EXISTS (
                SELECT 1 FROM pg_enum e
                WHERE e.enumtypid = (SELECT oid FROM pg_type WHERE typname = 'newscategory')
                AND e.enumlabel = uc.cat::text
            )
        """))
        invalid_count = result.scalar()
        
        if invalid_count > 0:
            logger.warning(f"⚠️  Найдено {invalid_count} невалидных значений в interested_categories")
        else:
            logger.success("✅ Все значения в interested_categories валидны")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке interested_categories: {e}")
    
    # 2. Проверить topic
    try:
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM news_items ni
            WHERE ni.topic IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM pg_enum e
                WHERE e.enumtypid = (SELECT oid FROM pg_type WHERE typname = 'newstopic')
                AND e.enumlabel = ni.topic::text
            )
        """))
        invalid_count = result.scalar()
        
        if invalid_count > 0:
            logger.warning(f"⚠️  Найдено {invalid_count} невалидных значений в news_items.topic")
        else:
            logger.success("✅ Все значения в news_items.topic валидны")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке topic: {e}")
    
    # 3. Проверить sentiment
    try:
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM news_items ni
            WHERE ni.sentiment IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM pg_enum e
                WHERE e.enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sentimentlabel')
                AND e.enumlabel = ni.sentiment::text
            )
        """))
        invalid_count = result.scalar()
        
        if invalid_count > 0:
            logger.warning(f"⚠️  Найдено {invalid_count} невалидных значений в news_items.sentiment")
        else:
            logger.success("✅ Все значения в news_items.sentiment валидны")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке sentiment: {e}")


async def run_diagnostics(session):
    """Выполнить итоговую диагностику."""
    logger.info("\n" + "=" * 50)
    logger.info("ИТОГОВАЯ ДИАГНОСТИКА")
    logger.info("=" * 50)
    
    diagnostics = []
    
    # 1. Колонки news_items
    try:
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'news_items' 
            AND column_name IN ('topic', 'sentiment', 'raw_snapshot_url')
        """))
        count = result.scalar()
        status = "✅ OK (3/3)" if count == 3 else f"❌ ERROR ({count}/3)"
        diagnostics.append(f"1. Колонки news_items: {status}")
    except Exception as e:
        diagnostics.append(f"1. Колонки news_items: ❌ ERROR ({e})")
    
    # 2. Тип interested_categories
    try:
        result = await session.execute(text("""
            SELECT typname FROM pg_type WHERE oid = (
                SELECT typelem FROM pg_type WHERE typname = (
                    SELECT udt_name FROM information_schema.columns 
                    WHERE table_name = 'user_preferences' AND column_name = 'interested_categories'
                )
            )
        """))
        element_type = result.scalar()
        status = "✅ OK (newscategory[])" if element_type == 'newscategory' else f"❌ ERROR ({element_type})"
        diagnostics.append(f"2. Тип interested_categories: {status}")
    except Exception as e:
        diagnostics.append(f"2. Тип interested_categories: ❌ ERROR ({e})")
    
    # 3. Оператор @>
    try:
        result = await session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM user_preferences 
                WHERE interested_categories @> ARRAY['product_update'::newscategory]
                LIMIT 1
            ) OR NOT EXISTS (
                SELECT 1 FROM user_preferences 
                WHERE interested_categories IS NOT NULL 
                AND array_length(interested_categories, 1) > 0
            )
        """))
        works = result.scalar()
        status = "✅ OK" if works else "❌ ERROR"
        diagnostics.append(f"3. Оператор @> работает: {status}")
    except Exception as e:
        diagnostics.append(f"3. Оператор @> работает: ❌ ERROR ({e})")
    
    # 4. Enum типы
    try:
        result = await session.execute(text("""
            SELECT COUNT(*) FROM pg_type 
            WHERE typname IN ('newscategory', 'newstopic', 'sentimentlabel')
        """))
        count = result.scalar()
        status = "✅ OK (3/3)" if count == 3 else f"❌ ERROR ({count}/3)"
        diagnostics.append(f"4. Enum типы: {status}")
    except Exception as e:
        diagnostics.append(f"4. Enum типы: ❌ ERROR ({e})")
    
    # Вывести все диагностики
    for diag in diagnostics:
        logger.info(diag)
    
    # Итоговый статус
    all_ok = all("✅" in d for d in diagnostics)
    if all_ok:
        logger.success("\n✅ ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ УСПЕШНО")
        return True
    else:
        logger.warning("\n⚠️  ТРЕБУЮТСЯ ДОПОЛНИТЕЛЬНЫЕ ИСПРАВЛЕНИЯ")
        return False


async def check_all_fixes_applied(session) -> bool:
    """Проверить, применены ли все исправления."""
    try:
        # Проверить enum типы
        result = await session.execute(text("""
            SELECT COUNT(*) FROM pg_type 
            WHERE typname IN ('newscategory', 'newstopic', 'sentimentlabel')
        """))
        enum_count = result.scalar()
        
        # Проверить колонки
        result = await session.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'news_items' 
            AND column_name IN ('topic', 'sentiment', 'raw_snapshot_url')
        """))
        columns_count = result.scalar()
        
        # Проверить тип interested_categories
        result = await session.execute(text("""
            SELECT typname FROM pg_type WHERE oid = (
                SELECT typelem FROM pg_type WHERE typname = (
                    SELECT udt_name FROM information_schema.columns 
                    WHERE table_name = 'user_preferences' AND column_name = 'interested_categories'
                )
            )
        """))
        element_type = result.scalar()
        
        return (enum_count == 3 and 
                columns_count == 3 and 
                element_type == 'newscategory')
    except Exception as e:
        logger.warning(f"Ошибка при проверке статуса: {e}")
        return False


async def main():
    """Основная функция."""
    logger.info("=" * 50)
    logger.info("ПРОВЕРКА И ИСПРАВЛЕНИЕ ПРОБЛЕМ WORKER СЕРВИСА")
    logger.info("=" * 50)
    logger.info(f"Рабочая директория: {Path.cwd()}")
    logger.info(f"Путь к скрипту: {Path(__file__).resolve()}")
    logger.info("")
    
    async with AsyncSessionLocal() as session:
        # Сначала проверить, применены ли все исправления
        logger.info("Проверка текущего статуса...")
        all_applied = await check_all_fixes_applied(session)
        
        if all_applied:
            logger.success("\n✅ ВСЕ SQL ИСПРАВЛЕНИЯ УЖЕ ПРИМЕНЕНЫ!")
            logger.info("\nВыполняю финальную диагностику...")
            await run_diagnostics(session)
            logger.info("\n⚠️  ВАЖНО: Проблема с event loop исправляется в коде Python.")
            logger.info("   Убедитесь, что изменения в backend/app/tasks/digest.py задеплоены")
            logger.info("   и worker сервис перезапущен.")
            return 0
        
        logger.info("⚠️  Обнаружены проблемы, применяю исправления...\n")
        
        success = True
        
        # 1. Создать enum типы
        if not await create_enum_types(session):
            success = False
        
        # 2. Добавить колонки в news_items
        if not await add_news_items_columns(session):
            success = False
        
        # 3. Исправить тип interested_categories
        if not await fix_interested_categories_type(session):
            success = False
        
        # 4. Проверить валидность данных
        await validate_data(session)
        
        # 5. Выполнить диагностику
        diagnostics_ok = await run_diagnostics(session)
        
        if success and diagnostics_ok:
            logger.success("\n✅ Все исправления применены успешно!")
            logger.info("\n⚠️  ВАЖНО: Проблема с event loop исправляется в коде Python.")
            logger.info("   Необходимо задеплоить изменения в backend/app/tasks/digest.py")
            logger.info("   и перезапустить worker сервис.")
            return 0
        else:
            logger.error("\n❌ Некоторые исправления не были применены.")
            logger.error("   Проверьте логи выше для деталей.")
            return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

