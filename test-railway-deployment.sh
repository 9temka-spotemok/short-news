#!/bin/bash

# Скрипт для проверки готовности к деплою на Railway
# Запустите этот скрипт перед деплоем

echo "🚀 Проверка готовности к деплою на Railway"
echo "=========================================="

# Проверка структуры проекта
echo "📁 Проверка структуры проекта..."
if [ ! -d "backend" ]; then
    echo "❌ Папка backend не найдена"
    exit 1
fi

if [ ! -f "railway.json" ]; then
    echo "❌ Файл railway.json не найден"
    exit 1
fi

echo "✅ Структура проекта корректна"

# Проверка файлов конфигурации
echo "📋 Проверка файлов конфигурации..."
if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ Файл backend/requirements.txt не найден"
    exit 1
fi

if [ ! -f "backend/env.production" ]; then
    echo "❌ Файл backend/env.production не найден"
    exit 1
fi

echo "✅ Файлы конфигурации найдены"

# Проверка railway.json
echo "🔧 Проверка railway.json..."
if ! grep -q "uvicorn main:app" railway.json; then
    echo "❌ railway.json не содержит правильную команду запуска"
    exit 1
fi

echo "✅ railway.json настроен правильно"

# Проверка requirements.txt
echo "📦 Проверка зависимостей..."
if ! grep -q "fastapi" backend/requirements.txt; then
    echo "❌ FastAPI не найден в requirements.txt"
    exit 1
fi

if ! grep -q "uvicorn" backend/requirements.txt; then
    echo "❌ Uvicorn не найден в requirements.txt"
    exit 1
fi

echo "✅ Зависимости настроены"

# Проверка переменных окружения
echo "🔑 Проверка переменных окружения..."
if ! grep -q "SECRET_KEY" backend/env.production; then
    echo "❌ SECRET_KEY не найден в env.production"
    exit 1
fi

if ! grep -q "DATABASE_URL" backend/env.production; then
    echo "❌ DATABASE_URL не найден в env.production"
    exit 1
fi

if ! grep -q "REDIS_URL" backend/env.production; then
    echo "❌ REDIS_URL не найден в env.production"
    exit 1
fi

echo "✅ Переменные окружения настроены"

# Проверка main.py
echo "🐍 Проверка main.py..."
if [ ! -f "backend/main.py" ]; then
    echo "❌ Файл backend/main.py не найден"
    exit 1
fi

echo "✅ main.py найден"

# Проверка health endpoint
echo "🏥 Проверка health endpoint..."
if ! grep -q "/health" backend/app/api/v1/api.py; then
    echo "❌ Health endpoint не найден в API"
    exit 1
fi

echo "✅ Health endpoint настроен"

echo ""
echo "🎉 Все проверки пройдены успешно!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Зайдите на railway.app"
echo "2. Создайте новый проект из GitHub репозитория"
echo "3. Выберите папку backend/ как корневую"
echo "4. Добавьте PostgreSQL и Redis сервисы"
echo "5. Настройте переменные окружения из RAILWAY_ENV_VARS.md"
echo "6. Дождитесь завершения деплоя"
echo "7. Обновите VITE_API_URL в Netlify"
echo ""
echo "📖 Подробная инструкция: RAILWAY_DEPLOYMENT_GUIDE.md"
echo "⚡ Быстрый старт: RAILWAY_QUICK_START.md"
echo "🔧 Переменные окружения: RAILWAY_ENV_VARS.md"
