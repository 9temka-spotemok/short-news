"""add analytics models and knowledge graph tables

Revision ID: 2b1c3d4e5f6g
Revises: 1f2a3b4c5d6e
Create Date: 2025-11-09 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2b1c3d4e5f6g"
down_revision = "1f2a3b4c5d6e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'analyticsperiod') THEN
                CREATE TYPE analyticsperiod AS ENUM ('daily', 'weekly', 'monthly');
            END IF;
        END $$;
        """
    )
    analytics_period_enum = postgresql.ENUM(name="analyticsperiod", create_type=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'impactcomponenttype') THEN
                CREATE TYPE impactcomponenttype AS ENUM (
                    'news_signal',
                    'pricing_change',
                    'feature_release',
                    'funding_event',
                    'community_event',
                    'other'
                );
            END IF;
        END $$;
        """
    )
    impact_component_enum = postgresql.ENUM(name="impactcomponenttype", create_type=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'analyticsentitytype') THEN
                CREATE TYPE analyticsentitytype AS ENUM (
                    'company',
                    'news_item',
                    'change_event',
                    'pricing_snapshot',
                    'product',
                    'feature',
                    'team',
                    'metric',
                    'external'
                );
            END IF;
        END $$;
        """
    )
    analytics_entity_enum = postgresql.ENUM(name="analyticsentitytype", create_type=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'relationshiptype') THEN
                CREATE TYPE relationshiptype AS ENUM ('causes', 'correlated_with', 'follows', 'amplifies', 'depends_on');
            END IF;
        END $$;
        """
    )
    relationship_enum = postgresql.ENUM(name="relationshiptype", create_type=False)

    op.create_table(
        "company_analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period", analytics_period_enum, nullable=False),
        sa.Column("news_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("news_positive", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("news_negative", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("news_neutral", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("news_average_sentiment", sa.Float(), nullable=False, server_default="0"),
        sa.Column("news_average_priority", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pricing_changes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_updates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("funding_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impact_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("innovation_velocity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trend_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metric_breakdown", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "period_start", "period", name="uq_company_snapshot_period"),
    )
    op.create_index(
        "ix_company_snapshot_company_period",
        "company_analytics_snapshots",
        ["company_id", "period", "period_start"],
        unique=False,
    )

    op.create_table(
        "impact_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_type", impact_component_enum, nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_contribution", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_entity_type", analytics_entity_enum, nullable=True),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["company_analytics_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_impact_components_snapshot", "impact_components", ["snapshot_id"], unique=False)
    op.create_index("ix_impact_components_company", "impact_components", ["company_id"], unique=False)

    op.create_table(
        "analytics_graph_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_entity_type", analytics_entity_enum, nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_type", analytics_entity_enum, nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", relationship_enum, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_analytics_graph_edge",
        ),
    )
    op.create_index("ix_analytics_graph_company", "analytics_graph_edges", ["company_id"], unique=False)
    op.create_index("ix_analytics_graph_source", "analytics_graph_edges", ["source_entity_id"], unique=False)
    op.create_index("ix_analytics_graph_target", "analytics_graph_edges", ["target_entity_id"], unique=False)

    op.create_table(
        "user_report_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("companies", postgresql.ARRAY(postgresql.UUID()), nullable=False, server_default=sa.text("'{}'::uuid[]")),
        sa.Column("filters", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("visualization_config", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_presets_user", "user_report_presets", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_report_presets_user", table_name="user_report_presets")
    op.drop_table("user_report_presets")

    op.drop_index("ix_analytics_graph_target", table_name="analytics_graph_edges")
    op.drop_index("ix_analytics_graph_source", table_name="analytics_graph_edges")
    op.drop_index("ix_analytics_graph_company", table_name="analytics_graph_edges")
    op.drop_table("analytics_graph_edges")

    op.drop_index("ix_impact_components_company", table_name="impact_components")
    op.drop_index("ix_impact_components_snapshot", table_name="impact_components")
    op.drop_table("impact_components")

    op.drop_index("ix_company_snapshot_company_period", table_name="company_analytics_snapshots")
    op.drop_table("company_analytics_snapshots")

    relationship_enum = postgresql.ENUM(name="relationshiptype")
    relationship_enum.drop(op.get_bind(), checkfirst=True)

    analytics_entity_enum = postgresql.ENUM(name="analyticsentitytype")
    analytics_entity_enum.drop(op.get_bind(), checkfirst=True)

    impact_component_enum = postgresql.ENUM(name="impactcomponenttype")
    impact_component_enum.drop(op.get_bind(), checkfirst=True)

    analytics_period_enum = postgresql.ENUM(name="analyticsperiod")
    analytics_period_enum.drop(op.get_bind(), checkfirst=True)


