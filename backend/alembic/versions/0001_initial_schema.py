"""Create initial tables

Revision ID: initial_schema
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\"")
    
    # Check if tables already exist
    connection = op.get_bind()
    
    # Check if companies table exists
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables WHERE table_name = 'companies'
        )
    """))
    
    companies_exist = result.scalar()
    
    # Check if news_items table exists
    result_news = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables WHERE table_name = 'news_items'
        )
    """))
    
    news_items_exist = result_news.scalar()
    
    # Only skip if ALL tables exist
    if companies_exist and news_items_exist:
        print("Tables already exist, skipping initial schema creation")
        return
    
    # Create custom types using raw SQL to avoid conflicts
    op.execute("""
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
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sourcetype AS ENUM (
                'BLOG', 'TWITTER', 'GITHUB', 'REDDIT', 'NEWS_SITE', 'PRESS_RELEASE'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationfrequency AS ENUM (
                'REALTIME', 'DAILY', 'WEEKLY', 'NEVER'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE activitytype AS ENUM (
                'VIEWED', 'FAVORITED', 'MARKED_READ', 'SHARED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('twitter_handle', sa.String(length=100), nullable=True),
        sa.Column('github_org', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('email_verification_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create news_items table using raw SQL to avoid enum type conflicts
    op.execute("""
        CREATE TABLE IF NOT EXISTS news_items (
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
    """)
    
    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('subscribed_companies', postgresql.ARRAY(sa.UUID()), nullable=True),
        sa.Column('interested_categories', postgresql.ARRAY(sa.Enum('product_update', 'pricing_change', 'strategic_announcement', 'technical_update', 'funding_news', 'research_paper', 'community_event', 'partnership', 'acquisition', 'integration', 'security_update', 'api_update', 'model_release', 'performance_improvement', 'feature_deprecation', name='newscategory')), nullable=True),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('notification_frequency', sa.Enum('REALTIME', 'DAILY', 'WEEKLY', 'NEVER', name='notificationfrequency'), server_default='DAILY', nullable=True),
        sa.Column('digest_format', sa.String(length=50), nullable=True),
        sa.Column('telegram_chat_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_activity table
    op.create_table(
        'user_activity',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('news_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.Enum('VIEWED', 'FAVORITED', 'MARKED_READ', 'SHARED', name='activitytype'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['news_id'], ['news_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create news_keywords table
    op.create_table(
        'news_keywords',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('news_id', sa.UUID(), nullable=False),
        sa.Column('keyword', sa.String(length=100), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['news_id'], ['news_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create scraper_state table
    op.create_table(
        'scraper_state',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('source_id', sa.String(length=255), nullable=False),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_item_id', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create notifications table using raw SQL to avoid enum type conflicts
    op.execute("""
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
    """)
    
    # Create indexes
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    # Create news_items indexes using raw SQL
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_category ON news_items(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_company ON news_items(company_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_search ON news_items USING GIN(search_vector)")
    op.create_index(op.f('idx_keywords'), 'news_keywords', ['keyword'], unique=False)
    op.create_index(op.f('idx_user_activity_user'), 'user_activity', ['user_id'], unique=False)
    op.create_index(op.f('idx_user_activity_news'), 'user_activity', ['news_id'], unique=False)
    op.create_index(op.f('idx_scraper_state_source'), 'scraper_state', ['source_id'], unique=True)
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at)")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_notifications_created")
    op.execute("DROP INDEX IF EXISTS idx_notifications_read")
    op.execute("DROP INDEX IF EXISTS idx_notifications_user")
    op.drop_index(op.f('idx_scraper_state_source'), table_name='scraper_state')
    op.drop_index(op.f('idx_user_activity_news'), table_name='user_activity')
    op.drop_index(op.f('idx_user_activity_user'), table_name='user_activity')
    op.drop_index(op.f('idx_keywords'), table_name='news_keywords')
    # Drop news_items indexes using raw SQL
    op.execute("DROP INDEX IF EXISTS idx_news_search")
    op.execute("DROP INDEX IF EXISTS idx_news_company")
    op.execute("DROP INDEX IF EXISTS idx_news_category")
    op.execute("DROP INDEX IF EXISTS idx_news_published")
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_companies_name'), table_name='companies')
    
    # Drop tables
    op.execute("DROP TABLE IF EXISTS notifications")
    op.drop_table('scraper_state')
    op.drop_table('news_keywords')
    op.drop_table('user_activity')
    op.drop_table('user_preferences')
    op.execute("DROP TABLE IF EXISTS news_items")
    op.drop_table('users')
    op.drop_table('companies')
    
    # Drop types
    op.execute("DROP TYPE IF EXISTS activitytype")
    op.execute("DROP TYPE IF EXISTS notificationfrequency")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS news_category")