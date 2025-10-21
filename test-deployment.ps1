# Скрипт для тестирования деплоя на Netlify (PowerShell)
# Запустите этот скрипт перед деплоем

Write-Host "Тестирование готовности к деплою на Netlify" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green

# Проверка структуры проекта
Write-Host "Проверка структуры проекта..." -ForegroundColor Yellow
if (-not (Test-Path "frontend")) {
    Write-Host "Папка frontend не найдена" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "backend")) {
    Write-Host "Папка backend не найдена" -ForegroundColor Red
    exit 1
}

Write-Host "Структура проекта корректна" -ForegroundColor Green

# Проверка файлов конфигурации
Write-Host "Проверка файлов конфигурации..." -ForegroundColor Yellow
if (-not (Test-Path "netlify.toml")) {
    Write-Host "Файл netlify.toml не найден" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "frontend/package.json")) {
    Write-Host "Файл frontend/package.json не найден" -ForegroundColor Red
    exit 1
}

Write-Host "Файлы конфигурации найдены" -ForegroundColor Green

# Переход в папку фронтенда
Set-Location frontend

# Проверка зависимостей
Write-Host "Проверка зависимостей..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules")) {
    Write-Host "Установка зависимостей..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ошибка установки зависимостей" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Зависимости установлены" -ForegroundColor Green

# Проверка TypeScript
Write-Host "Проверка TypeScript..." -ForegroundColor Yellow
npm run type-check
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибки TypeScript" -ForegroundColor Red
    exit 1
}

Write-Host "TypeScript проверка пройдена" -ForegroundColor Green

# Сборка проекта
Write-Host "Сборка проекта..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка сборки" -ForegroundColor Red
    exit 1
}

Write-Host "Проект успешно собран" -ForegroundColor Green

# Проверка папки dist
if (-not (Test-Path "dist")) {
    Write-Host "Папка dist не создана" -ForegroundColor Red
    exit 1
}

Write-Host "Папка dist создана" -ForegroundColor Green

# Проверка размера сборки
Write-Host "Размер сборки:" -ForegroundColor Yellow
Get-ChildItem -Path "dist" -Recurse | Measure-Object -Property Length -Sum | ForEach-Object {
    $sizeMB = [math]::Round($_.Sum / 1MB, 2)
    Write-Host "Размер: $sizeMB MB" -ForegroundColor Cyan
}

# Проверка основных файлов
if (-not (Test-Path "dist/index.html")) {
    Write-Host "index.html не найден в dist" -ForegroundColor Red
    exit 1
}

Write-Host "Основные файлы найдены" -ForegroundColor Green

# Возврат в корневую папку
Set-Location ..

Write-Host ""
Write-Host "Все проверки пройдены успешно!" -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги:" -ForegroundColor Yellow
Write-Host "1. Настройте переменные окружения в Netlify" -ForegroundColor White
Write-Host "2. Подключите репозиторий к Netlify" -ForegroundColor White
Write-Host "3. Настройте сборку (build command: npm run build, publish directory: frontend/dist)" -ForegroundColor White
Write-Host "4. Деплойте бэкенд на Railway/Render/Heroku" -ForegroundColor White
Write-Host "5. Обновите VITE_API_URL в Netlify на URL вашего бэкенда" -ForegroundColor White
Write-Host ""
Write-Host "Подробная инструкция: NETLIFY_DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan