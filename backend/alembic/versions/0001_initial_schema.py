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
    
    tables_exist = result.scalar()
    
    if tables_exist:
        print("Tables already exist, skipping initial schema creation")
        return
    
    # Create custom types using raw SQL to avoid conflicts
    op.execute("""
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
    
    # Create news_items table
    op.create_table(
        'news_items',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=False),
        sa.Column('source_type', sa.Enum('BLOG', 'TWITTER', 'GITHUB', 'REDDIT', 'NEWS_SITE', 'PRESS_RELEASE', name='sourcetype'), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.Column('category', sa.Enum('PRODUCT_UPDATE', 'PRICING_CHANGE', 'STRATEGIC_ANNOUNCEMENT', 'TECHNICAL_UPDATE', 'FUNDING_NEWS', 'RESEARCH_PAPER', 'COMMUNITY_EVENT', 'PARTNERSHIP', 'ACQUISITION', 'INTEGRATION', 'SECURITY_UPDATE', 'API_UPDATE', 'MODEL_RELEASE', 'PERFORMANCE_IMPROVEMENT', 'FEATURE_DEPRECATION', name='newscategory'), nullable=True),
        sa.Column('priority_score', sa.Float(), server_default='0.5', nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('subscribed_companies', postgresql.ARRAY(sa.UUID()), nullable=True),
        sa.Column('interested_categories', postgresql.ARRAY(sa.Enum('PRODUCT_UPDATE', 'PRICING_CHANGE', 'STRATEGIC_ANNOUNCEMENT', 'TECHNICAL_UPDATE', 'FUNDING_NEWS', 'RESEARCH_PAPER', 'COMMUNITY_EVENT', 'PARTNERSHIP', 'ACQUISITION', 'INTEGRATION', 'SECURITY_UPDATE', 'API_UPDATE', 'MODEL_RELEASE', 'PERFORMANCE_IMPROVEMENT', 'FEATURE_DEPRECATION', name='newscategory')), nullable=True),
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
    
    # Create indexes
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('idx_news_published'), 'news_items', [sa.text('published_at DESC')], unique=False)
    op.create_index(op.f('idx_news_category'), 'news_items', ['category'], unique=False)
    op.create_index(op.f('idx_news_company'), 'news_items', ['company_id'], unique=False)
    op.create_index(op.f('idx_news_search'), 'news_items', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_index(op.f('idx_keywords'), 'news_keywords', ['keyword'], unique=False)
    op.create_index(op.f('idx_user_activity_user'), 'user_activity', ['user_id'], unique=False)
    op.create_index(op.f('idx_user_activity_news'), 'user_activity', ['news_id'], unique=False)
    op.create_index(op.f('idx_scraper_state_source'), 'scraper_state', ['source_id'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('idx_scraper_state_source'), table_name='scraper_state')
    op.drop_index(op.f('idx_user_activity_news'), table_name='user_activity')
    op.drop_index(op.f('idx_user_activity_user'), table_name='user_activity')
    op.drop_index(op.f('idx_keywords'), table_name='news_keywords')
    op.drop_index(op.f('idx_news_search'), table_name='news_items')
    op.drop_index(op.f('idx_news_company'), table_name='news_items')
    op.drop_index(op.f('idx_news_category'), table_name='news_items')
    op.drop_index(op.f('idx_news_published'), table_name='news_items')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_companies_name'), table_name='companies')
    
    # Drop tables
    op.drop_table('scraper_state')
    op.drop_table('news_keywords')
    op.drop_table('user_activity')
    op.drop_table('user_preferences')
    op.drop_table('news_items')
    op.drop_table('users')
    op.drop_table('companies')
    
    # Drop types
    op.execute("DROP TYPE IF EXISTS activitytype")
    op.execute("DROP TYPE IF EXISTS notificationfrequency")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS news_category")