"""add_onboarding_sessions_table

Revision ID: 8f2abc2f1342
Revises: 32e8440a3173
Create Date: 2025-11-24 20:14:42.149760

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8f2abc2f1342'
down_revision = '32e8440a3173'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for onboarding step
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'onboardingstep') THEN
                CREATE TYPE onboardingstep AS ENUM (
                    'company_input',
                    'company_card',
                    'competitor_selection',
                    'observation_setup',
                    'subscription_confirm',
                    'completed'
                );
            END IF;
        END $$;
        """
    )
    onboarding_step_enum = postgresql.ENUM(name="onboardingstep", create_type=False)

    # Create onboarding_sessions table (with IF NOT EXISTS check)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'onboarding_sessions'
            ) THEN
                CREATE TABLE onboarding_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    user_id UUID,
                    session_token VARCHAR(255) NOT NULL,
                    current_step onboardingstep NOT NULL DEFAULT 'company_input',
                    company_data JSONB,
                    selected_competitors JSONB,
                    observation_config JSONB,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    CONSTRAINT fk_onboarding_user_id FOREIGN KEY (user_id) 
                        REFERENCES users(id) ON DELETE SET NULL,
                    CONSTRAINT uq_onboarding_session_token UNIQUE (session_token)
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS ix_onboarding_sessions_id ON onboarding_sessions(id);
                CREATE INDEX IF NOT EXISTS ix_onboarding_sessions_created_at ON onboarding_sessions(created_at);
                CREATE INDEX IF NOT EXISTS ix_onboarding_sessions_updated_at ON onboarding_sessions(updated_at);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_onboarding_session_token ON onboarding_sessions(session_token);
                CREATE INDEX IF NOT EXISTS idx_onboarding_user_id ON onboarding_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_onboarding_current_step ON onboarding_sessions(current_step);
                CREATE INDEX IF NOT EXISTS idx_onboarding_created_at ON onboarding_sessions(created_at);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Drop indexes (with IF EXISTS check)
    op.execute("DROP INDEX IF EXISTS idx_onboarding_created_at")
    op.execute("DROP INDEX IF EXISTS idx_onboarding_current_step")
    op.execute("DROP INDEX IF EXISTS idx_onboarding_user_id")
    op.execute("DROP INDEX IF EXISTS idx_onboarding_session_token")
    op.execute("DROP INDEX IF EXISTS ix_onboarding_sessions_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_onboarding_sessions_created_at")
    op.execute("DROP INDEX IF EXISTS ix_onboarding_sessions_id")

    # Drop table (with IF EXISTS check)
    op.execute("DROP TABLE IF EXISTS onboarding_sessions")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS onboardingstep")
