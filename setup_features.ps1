# Setup script for new features (PowerShell version)
# Run this after pulling the code

Write-Host "🚀 Setting up new features for AI Competitor Insight Hub" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "backend") -or -not (Test-Path "frontend")) {
    Write-Host "❌ Error: Run this script from project root directory" -ForegroundColor Red
    exit 1
}

# Step 1: Apply migrations
Write-Host "📦 Step 1/3: Applying database migrations..." -ForegroundColor Yellow
Set-Location backend

try {
    if (Get-Command alembic -ErrorAction SilentlyContinue) {
        alembic upgrade head
    } elseif (Get-Command poetry -ErrorAction SilentlyContinue) {
        poetry run alembic upgrade head
    } else {
        python -m alembic upgrade head
    }
    
    Write-Host "✅ Migrations applied" -ForegroundColor Green
} catch {
    Write-Host "❌ Migration failed. Check database connection." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Initialize user settings
Write-Host "⚙️  Step 2/3: Initializing user settings..." -ForegroundColor Yellow

if (Test-Path "scripts/init_all_settings.py") {
    try {
        python scripts/init_all_settings.py
        Write-Host "✅ User settings initialized" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Warning: Failed to initialize settings. This is OK if no users exist yet." -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Script not found, skipping..." -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Summary
Write-Host "🎉 Step 3/3: Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start backend:  cd backend; uvicorn main:app --reload"
Write-Host "2. Start frontend: cd frontend; npm run dev"
Write-Host "3. (Optional) Start Celery worker: cd backend; python -m celery -A celery_app worker --loglevel=info"
Write-Host "4. (Optional) Start Celery beat:   cd backend; python -m celery -A celery_app beat --loglevel=info"
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "- SETUP_NEW_FEATURES.md - Full setup guide"
Write-Host "- TROUBLESHOOTING_DIGESTS.md - If something doesn't work"
Write-Host "- docs/TELEGRAM_SETUP.md - Telegram bot setup"
Write-Host ""
Write-Host "✅ Ready to test new features!" -ForegroundColor Green

# Return to root directory
Set-Location ..



