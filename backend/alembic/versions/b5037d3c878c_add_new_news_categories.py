"""add_new_news_categories

Revision ID: b5037d3c878c
Revises: 28c9c8f54d42
Create Date: 2025-10-09 16:20:54.534915

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5037d3c878c'
down_revision = '28c9c8f54d42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new values to news_category enum
    op.execute("ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'partnership'")
    op.execute("ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'acquisition'")
    op.execute("ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'integration'")
    op.execute("ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'security_update'")
    op.execute("ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'api_update'")
    op.execute("ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'model_release'")
    op.execute("ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'performance_improvement'")
    op.execute("ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'feature_deprecation'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # To properly downgrade, would need to recreate the enum type
    pass
