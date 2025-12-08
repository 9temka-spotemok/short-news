"""Add enum types

Revision ID: 28c9c8f54d42
Revises: 
Create Date: 2025-10-07 11:20:26.621381

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '28c9c8f54d42'
down_revision = 'initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: enum conversions are skipped to avoid type casting issues on existing data.
    pass


def downgrade() -> None:
    # No-op downgrade
    pass
