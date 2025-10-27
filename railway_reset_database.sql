-- Railway Database Reset Script
-- Run this in Railway Dashboard → PostgreSQL → Connect → Query

-- Step 1: Drop all existing tables
DROP TABLE IF EXISTS alembic_version CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS scraper_state CASCADE;
DROP TABLE IF EXISTS news_keywords CASCADE;
DROP TABLE IF EXISTS user_activity CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS news_items CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

-- Step 2: Drop all enum types
DROP TYPE IF EXISTS activitytype CASCADE;
DROP TYPE IF EXISTS notificationfrequency CASCADE;
DROP TYPE IF EXISTS notification_frequency CASCADE;
DROP TYPE IF EXISTS digestfrequency CASCADE;
DROP TYPE IF EXISTS digest_frequency CASCADE;
DROP TYPE IF EXISTS digestformat CASCADE;
DROP TYPE IF EXISTS digest_format CASCADE;
DROP TYPE IF EXISTS telegramdigestmode CASCADE;
DROP TYPE IF EXISTS telegram_digest_mode CASCADE;
DROP TYPE IF EXISTS sourcetype CASCADE;
DROP TYPE IF EXISTS news_category CASCADE;
DROP TYPE IF EXISTS notification_type CASCADE;
DROP TYPE IF EXISTS notification_priority CASCADE;

-- Step 3: Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Step 4: Create enum types
DO $$ BEGIN
    CREATE TYPE news_category AS ENUM (
        'PRODUCT_UPDATE', 'PRICING_CHANGE', 'STRATEGIC_ANNOUNCEMENT', 
        'TECHNICAL_UPDATE', 'FUNDING_NEWS', 'RESEARCH_PAPER', 'COMMUNITY_EVENT',
        'PARTNERSHIP', 'ACQUISITION', 'INTEGRATION', 'SECURITY_UPDATE',
        'API_UPDATE', 'MODEL_RELEASE', 'PERFORMANCE_IMPROVEMENT', 'FEATURE_DEPRECATION'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE sourcetype AS ENUM (
        'BLOG', 'TWITTER', 'GITHUB', 'REDDIT', 'NEWS_SITE', 'PRESS_RELEASE'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE notificationfrequency AS ENUM (
        'REALTIME', 'DAILY', 'WEEKLY', 'NEVER'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE notification_frequency AS ENUM (
        'realtime', 'daily', 'weekly', 'never'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE digest_frequency AS ENUM (
        'daily', 'weekly', 'custom'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE digest_format AS ENUM (
        'short', 'detailed'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE telegram_digest_mode AS ENUM (
        'all', 'tracked'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE activitytype AS ENUM (
        'VIEWED', 'FAVORITED', 'MARKED_READ', 'SHARED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Step 5: Create companies table
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
);

CREATE INDEX ix_companies_name ON companies(name);

-- Step 6: Create users table
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
);

CREATE INDEX ix_users_email ON users(email);

-- Step 7: Create news_items table
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
);

CREATE INDEX idx_news_published ON news_items(published_at DESC);
CREATE INDEX idx_news_category ON news_items(category);
CREATE INDEX idx_news_company ON news_items(company_id);
CREATE INDEX idx_news_search ON news_items USING GIN(search_vector);

-- Step 8: Create user_preferences table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscribed_companies UUID[],
    interested_categories VARCHAR(50)[],
    keywords VARCHAR(100)[],
    notification_frequency notification_frequency DEFAULT 'daily',
    digest_enabled BOOLEAN DEFAULT FALSE,
    digest_frequency digest_frequency DEFAULT 'daily',
    digest_custom_schedule JSONB DEFAULT '{}',
    digest_format digest_format DEFAULT 'short',
    digest_include_summaries BOOLEAN DEFAULT TRUE,
    telegram_chat_id VARCHAR(255),
    telegram_enabled BOOLEAN DEFAULT FALSE,
    telegram_digest_mode telegram_digest_mode DEFAULT 'all',
    timezone VARCHAR(50) DEFAULT 'UTC',
    week_start_day INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 9: Create user_activity table
CREATE TABLE user_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    news_id UUID NOT NULL REFERENCES news_items(id) ON DELETE CASCADE,
    action activitytype NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_activity_user ON user_activity(user_id);
CREATE INDEX idx_user_activity_news ON user_activity(news_id);

-- Step 10: Create news_keywords table
CREATE TABLE news_keywords (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    news_id UUID NOT NULL REFERENCES news_items(id) ON DELETE CASCADE,
    keyword VARCHAR(100) NOT NULL,
    relevance_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_keywords ON news_keywords(keyword);

-- Step 11: Create scraper_state table
CREATE TABLE scraper_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(255) NOT NULL UNIQUE,
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    last_item_id VARCHAR(500),
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_scraper_state_source ON scraper_state(source_id);

-- Step 12: Create notifications table
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
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at);

-- Step 13: Create alembic_version table
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) VALUES ('initial_schema');

-- Success message
SELECT 'Database reset completed successfully!' AS status;

