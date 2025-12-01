"""add_subscriptions_table

Revision ID: a1b2c3d4e5f9
Revises: c63eec1e5ba9
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from decimal import Decimal

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f9'
down_revision = 'c63eec1e5ba9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for subscription status
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscriptionstatus') THEN
                CREATE TYPE subscriptionstatus AS ENUM (
                    'trial',
                    'active',
                    'cancelled',
                    'expired'
                );
            END IF;
        END $$;
        """
    )
    subscription_status_enum = postgresql.ENUM(name="subscriptionstatus", create_type=False)

    # Create subscriptions table (with IF NOT EXISTS check)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'subscriptions'
            ) THEN
                CREATE TABLE subscriptions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    user_id UUID NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'trial',
                    plan_type VARCHAR(20) NOT NULL DEFAULT 'monthly',
                    price NUMERIC(10, 2) NOT NULL DEFAULT 29.00,
                    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                    trial_started_at TIMESTAMP WITH TIME ZONE,
                    trial_ends_at TIMESTAMP WITH TIME ZONE,
                    started_at TIMESTAMP WITH TIME ZONE,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    cancelled_at TIMESTAMP WITH TIME ZONE,
                    payment_provider VARCHAR(50),
                    payment_subscription_id VARCHAR(255),
                    subscription_metadata JSONB DEFAULT '{}',
                    CONSTRAINT fk_subscriptions_user_id FOREIGN KEY (user_id) 
                        REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT uq_subscriptions_user_id UNIQUE (user_id)
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS ix_subscriptions_id ON subscriptions(id);
                CREATE INDEX IF NOT EXISTS ix_subscriptions_created_at ON subscriptions(created_at);
                CREATE INDEX IF NOT EXISTS ix_subscriptions_updated_at ON subscriptions(updated_at);
                CREATE INDEX IF NOT EXISTS idx_subscription_user_id ON subscriptions(user_id);
                CREATE INDEX IF NOT EXISTS idx_subscription_status ON subscriptions(status);
                CREATE INDEX IF NOT EXISTS idx_subscription_trial_ends_at ON subscriptions(trial_ends_at);
                CREATE INDEX IF NOT EXISTS idx_subscription_expires_at ON subscriptions(expires_at);
                
                -- Add comment to table
                COMMENT ON TABLE subscriptions IS 'User subscriptions and trials';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Drop indexes (with IF EXISTS check)
    op.execute("DROP INDEX IF EXISTS idx_subscription_expires_at")
    op.execute("DROP INDEX IF EXISTS idx_subscription_trial_ends_at")
    op.execute("DROP INDEX IF EXISTS idx_subscription_status")
    op.execute("DROP INDEX IF EXISTS idx_subscription_user_id")
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_created_at")
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_id")

    # Drop table (with IF EXISTS check)
    op.execute("DROP TABLE IF EXISTS subscriptions")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")

