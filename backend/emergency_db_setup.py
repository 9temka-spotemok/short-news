#!/usr/bin/env python3
"""
Emergency Database Setup for Railway
Создает таблицы напрямую через SQL если миграции не работают
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.core.config import settings

async def create_tables_directly():
    """Create tables directly using SQL"""
    print("🚨 Emergency Database Setup")
    print("=" * 50)
    
    # Get database URL
    db_url = settings.DATABASE_URL
    if not db_url:
        print("❌ DATABASE_URL not configured!")
        return False
    
    print(f"✅ Database URL configured")
    
    # Convert to sync URL for direct SQL execution
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        engine = create_engine(sync_url)
        
        with engine.connect() as conn:
            # Check if tables exist
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables WHERE table_name = 'user_preferences'
                )
            """))
            
            if result.scalar():
                print("✅ Tables already exist")
                return True
            
            print("📦 Creating tables directly...")
            
            # Create extensions
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\""))
            
            # Create types
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE news_category AS ENUM (
                        'product_update', 'pricing_change', 'strategic_announcement', 
                        'technical_update', 'funding_news', 'research_paper', 'community_event',
                        'partnership', 'acquisition', 'integration', 'security_update',
                        'api_update', 'model_release', 'performance_improvement', 'feature_deprecation'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE sourcetype AS ENUM (
                        'BLOG', 'TWITTER', 'GITHUB', 'REDDIT', 'NEWS_SITE', 'PRESS_RELEASE'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE notificationfrequency AS ENUM (
                        'REALTIME', 'DAILY', 'WEEKLY', 'NEVER'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE activitytype AS ENUM (
                        'VIEWED', 'FAVORITED', 'MARKED_READ', 'SHARED'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE digestfrequency AS ENUM (
                        'DAILY', 'WEEKLY', 'MONTHLY'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            # Create companies table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS companies (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    name VARCHAR(255) UNIQUE NOT NULL,
                    website VARCHAR(500),
                    description TEXT,
                    logo_url VARCHAR(500),
                    category VARCHAR(100),
                    twitter_handle VARCHAR(100),
                    github_org VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create users table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    email_verification_token VARCHAR(255),
                    password_reset_token VARCHAR(255),
                    password_reset_expires TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create news_items table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS news_items (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    title VARCHAR(500) NOT NULL,
                    content TEXT,
                    summary TEXT,
                    source_url VARCHAR(1000) UNIQUE NOT NULL,
                    source_type sourcetype NOT NULL,
                    company_id UUID REFERENCES companies(id),
                    category news_category,
                    priority_score FLOAT DEFAULT 0.5,
                    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    search_vector TSVECTOR,
                    CONSTRAINT unique_source UNIQUE(source_url)
                )
            """))
            
            # Create user_preferences table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    subscribed_companies UUID[],
                    interested_categories news_category[],
                    keywords TEXT[],
                    notification_frequency notificationfrequency DEFAULT 'DAILY',
                    digest_enabled BOOLEAN DEFAULT TRUE,
                    digest_frequency digestfrequency DEFAULT 'DAILY',
                    digest_custom_schedule VARCHAR(100),
                    digest_format VARCHAR(50),
                    digest_include_summaries BOOLEAN DEFAULT TRUE,
                    telegram_chat_id VARCHAR(100),
                    telegram_enabled BOOLEAN DEFAULT FALSE,
                    telegram_digest_mode VARCHAR(50),
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    week_start_day INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT unique_user_pref UNIQUE(user_id)
                )
            """))
            
            # Create user_activity table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    news_id UUID REFERENCES news_items(id) ON DELETE CASCADE,
                    action activitytype NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT unique_user_news_action UNIQUE(user_id, news_id, action)
                )
            """))
            
            # Create news_keywords table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS news_keywords (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    news_id UUID REFERENCES news_items(id) ON DELETE CASCADE,
                    keyword VARCHAR(100) NOT NULL,
                    relevance_score FLOAT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create scraper_state table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS scraper_state (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    source_id VARCHAR(255) UNIQUE NOT NULL,
                    last_scraped_at TIMESTAMP WITH TIME ZONE,
                    last_item_id VARCHAR(500),
                    status VARCHAR(50),
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create notifications table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT,
                    data JSONB,
                    is_read BOOLEAN DEFAULT FALSE,
                    priority VARCHAR(20) DEFAULT 'normal',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_companies_name ON companies(name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_category ON news_items(category)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_company ON news_items(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_search ON news_items USING GIN(search_vector)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_keywords ON news_keywords(keyword)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_activity_news ON user_activity(news_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_scraper_state_source ON scraper_state(source_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at)"))
            
            conn.commit()
            
        print("✅ Tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

async def main():
    """Main function"""
    success = await create_tables_directly()
    if success:
        print("\n🎉 Database setup complete!")
        print("You can now restart your services.")
    else:
        print("\n💥 Database setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
