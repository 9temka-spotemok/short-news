"""add crawl schedules and notification channel tables

Revision ID: 1f2a3b4c5d6e
Revises: 1b2c3d4e5f67
Create Date: 2025-11-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1f2a3b4c5d6e"
down_revision = "1b2c3d4e5f67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crawlscope') THEN
                CREATE TYPE crawlscope AS ENUM ('source_type', 'company', 'source');
            END IF;
        END $$;
        """
    )
    crawl_scope_enum = postgresql.ENUM(name="crawlscope", create_type=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crawlmode') THEN
                CREATE TYPE crawlmode AS ENUM ('always_update', 'change_detection');
            END IF;
        END $$;
        """
    )
    crawl_mode_enum = postgresql.ENUM(name="crawlmode", create_type=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crawlstatus') THEN
                CREATE TYPE crawlstatus AS ENUM ('scheduled', 'running', 'success', 'failed', 'skipped');
            END IF;
        END $$;
        """
    )
    crawl_status_enum = postgresql.ENUM(name="crawlstatus", create_type=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationchanneltype') THEN
                CREATE TYPE notificationchanneltype AS ENUM ('email', 'telegram', 'webhook', 'slack', 'zapier');
            END IF;
        END $$;
        """
    )
    notification_channel_type_enum = postgresql.ENUM(name="notificationchanneltype", create_type=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationdeliverystatus') THEN
                CREATE TYPE notificationdeliverystatus AS ENUM ('pending', 'sent', 'failed', 'cancelled', 'retrying');
            END IF;
        END $$;
        """
    )
    notification_delivery_status_enum = postgresql.ENUM(name="notificationdeliverystatus", create_type=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationeventstatus') THEN
                CREATE TYPE notificationeventstatus AS ENUM ('queued', 'dispatched', 'delivered', 'failed', 'suppressed', 'expired');
            END IF;
        END $$;
        """
    )
    notification_event_status_enum = postgresql.ENUM(name="notificationeventstatus", create_type=False)

    op.create_table(
        "crawl_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", crawl_scope_enum, nullable=False),
        sa.Column("scope_value", sa.String(length=255), nullable=False),
        sa.Column("mode", crawl_mode_enum, nullable=False, server_default="always_update"),
        sa.Column("frequency_seconds", sa.Integer(), nullable=False, server_default="900"),
        sa.Column("jitter_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_backoff_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "scope_value", name="uq_crawl_schedule_scope"),
    )
    op.create_index(op.f("ix_crawl_schedules_scope"), "crawl_schedules", ["scope"], unique=False)
    op.create_index(op.f("ix_crawl_schedules_scope_value"), "crawl_schedules", ["scope_value"], unique=False)

    op.create_table(
        "source_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", postgresql.ENUM(name="sourcetype", create_type=False), nullable=False),
        sa.Column("mode", crawl_mode_enum, nullable=False, server_default="always_update"),
        sa.Column("last_content_hash", sa.String(length=255), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_no_change", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_id"], ["crawl_schedules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "source_type", name="uq_source_profile_company_source"),
    )
    op.create_index(op.f("ix_source_profiles_company_id"), "source_profiles", ["company_id"], unique=False)
    op.create_index(op.f("ix_source_profiles_source_type"), "source_profiles", ["source_type"], unique=False)

    op.create_table(
        "crawl_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", crawl_status_enum, nullable=False, server_default="scheduled"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("change_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["source_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_id"], ["crawl_schedules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crawl_runs_profile_id"), "crawl_runs", ["profile_id"], unique=False)
    op.create_index(op.f("ix_crawl_runs_status"), "crawl_runs", ["status"], unique=False)

    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_type", notification_channel_type_enum, nullable=False),
        sa.Column("destination", sa.String(length=500), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "channel_type", "destination", name="uq_notification_channel_destination"),
    )
    op.create_index(op.f("ix_notification_channels_channel_type"), "notification_channels", ["channel_type"], unique=False)
    op.create_index(op.f("ix_notification_channels_user_id"), "notification_channels", ["user_id"], unique=False)

    op.create_table(
        "notification_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_type", postgresql.ENUM(name="notification_type", create_type=False), nullable=False),
        sa.Column("priority", postgresql.ENUM(name="notification_priority", create_type=False), nullable=False, server_default="medium"),
        sa.Column(
            "payload",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("deduplication_key", sa.String(length=255), nullable=True),
        sa.Column("status", notification_event_status_enum, nullable=False, server_default="queued"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_events_status"), "notification_events", ["status"], unique=False)
    op.create_index(op.f("ix_notification_events_deduplication_key"), "notification_events", ["deduplication_key"], unique=False)
    op.create_index(op.f("ix_notification_events_notification_type"), "notification_events", ["notification_type"], unique=False)

    op.create_table(
        "notification_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_type", postgresql.ENUM(name="notification_type", create_type=False), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("frequency", sa.String(length=50), nullable=False, server_default="immediate"),
        sa.Column(
            "min_priority",
            postgresql.ENUM(name="notification_priority", create_type=False),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "filters",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["notification_channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "channel_id", "notification_type", name="uq_notification_subscription"),
    )
    op.create_index(op.f("ix_notification_subscriptions_notification_type"), "notification_subscriptions", ["notification_type"], unique=False)
    op.create_index(op.f("ix_notification_subscriptions_user_id"), "notification_subscriptions", ["user_id"], unique=False)

    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", notification_delivery_status_enum, nullable=False, server_default="pending"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "response_metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["notification_channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["notification_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_deliveries_status"), "notification_deliveries", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_deliveries_status"), table_name="notification_deliveries")
    op.drop_table("notification_deliveries")

    op.drop_index(op.f("ix_notification_subscriptions_user_id"), table_name="notification_subscriptions")
    op.drop_index(op.f("ix_notification_subscriptions_notification_type"), table_name="notification_subscriptions")
    op.drop_table("notification_subscriptions")

    op.drop_index(op.f("ix_notification_events_notification_type"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_deduplication_key"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_status"), table_name="notification_events")
    op.drop_table("notification_events")

    op.drop_index(op.f("ix_notification_channels_user_id"), table_name="notification_channels")
    op.drop_index(op.f("ix_notification_channels_channel_type"), table_name="notification_channels")
    op.drop_table("notification_channels")

    op.drop_index(op.f("ix_crawl_runs_status"), table_name="crawl_runs")
    op.drop_index(op.f("ix_crawl_runs_profile_id"), table_name="crawl_runs")
    op.drop_table("crawl_runs")

    op.drop_index(op.f("ix_source_profiles_source_type"), table_name="source_profiles")
    op.drop_index(op.f("ix_source_profiles_company_id"), table_name="source_profiles")
    op.drop_table("source_profiles")

    op.drop_index(op.f("ix_crawl_schedules_scope_value"), table_name="crawl_schedules")
    op.drop_index(op.f("ix_crawl_schedules_scope"), table_name="crawl_schedules")
    op.drop_table("crawl_schedules")

    notification_event_status_enum = postgresql.ENUM(name="notificationeventstatus")
    notification_event_status_enum.drop(op.get_bind(), checkfirst=True)

    notification_delivery_status_enum = postgresql.ENUM(name="notificationdeliverystatus")
    notification_delivery_status_enum.drop(op.get_bind(), checkfirst=True)

    notification_channel_type_enum = postgresql.ENUM(name="notificationchanneltype")
    notification_channel_type_enum.drop(op.get_bind(), checkfirst=True)

    crawl_status_enum = postgresql.ENUM(name="crawlstatus")
    crawl_status_enum.drop(op.get_bind(), checkfirst=True)

    crawl_mode_enum = postgresql.ENUM(name="crawlmode")
    crawl_mode_enum.drop(op.get_bind(), checkfirst=True)

    crawl_scope_enum = postgresql.ENUM(name="crawlscope")
    crawl_scope_enum.drop(op.get_bind(), checkfirst=True)


