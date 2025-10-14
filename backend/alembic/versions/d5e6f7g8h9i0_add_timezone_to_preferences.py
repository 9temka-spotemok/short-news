"""add timezone to preferences

Revision ID: d5e6f7g8h9i0
Revises: c1d2e3f4g5h6
Create Date: 2025-10-14 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e6f7g8h9i0'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add timezone field to user_preferences
    op.add_column('user_preferences', 
        sa.Column('timezone', sa.String(length=50), nullable=True, server_default='UTC')
    )
    
    # Add week_start_day field (0=Sunday, 1=Monday)
    op.add_column('user_preferences',
        sa.Column('week_start_day', sa.Integer(), nullable=True, server_default='0')
    )
    
    # Update existing rows to use UTC and Sunday as defaults
    op.execute("UPDATE user_preferences SET timezone = 'UTC' WHERE timezone IS NULL")
    op.execute("UPDATE user_preferences SET week_start_day = 0 WHERE week_start_day IS NULL")


def downgrade() -> None:
    op.drop_column('user_preferences', 'week_start_day')
    op.drop_column('user_preferences', 'timezone')

