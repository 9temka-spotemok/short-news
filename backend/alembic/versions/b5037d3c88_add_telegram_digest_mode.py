"""add telegram digest mode

Revision ID: b5037d3c88
Revises: e1f2g3h4i5j6
Create Date: 2025-10-24 16:42:05.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b5037d3c88'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create telegram_digest_mode enum
    op.execute("CREATE TYPE telegram_digest_mode AS ENUM ('all', 'tracked')")
    
    # Add telegram_digest_mode column to user_preferences table
    op.add_column('user_preferences', 
                  sa.Column('telegram_digest_mode', 
                           postgresql.ENUM('all', 'tracked', name='telegram_digest_mode'), 
                           nullable=True, 
                           default='all'))


def downgrade() -> None:
    # Remove telegram_digest_mode column
    op.drop_column('user_preferences', 'telegram_digest_mode')
    
    # Drop telegram_digest_mode enum
    op.execute("DROP TYPE telegram_digest_mode")
