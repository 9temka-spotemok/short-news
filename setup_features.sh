#!/bin/bash

# Setup script for new features
# Run this after pulling the code

echo "🚀 Setting up new features for AI Competitor Insight Hub"
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Run this script from project root directory"
    exit 1
fi

# Step 1: Apply migrations
echo "📦 Step 1/3: Applying database migrations..."
cd backend

if command -v alembic &> /dev/null; then
    alembic upgrade head
elif command -v poetry &> /dev/null; then
    poetry run alembic upgrade head
else
    python -m alembic upgrade head
fi

if [ $? -ne 0 ]; then
    echo "❌ Migration failed. Check database connection."
    exit 1
fi

echo "✅ Migrations applied"
echo ""

# Step 2: Initialize user settings
echo "⚙️  Step 2/3: Initializing user settings..."

if [ -f "scripts/init_all_settings.py" ]; then
    python scripts/init_all_settings.py
    
    if [ $? -ne 0 ]; then
        echo "⚠️  Warning: Failed to initialize settings. This is OK if no users exist yet."
    else
        echo "✅ User settings initialized"
    fi
else
    echo "⚠️  Script not found, skipping..."
fi

echo ""

# Step 3: Summary
echo "🎉 Step 3/3: Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start backend:  cd backend && uvicorn main:app --reload"
echo "2. Start frontend: cd frontend && npm run dev"
echo "3. (Optional) Start Celery worker: cd backend && celery -A celery_app worker --loglevel=info"
echo "4. (Optional) Start Celery beat:   cd backend && celery -A celery_app beat --loglevel=info"
echo ""
echo "📚 Documentation:"
echo "- SETUP_NEW_FEATURES.md - Full setup guide"
echo "- TROUBLESHOOTING_DIGESTS.md - If something doesn't work"
echo "- docs/TELEGRAM_SETUP.md - Telegram bot setup"
echo ""
echo "✅ Ready to test new features!"

