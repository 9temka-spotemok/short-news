-- AI Competitor Insight Hub - Database Initialization
-- This file is executed when the PostgreSQL container starts for the first time

-- Create database if it doesn't exist (handled by environment variables)
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE news_category AS ENUM (
    'product_update',
    'pricing_change', 
    'strategic_announcement',
    'technical_update',
    'funding_news',
    'research_paper',
    'community_event',
    'partnership',
    'acquisition',
    'integration',
    'security_update',
    'api_update',
    'model_release',
    'performance_improvement',
    'feature_deprecation'
);

CREATE TYPE source_type AS ENUM (
    'blog',
    'twitter',
    'github',
    'reddit',
    'news_site',
    'press_release'
);

CREATE TYPE notification_frequency AS ENUM (
    'realtime',
    'daily',
    'weekly',
    'never'
);

-- Create companies table
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    website VARCHAR(500),
    description TEXT,
    logo_url VARCHAR(500),
    category VARCHAR(100), -- llm_provider, search_engine, toolkit, etc.
    twitter_handle VARCHAR(100),
    github_org VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create news_items table
CREATE TABLE IF NOT EXISTS news_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    summary TEXT,
    source_url VARCHAR(1000) UNIQUE NOT NULL,
    source_type source_type NOT NULL,
    company_id UUID REFERENCES companies(id),
    category news_category,
    priority_score FLOAT DEFAULT 0.5,
    published_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Full-text search
    search_vector TSVECTOR,
    
    CONSTRAINT unique_source UNIQUE(source_url)
);

-- Create user_preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    subscribed_companies UUID[], -- Array of company IDs
    interested_categories news_category[], -- Array of categories
    keywords TEXT[], -- Array of keywords
    notification_frequency notification_frequency DEFAULT 'daily',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_user_pref UNIQUE(user_id)
);

-- Create user_activity table
CREATE TABLE IF NOT EXISTS user_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    news_id UUID REFERENCES news_items(id) ON DELETE CASCADE,
    action VARCHAR(50), -- viewed, favorited, marked_read
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_user_news_action UNIQUE(user_id, news_id, action)
);

-- Create news_keywords table
CREATE TABLE IF NOT EXISTS news_keywords (
    news_id UUID REFERENCES news_items(id) ON DELETE CASCADE,
    keyword VARCHAR(100),
    relevance_score FLOAT,
    
    PRIMARY KEY(news_id, keyword)
);

-- Create scraper_state table
CREATE TABLE IF NOT EXISTS scraper_state (
    source_id VARCHAR(255) PRIMARY KEY,
    last_scraped_at TIMESTAMP,
    last_item_id VARCHAR(500),
    status VARCHAR(50), -- active, paused, error
    error_message TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_category ON news_items(category);
CREATE INDEX IF NOT EXISTS idx_news_company ON news_items(company_id);
CREATE INDEX IF NOT EXISTS idx_news_search ON news_items USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_keywords ON news_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_news ON user_activity(news_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);

-- Create function to update search vector
CREATE OR REPLACE FUNCTION update_news_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'C');
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for search vector update
CREATE TRIGGER update_news_search_vector_trigger
    BEFORE INSERT OR UPDATE ON news_items
    FOR EACH ROW
    EXECUTE FUNCTION update_news_search_vector();

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at 
    BEFORE UPDATE ON companies 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at 
    BEFORE UPDATE ON user_preferences 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample companies
INSERT INTO companies (name, website, description, category, twitter_handle, github_org) VALUES
('OpenAI', 'https://openai.com', 'AI research company focused on developing safe AI', 'llm_provider', 'OpenAI', 'openai'),
('Anthropic', 'https://www.anthropic.com', 'AI safety company developing helpful, harmless, and honest AI', 'llm_provider', 'AnthropicAI', 'anthropics'),
('Google', 'https://ai.google', 'Google AI research and products', 'llm_provider', 'GoogleAI', 'google'),
('Meta', 'https://ai.meta.com', 'Meta AI research and development', 'llm_provider', 'MetaAI', 'facebookresearch'),
('Microsoft', 'https://www.microsoft.com/en-us/ai', 'Microsoft AI platform and services', 'llm_provider', 'MicrosoftAI', 'microsoft'),
('Cohere', 'https://cohere.ai', 'Enterprise AI platform for text understanding', 'llm_provider', 'CohereAI', 'cohere'),
('Hugging Face', 'https://huggingface.co', 'Open source AI platform and community', 'toolkit', 'huggingface', 'huggingface'),
('LangChain', 'https://langchain.com', 'Framework for developing LLM applications', 'toolkit', 'LangChainAI', 'langchain-ai'),
('Replicate', 'https://replicate.com', 'Machine learning model hosting platform', 'toolkit', 'replicate', 'replicate'),
('Pinecone', 'https://www.pinecone.io', 'Vector database for AI applications', 'toolkit', 'pinecone', 'pinecone-io')
ON CONFLICT (name) DO NOTHING;

-- Create initial admin user (password: admin123)
INSERT INTO users (email, password_hash, full_name, is_active, is_verified) VALUES
('admin@shot-news.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4zJ4jQOQjW', 'Admin User', TRUE, TRUE)
ON CONFLICT (email) DO NOTHING;
