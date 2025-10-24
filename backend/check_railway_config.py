#!/usr/bin/env python3
"""
Railway Configuration Checker
Проверяет конфигурацию для развертывания на Railway
"""

import os
import sys
import asyncio
import httpx
from urllib.parse import urlparse

def check_environment_variables():
    """Проверяет наличие обязательных переменных окружения"""
    print("🔍 Проверка переменных окружения...")
    
    required_vars = [
        "SECRET_KEY",
        "DATABASE_URL", 
        "REDIS_URL",
        "ENVIRONMENT"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ Все обязательные переменные присутствуют")
        return True

def check_database_url():
    """Проверяет формат DATABASE_URL"""
    print("\n🔍 Проверка DATABASE_URL...")
    
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL не установлена")
        return False
    
    try:
        parsed = urlparse(db_url)
        if parsed.scheme != "postgresql":
            print(f"❌ Неверная схема в DATABASE_URL: {parsed.scheme}")
            return False
        
        if not parsed.hostname:
            print("❌ Отсутствует hostname в DATABASE_URL")
            return False
            
        print("✅ DATABASE_URL имеет правильный формат")
        return True
    except Exception as e:
        print(f"❌ Ошибка парсинга DATABASE_URL: {e}")
        return False

def check_redis_url():
    """Проверяет формат REDIS_URL"""
    print("\n🔍 Проверка REDIS_URL...")
    
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL не установлена")
        return False
    
    try:
        parsed = urlparse(redis_url)
        if parsed.scheme not in ["redis", "rediss"]:
            print(f"❌ Неверная схема в REDIS_URL: {parsed.scheme}")
            return False
        
        if not parsed.hostname:
            print("❌ Отсутствует hostname в REDIS_URL")
            return False
            
        print("✅ REDIS_URL имеет правильный формат")
        return True
    except Exception as e:
        print(f"❌ Ошибка парсинга REDIS_URL: {e}")
        return False

async def check_database_connection():
    """Проверяет подключение к базе данных"""
    print("\n🔍 Проверка подключения к базе данных...")
    
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL не установлена")
        return False
    
    try:
        # Импортируем здесь, чтобы избежать ошибок если модули не установлены
        from sqlalchemy import create_engine, text
        
        # Создаем синхронный engine для проверки
        engine = create_engine(db_url.replace("postgresql+asyncpg://", "postgresql://"))
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print("✅ Подключение к базе данных успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False

async def check_redis_connection():
    """Проверяет подключение к Redis"""
    print("\n🔍 Проверка подключения к Redis...")
    
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL не установлена")
        return False
    
    try:
        import redis
        
        # Парсим URL для создания клиента
        parsed = urlparse(redis_url)
        
        client = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            password=parsed.password,
            db=int(parsed.path.lstrip('/')) if parsed.path else 0,
            decode_responses=True
        )
        
        # Проверяем подключение
        client.ping()
        
        print("✅ Подключение к Redis успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        return False

def check_port_configuration():
    """Проверяет конфигурацию порта"""
    print("\n🔍 Проверка конфигурации порта...")
    
    port = os.environ.get("PORT")
    if not port:
        print("❌ Переменная PORT не установлена")
        return False
    
    try:
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            print(f"❌ Неверный номер порта: {port_num}")
            return False
        
        print(f"✅ Порт настроен правильно: {port_num}")
        return True
        
    except ValueError:
        print(f"❌ Неверный формат порта: {port}")
        return False

def check_cors_configuration():
    """Проверяет конфигурацию CORS"""
    print("\n🔍 Проверка конфигурации CORS...")
    
    allowed_hosts = os.environ.get("ALLOWED_HOSTS")
    if not allowed_hosts:
        print("⚠️  ALLOWED_HOSTS не установлена (будет использоваться значение по умолчанию)")
        return True
    
    try:
        # Парсим JSON список
        import json
        hosts = json.loads(allowed_hosts)
        
        if not isinstance(hosts, list):
            print("❌ ALLOWED_HOSTS должна быть списком")
            return False
        
        print(f"✅ CORS настроен для {len(hosts)} хостов")
        return True
        
    except json.JSONDecodeError:
        print("❌ Неверный формат ALLOWED_HOSTS (должен быть JSON список)")
        return False

def print_railway_info():
    """Выводит информацию о Railway"""
    print("\n📋 Информация о Railway:")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'не установлено')}")
    print(f"Debug: {os.environ.get('DEBUG', 'не установлено')}")
    print(f"Port: {os.environ.get('PORT', 'не установлено')}")
    
    # Маскируем чувствительные данные
    db_url = os.environ.get('DATABASE_URL', 'не установлено')
    if db_url != 'не установлено':
        import re
        masked_db = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', db_url)
        print(f"Database URL: {masked_db}")
    
    redis_url = os.environ.get('REDIS_URL', 'не установлено')
    if redis_url != 'не установлено':
        import re
        masked_redis = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', redis_url)
        print(f"Redis URL: {masked_redis}")

async def main():
    """Основная функция проверки"""
    print("🚀 Railway Configuration Checker")
    print("=" * 50)
    
    print_railway_info()
    
    checks = [
        check_environment_variables,
        check_database_url,
        check_redis_url,
        check_port_configuration,
        check_cors_configuration,
        check_database_connection,
        check_redis_connection,
    ]
    
    results = []
    for check in checks:
        if asyncio.iscoroutinefunction(check):
            result = await check()
        else:
            result = check()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Результаты проверки:")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ Все проверки пройдены ({passed}/{total})")
        print("🎉 Конфигурация готова для Railway!")
        return 0
    else:
        print(f"❌ Провалено проверок: {total - passed}/{total}")
        print("🔧 Необходимо исправить ошибки перед развертыванием")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Проверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        sys.exit(1)
