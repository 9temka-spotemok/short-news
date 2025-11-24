"""create reports table

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2025-01-XX 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for report status
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reportstatus') THEN
                CREATE TYPE reportstatus AS ENUM ('processing', 'ready', 'error');
            END IF;
        END $$;
        """
    )
    report_status_enum = postgresql.ENUM(name="reportstatus", create_type=False)

    # Create reports table
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.String(500), nullable=False, comment="Company name or URL query"),
        sa.Column("status", report_status_enum, nullable=False, server_default=sa.text("'processing'"), comment="Report generation status"),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Associated company (if found/created)"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Error message if status is error"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="When report generation completed"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
    )

    # Create indexes
    op.create_index("ix_reports_id", "reports", ["id"], unique=False)
    op.create_index("ix_reports_created_at", "reports", ["created_at"], unique=False)
    op.create_index("ix_reports_user_id", "reports", ["user_id"], unique=False)
    op.create_index("ix_reports_company_id", "reports", ["company_id"], unique=False)
    op.create_index("ix_reports_status", "reports", ["status"], unique=False)
    op.create_index("idx_report_user_status", "reports", ["user_id", "status"], unique=False)
    op.create_index("idx_report_created_at", "reports", ["created_at"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_report_created_at", table_name="reports")
    op.drop_index("idx_report_user_status", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_company_id", table_name="reports")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_reports_id", table_name="reports")

    # Drop table
    op.drop_table("reports")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS reportstatus")

