"""add news nlp logs table

Revision ID: 0a1b2c3d4e6
Revises: f7a8b9c0d1e2
Create Date: 2025-11-08 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0a1b2c3d4e6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'newsnlpstage'
            ) THEN
                CREATE TYPE newsnlpstage AS ENUM (
                    'classification',
                    'sentiment',
                    'priority',
                    'summary',
                    'keywords'
                );
            END IF;
        END $$;
        """
    )

    newsnlpstage_enum_existing = postgresql.ENUM(
        "classification",
        "sentiment",
        "priority",
        "summary",
        "keywords",
        name="newsnlpstage",
        create_type=False,
    )

    op.create_table(
        "news_nlp_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "news_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("news_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", newsnlpstage_enum_existing, nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.create_index("ix_news_nlp_logs_news_id", "news_nlp_logs", ["news_id"])
    op.create_index("idx_news_nlp_logs_stage", "news_nlp_logs", ["stage"])
    op.create_index("idx_news_nlp_logs_provider", "news_nlp_logs", ["provider"])


def downgrade() -> None:
    op.drop_index("idx_news_nlp_logs_provider", table_name="news_nlp_logs")
    op.drop_index("idx_news_nlp_logs_stage", table_name="news_nlp_logs")
    op.drop_index("ix_news_nlp_logs_news_id", table_name="news_nlp_logs")
    op.drop_table("news_nlp_logs")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'newsnlpstage'
            ) THEN
                DROP TYPE newsnlpstage;
            END IF;
        END $$;
        """
    )

    newsnlpstage_enum_existing = postgresql.ENUM(
        "classification",
        "sentiment",
        "priority",
        "summary",
        "keywords",
        name="newsnlpstage",
        create_type=False,
    )
