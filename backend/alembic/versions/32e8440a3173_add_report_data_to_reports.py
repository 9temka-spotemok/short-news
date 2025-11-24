"""add_report_data_to_reports

Revision ID: 32e8440a3173
Revises: 7a892f07b7a1
Create Date: 2025-11-21 14:10:22.435564

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '32e8440a3173'
down_revision = '7a892f07b7a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add report_data column to reports table
    op.add_column(
        'reports',
        sa.Column(
            'report_data',
            postgresql.JSON,
            nullable=True,
            comment='Report data (company, news, categories, sources, pricing, competitors)'
        )
    )


def downgrade() -> None:
    # Remove report_data column from reports table
    op.drop_column('reports', 'report_data')
