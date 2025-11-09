"""add pricing snapshots and competitor change events

Revision ID: 1b2c3d4e5f67
Revises: 0a1b2c3d4e6
Create Date: 2025-11-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSON, UUID


# revision identifiers, used by Alembic.
revision = "1b2c3d4e5f67"
down_revision = "0a1b2c3d4e6"
branch_labels = None
depends_on = None


sourcetype_enum = ENUM(
    "blog",
    "twitter",
    "github",
    "reddit",
    "news_site",
    "press_release",
    name="sourcetype",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'competitorprocessingstatus'
            ) THEN
                CREATE TYPE competitorprocessingstatus AS ENUM ('success', 'skipped', 'error');
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'competitornotificationstatus'
            ) THEN
                CREATE TYPE competitornotificationstatus AS ENUM ('pending', 'sent', 'failed', 'skipped');
            END IF;
        END $$;
        """
    )

    processing_status_enum = ENUM(
        "success",
        "skipped",
        "error",
        name="competitorprocessingstatus",
        create_type=False,
    )

    notification_status_enum = ENUM(
        "pending",
        "sent",
        "failed",
        "skipped",
        name="competitornotificationstatus",
        create_type=False,
    )

    op.create_table(
        "competitor_pricing_snapshots",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("source_type", sourcetype_enum, nullable=False),
        sa.Column("data_hash", sa.String(length=64), nullable=True),
        sa.Column("normalized_data", JSON, nullable=True),
        sa.Column("raw_snapshot_url", sa.String(length=1000), nullable=True),
        sa.Column("parser_version", sa.String(length=32), nullable=False),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("extraction_metadata", JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("warnings", JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column(
            "processing_status",
            processing_status_enum,
            nullable=False,
            server_default=sa.text("'success'"),
        ),
        sa.Column("processing_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_competitor_pricing_snapshot_company_url",
        "competitor_pricing_snapshots",
        ["company_id", "source_url"],
    )
    op.create_index(
        op.f("ix_competitor_pricing_snapshots_data_hash"),
        "competitor_pricing_snapshots",
        ["data_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_pricing_snapshots_company_id"),
        "competitor_pricing_snapshots",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_pricing_snapshots_extracted_at"),
        "competitor_pricing_snapshots",
        ["extracted_at"],
        unique=False,
    )

    op.create_table(
        "competitor_change_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sourcetype_enum, nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("changed_fields", JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("raw_diff", JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "current_snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("competitor_pricing_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "previous_snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("competitor_pricing_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "processing_status",
            processing_status_enum,
            nullable=False,
            server_default=sa.text("'success'"),
        ),
        sa.Column(
            "notification_status",
            notification_status_enum,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_competitor_change_events_company_detected",
        "competitor_change_events",
        ["company_id", "detected_at"],
    )
    op.create_index(
        op.f("ix_competitor_change_events_company_id"),
        "competitor_change_events",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_change_events_detected_at"),
        "competitor_change_events",
        ["detected_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_competitor_change_events_detected_at"), table_name="competitor_change_events")
    op.drop_index(op.f("ix_competitor_change_events_company_id"), table_name="competitor_change_events")
    op.drop_index("ix_competitor_change_events_company_detected", table_name="competitor_change_events")
    op.drop_table("competitor_change_events")

    op.drop_index(op.f("ix_competitor_pricing_snapshots_extracted_at"), table_name="competitor_pricing_snapshots")
    op.drop_index(op.f("ix_competitor_pricing_snapshots_company_id"), table_name="competitor_pricing_snapshots")
    op.drop_index(op.f("ix_competitor_pricing_snapshots_data_hash"), table_name="competitor_pricing_snapshots")
    op.drop_index("ix_competitor_pricing_snapshot_company_url", table_name="competitor_pricing_snapshots")
    op.drop_table("competitor_pricing_snapshots")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'competitornotificationstatus'
            ) THEN
                DROP TYPE competitornotificationstatus;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'competitorprocessingstatus'
            ) THEN
                DROP TYPE competitorprocessingstatus;
            END IF;
        END $$;
        """
    )


