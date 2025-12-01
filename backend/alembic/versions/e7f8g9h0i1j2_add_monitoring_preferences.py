"""add monitoring preferences

Revision ID: e7f8g9h0i1j2
Revises: a1b2c3d4e5f9
Create Date: 2025-11-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7f8g9h0i1j2"
down_revision = "a1b2c3d4e5f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add monitoring_enabled
    op.add_column(
        "user_preferences",
        sa.Column("monitoring_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Create monitoring_frequency enum if it does not exist
    op.execute(
        """
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'monitoring_frequency') THEN
                CREATE TYPE monitoring_frequency AS ENUM ('hourly', '6h', 'daily', 'weekly');
            END IF;
        END $$;
        """
    )

    # Add monitoring_check_frequency
    op.add_column(
        "user_preferences",
        sa.Column(
            "monitoring_check_frequency",
            sa.Enum("hourly", "6h", "daily", "weekly", name="monitoring_frequency"),
            nullable=False,
            server_default="daily",
        ),
    )

    # Add other monitoring fields
    op.add_column(
        "user_preferences",
        sa.Column(
            "monitoring_notify_on_changes", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column("monitoring_change_types", sa.JSON(), nullable=True),
    )
    op.add_column(
        "user_preferences",
        sa.Column("monitoring_auto_refresh", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "user_preferences",
        sa.Column("monitoring_notification_channels", sa.JSON(), nullable=True),
    )

    # Set default values for JSON columns where NULL
    op.execute(
        """
        UPDATE user_preferences 
        SET monitoring_change_types = '[
            "website_structure",
            "marketing_banner",
            "marketing_landing",
            "marketing_product",
            "marketing_jobs",
            "seo_meta",
            "seo_structure",
            "pricing"
        ]'::jsonb
        WHERE monitoring_change_types IS NULL;
        """
    )

    op.execute(
        """
        UPDATE user_preferences 
        SET monitoring_notification_channels = '{"email": true, "telegram": false}'::jsonb
        WHERE monitoring_notification_channels IS NULL;
        """
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "monitoring_notification_channels")
    op.drop_column("user_preferences", "monitoring_auto_refresh")
    op.drop_column("user_preferences", "monitoring_change_types")
    op.drop_column("user_preferences", "monitoring_notify_on_changes")
    op.drop_column("user_preferences", "monitoring_check_frequency")
    op.drop_column("user_preferences", "monitoring_enabled")
    op.execute("DROP TYPE IF EXISTS monitoring_frequency;")


