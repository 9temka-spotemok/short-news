"""
Скрипт для сброса миграций и пересоздания таблиц в Railway

Этот скрипт:
1. Удаляет таблицу alembic_version
2. Создает все необходимые таблицы напрямую через SQL
3. Вставляет запись в alembic_version как "initial_schema"

Запуск: railway run python backend/reset_migrations.py
"""
import asyncio
import os
from sqlalchemy import create_engine, text

async def reset_migrations():
    print("🔄 Resetting migrations and recreating tables...")
    
    # Get DATABASE_URL from environment
    db_url = os.environ.get('DATABASE_URL', '')
    
    if not db_url:
        print("❌ Error: DATABASE_URL environment variable is not set.")
        exit(1)
    
    # Replace asyncpg scheme for sync connection
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Drop alembic_version table
                print("🗑️  Dropping alembic_version table...")
                conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
                
                # Drop all existing tables
                print("🗑️  Dropping existing tables...")
                conn.execute(text("DROP TABLE IF EXISTS notifications"))
                conn.execute(text("DROP TABLE IF EXISTS scraper_state"))
                conn.execute(text("DROP TABLE IF EXISTS news_keywords"))
                conn.execute(text("DROP TABLE IF EXISTS user_activity"))
                conn.execute(text("DROP TABLE IF EXISTS user_preferences"))
                conn.execute(text("DROP TABLE IF EXISTS news_items"))
                conn.execute(text("DROP TABLE IF EXISTS users"))
                conn.execute(text("DROP TABLE IF EXISTS companies"))
                
                # Drop types
                print("🗑️  Dropping existing types...")
                conn.execute(text("DROP TYPE IF EXISTS activitytype"))
                conn.execute(text("DROP TYPE IF EXISTS notificationfrequency"))
                conn.execute(text("DROP TYPE IF EXISTS sourcetype"))
                conn.execute(text("DROP TYPE IF EXISTS news_category"))
                conn.execute(text("DROP TYPE IF EXISTS telegramdigestmode"))
                
                # Create extensions
                print("📦 Creating extensions...")
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
                
                # Create types
                print("📝 Creating enum types...")
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
                        CREATE TYPE telegramdigestmode AS ENUM (
                            'all', 'tracked'
                        );
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                """))
                
                # Create companies table
                print("🏢 Creating companies table...")
                conn.execute(text("""
                    CREATE TABLE companies (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        name VARCHAR(255) NOT NULL UNIQUE,
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
                print("👤 Creating users table...")
                conn.execute(text("""
                    CREATE TABLE users (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        email VARCHAR(255) NOT NULL UNIQUE,
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
                
                # Create indexes for companies and users
                print("📊 Creating indexes...")
                conn.execute(text("CREATE INDEX ix_companies_name ON companies(name)"))
                conn.execute(text("CREATE INDEX ix_users_email ON users(email)"))
                
                # Create news_items table
                print("📰 Creating news_items table...")
                conn.execute(text("""
                    CREATE TABLE news_items (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        title VARCHAR(500) NOT NULL,
                        content TEXT,
                        summary TEXT,
                        source_url VARCHAR(1000) UNIQUE NOT NULL,
                        source_type VARCHAR(50) NOT NULL,
                        company_id UUID REFERENCES companies(id),
                        category VARCHAR(50),
                        priority_score FLOAT DEFAULT 0.5,
                        published_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        search_vector TSVECTOR,
                        CONSTRAINT unique_source UNIQUE(source_url)
                    )
                """))
                
                # Create indexes for news_items
                conn.execute(text("CREATE INDEX idx_news_published ON news_items(published_at DESC)"))
                conn.execute(text("CREATE INDEX idx_news_category ON news_items(category)"))
                conn.execute(text("CREATE INDEX idx_news_company ON news_items(company_id)"))
                conn.execute(text("CREATE INDEX idx_news_search ON news_items USING GIN(search_vector)"))
                
                # Create user_preferences table
                print("⚙️  Creating user_preferences table...")
                conn.execute(text("""
                    CREATE TABLE user_preferences (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        subscribed_companies UUID[],
                        interested_categories VARCHAR(50)[],
                        keywords VARCHAR(100)[],
                        notification_frequency notificationfrequency DEFAULT 'DAILY',
                        digest_enabled BOOLEAN DEFAULT FALSE,
                        digest_frequency VARCHAR(20),
                        digest_custom_schedule VARCHAR(100),
                        digest_format VARCHAR(50),
                        digest_include_summaries BOOLEAN DEFAULT TRUE,
                        telegram_chat_id VARCHAR(100),
                        telegram_enabled BOOLEAN DEFAULT FALSE,
                        telegram_digest_mode telegramdigestmode DEFAULT 'all',
                        timezone VARCHAR(50) DEFAULT 'UTC',
                        week_start_day VARCHAR(10) DEFAULT 'monday',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                # Create user_activity table
                print("📊 Creating user_activity table...")
                conn.execute(text("""
                    CREATE TABLE user_activity (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        news_id UUID NOT NULL REFERENCES news_items(id) ON DELETE CASCADE,
                        action activitytype NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                conn.execute(text("CREATE INDEX idx_user_activity_user ON user_activity(user_id)"))
                conn.execute(text("CREATE INDEX idx_user_activity_news ON user_activity(news_id)"))
                
                # Create news_keywords table
                print("🔑 Creating news_keywords table...")
                conn.execute(text("""
                    CREATE TABLE news_keywords (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        news_id UUID NOT NULL REFERENCES news_items(id) ON DELETE CASCADE,
                        keyword VARCHAR(100) NOT NULL,
                        relevance_score FLOAT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                conn.execute(text("CREATE INDEX idx_keywords ON news_keywords(keyword)"))
                
                # Create scraper_state table
                print("🤖 Creating scraper_state table...")
                conn.execute(text("""
                    CREATE TABLE scraper_state (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        source_id VARCHAR(255) NOT NULL UNIQUE,
                        last_scraped_at TIMESTAMP WITH TIME ZONE,
                        last_item_id VARCHAR(500),
                        status VARCHAR(50),
                        error_message TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                conn.execute(text("CREATE INDEX idx_scraper_state_source ON scraper_state(source_id)"))
                
                # Create notifications table
                print("🔔 Creating notifications table...")
                conn.execute(text("""
                    CREATE TABLE notifications (
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
                
                conn.execute(text("CREATE INDEX idx_notifications_user ON notifications(user_id)"))
                conn.execute(text("CREATE INDEX idx_notifications_read ON notifications(is_read)"))
                conn.execute(text("CREATE INDEX idx_notifications_created ON notifications(created_at)"))
                
                # Create alembic_version table and mark as "initial_schema"
                print("📝 Setting up Alembic version...")
                conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    )
                """))
                
                conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('initial_schema')"))
                
                # Commit transaction
                trans.commit()
                
                print("✅ All tables created successfully!")
                print("✅ Alembic version set to 'initial_schema'")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during transaction: {e}")
                raise
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(reset_migrations())

