# Скрипт для проверки готовности к деплою на Railway (PowerShell)
# Запустите этот скрипт перед деплоем

Write-Host "Проверка готовности к деплою на Railway" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Проверка структуры проекта
Write-Host "Проверка структуры проекта..." -ForegroundColor Yellow
if (-not (Test-Path "backend")) {
    Write-Host "Папка backend не найдена" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "railway.json")) {
    Write-Host "Файл railway.json не найден" -ForegroundColor Red
    exit 1
}

Write-Host "Структура проекта корректна" -ForegroundColor Green

# Проверка файлов конфигурации
Write-Host "Проверка файлов конфигурации..." -ForegroundColor Yellow
if (-not (Test-Path "backend/requirements.txt")) {
    Write-Host "Файл backend/requirements.txt не найден" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "backend/env.production")) {
    Write-Host "Файл backend/env.production не найден" -ForegroundColor Red
    exit 1
}

Write-Host "Файлы конфигурации найдены" -ForegroundColor Green

# Проверка railway.json
Write-Host "Проверка railway.json..." -ForegroundColor Yellow
$railwayContent = Get-Content "railway.json" -Raw
if (-not ($railwayContent -match "uvicorn main:app")) {
    Write-Host "railway.json не содержит правильную команду запуска" -ForegroundColor Red
    exit 1
}

Write-Host "railway.json настроен правильно" -ForegroundColor Green

# Проверка requirements.txt
Write-Host "Проверка зависимостей..." -ForegroundColor Yellow
$requirementsContent = Get-Content "backend/requirements.txt" -Raw
if (-not ($requirementsContent -match "fastapi")) {
    Write-Host "FastAPI не найден в requirements.txt" -ForegroundColor Red
    exit 1
}

if (-not ($requirementsContent -match "uvicorn")) {
    Write-Host "Uvicorn не найден в requirements.txt" -ForegroundColor Red
    exit 1
}

Write-Host "Зависимости настроены" -ForegroundColor Green

# Проверка переменных окружения
Write-Host "Проверка переменных окружения..." -ForegroundColor Yellow
$envContent = Get-Content "backend/env.production" -Raw
if (-not ($envContent -match "SECRET_KEY")) {
    Write-Host "SECRET_KEY не найден в env.production" -ForegroundColor Red
    exit 1
}

if (-not ($envContent -match "DATABASE_URL")) {
    Write-Host "DATABASE_URL не найден в env.production" -ForegroundColor Red
    exit 1
}

if (-not ($envContent -match "REDIS_URL")) {
    Write-Host "REDIS_URL не найден в env.production" -ForegroundColor Red
    exit 1
}

Write-Host "Переменные окружения настроены" -ForegroundColor Green

# Проверка main.py
Write-Host "Проверка main.py..." -ForegroundColor Yellow
if (-not (Test-Path "backend/main.py")) {
    Write-Host "Файл backend/main.py не найден" -ForegroundColor Red
    exit 1
}

Write-Host "main.py найден" -ForegroundColor Green

# Проверка health endpoint
Write-Host "Проверка health endpoint..." -ForegroundColor Yellow
if (Test-Path "backend/app/api/v1/api.py") {
    $apiContent = Get-Content "backend/app/api/v1/api.py" -Raw
    if (-not ($apiContent -match "/health")) {
        Write-Host "Health endpoint не найден в API" -ForegroundColor Red
        exit 1
    }
    Write-Host "Health endpoint настроен" -ForegroundColor Green
} else {
    Write-Host "Файл API не найден" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Все проверки пройдены успешно!" -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги:" -ForegroundColor Yellow
Write-Host "1. Зайдите на railway.app" -ForegroundColor White
Write-Host "2. Создайте новый проект из GitHub репозитория" -ForegroundColor White
Write-Host "3. Выберите папку backend/ как корневую" -ForegroundColor White
Write-Host "4. Добавьте PostgreSQL и Redis сервисы" -ForegroundColor White
Write-Host "5. Настройте переменные окружения из RAILWAY_ENV_VARS.md" -ForegroundColor White
Write-Host "6. Дождитесь завершения деплоя" -ForegroundColor White
Write-Host "7. Обновите VITE_API_URL в Netlify" -ForegroundColor White
Write-Host ""
Write-Host "Подробная инструкция: RAILWAY_DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan
Write-Host "Быстрый старт: RAILWAY_QUICK_START.md" -ForegroundColor Cyan
Write-Host "Переменные окружения: RAILWAY_ENV_VARS.md" -ForegroundColor Cyan
