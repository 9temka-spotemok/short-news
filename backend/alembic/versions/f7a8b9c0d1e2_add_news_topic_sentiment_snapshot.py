"""add topic, sentiment and raw snapshot metadata to news

Revision ID: f7a8b9c0d1e2
Revises: b5037d3c88
Create Date: 2025-11-08 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "b5037d3c88"
branch_labels = None
depends_on = None


news_topic_enum = sa.Enum(
    "product",
    "strategy",
    "finance",
    "technology",
    "security",
    "research",
    "community",
    "talent",
    "regulation",
    "market",
    "other",
    name="newstopic",
)

sentiment_enum = sa.Enum(
    "positive",
    "neutral",
    "negative",
    "mixed",
    name="sentimentlabel",
)


def upgrade() -> None:
    bind = op.get_bind()
    news_topic_enum.create(bind, checkfirst=True)
    sentiment_enum.create(bind, checkfirst=True)

    op.add_column(
        "news_items",
        sa.Column("topic", news_topic_enum, nullable=True),
    )
    op.add_column(
        "news_items",
        sa.Column("sentiment", sentiment_enum, nullable=True),
    )
    op.add_column(
        "news_items",
        sa.Column("raw_snapshot_url", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("news_items", "raw_snapshot_url")
    op.drop_column("news_items", "sentiment")
    op.drop_column("news_items", "topic")

    bind = op.get_bind()
    sentiment_enum.drop(bind, checkfirst=True)
    news_topic_enum.drop(bind, checkfirst=True)


