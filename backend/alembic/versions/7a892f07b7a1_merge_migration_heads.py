"""merge_migration_heads

Revision ID: 7a892f07b7a1
Revises: 73b129050e97, a1b2c3d4e5f6
Create Date: 2025-11-20 13:52:08.091487

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a892f07b7a1'
down_revision = ('73b129050e97', 'a1b2c3d4e5f6')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
