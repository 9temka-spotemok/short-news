"""add_digest_and_notifications

Revision ID: c1d2e3f4g5h6
Revises: b5037d3c878c
Create Date: 2025-10-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'b5037d3c878c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new enum types with checkfirst
    digest_frequency_enum = postgresql.ENUM('daily', 'weekly', 'custom', name='digest_frequency', create_type=False)
    digest_frequency_enum.create(op.get_bind(), checkfirst=True)
    
    digest_format_enum = postgresql.ENUM('short', 'detailed', name='digest_format', create_type=False)
    digest_format_enum.create(op.get_bind(), checkfirst=True)
    
    notification_type_enum = postgresql.ENUM(
        'new_news', 'company_active', 'pricing_change', 'funding_announcement',
        'product_launch', 'category_trend', 'keyword_match', 'competitor_milestone',
        name='notification_type', create_type=False
    )
    notification_type_enum.create(op.get_bind(), checkfirst=True)
    
    notification_priority_enum = postgresql.ENUM('low', 'medium', 'high', name='notification_priority', create_type=False)
    notification_priority_enum.create(op.get_bind(), checkfirst=True)
    
    # Add digest settings columns to user_preferences
    op.add_column('user_preferences', sa.Column('digest_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('user_preferences', sa.Column('digest_frequency', digest_frequency_enum, nullable=True, server_default='daily'))
    op.add_column('user_preferences', sa.Column('digest_custom_schedule', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'))
    op.add_column('user_preferences', sa.Column('digest_format', digest_format_enum, nullable=True, server_default='short'))
    op.add_column('user_preferences', sa.Column('digest_include_summaries', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('user_preferences', sa.Column('telegram_chat_id', sa.String(length=255), nullable=True))
    op.add_column('user_preferences', sa.Column('telegram_enabled', sa.Boolean(), nullable=True, server_default='false'))
    
    # Create notification_settings table
    op.create_table(
        'notification_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notification_types', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('min_priority_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('company_alerts', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('category_trends', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('keyword_alerts', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_notification_settings_user_id'), 'notification_settings', ['user_id'], unique=False)
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', notification_type_enum, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('is_read', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('priority', notification_priority_enum, nullable=True, server_default='medium'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    
    # Create competitor_comparisons table
    op.create_table(
        'competitor_comparisons',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_ids', postgresql.ARRAY(postgresql.UUID()), nullable=False),
        sa.Column('date_from', sa.DateTime(), nullable=False),
        sa.Column('date_to', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_competitor_comparisons_user_id'), 'competitor_comparisons', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f('ix_competitor_comparisons_user_id'), table_name='competitor_comparisons')
    op.drop_table('competitor_comparisons')
    
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
    
    op.drop_index(op.f('ix_notification_settings_user_id'), table_name='notification_settings')
    op.drop_table('notification_settings')
    
    # Remove columns from user_preferences
    op.drop_column('user_preferences', 'telegram_enabled')
    op.drop_column('user_preferences', 'telegram_chat_id')
    op.drop_column('user_preferences', 'digest_include_summaries')
    op.drop_column('user_preferences', 'digest_format')
    op.drop_column('user_preferences', 'digest_custom_schedule')
    op.drop_column('user_preferences', 'digest_frequency')
    op.drop_column('user_preferences', 'digest_enabled')
    
    # Drop enum types
    notification_priority_enum = postgresql.ENUM(name='notification_priority')
    notification_priority_enum.drop(op.get_bind())
    
    notification_type_enum = postgresql.ENUM(name='notification_type')
    notification_type_enum.drop(op.get_bind())
    
    digest_format_enum = postgresql.ENUM(name='digest_format')
    digest_format_enum.drop(op.get_bind())
    
    digest_frequency_enum = postgresql.ENUM(name='digest_frequency')
    digest_frequency_enum.drop(op.get_bind())

