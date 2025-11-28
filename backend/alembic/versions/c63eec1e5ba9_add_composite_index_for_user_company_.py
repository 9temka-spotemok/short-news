"""add_composite_index_for_user_company_joins

Revision ID: c63eec1e5ba9
Revises: 27f990c49949
Create Date: 2025-11-28 15:57:52.988757

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c63eec1e5ba9'
down_revision = '27f990c49949'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add composite index on companies(user_id, id) for optimizing JOIN queries.
    
    This index significantly improves performance when filtering news items
    by user_id through JOIN operations instead of IN clauses.
    """
    # Create composite index for optimizing JOIN queries
    # This index helps when querying: SELECT news_items.* FROM news_items 
    # JOIN companies ON news_items.company_id = companies.id 
    # WHERE companies.user_id = :user_id
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_companies_user_id_id "
        "ON companies(user_id, id) "
        "WHERE user_id IS NOT NULL"
    )


def downgrade() -> None:
    """Remove composite index."""
    op.execute("DROP INDEX IF EXISTS idx_companies_user_id_id")
