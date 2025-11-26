"""add_expires_at_to_onboarding_sessions

Revision ID: 8e90453b54da
Revises: 8f2abc2f1342
Create Date: 2025-11-26 22:39:25.709537

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '8e90453b54da'
down_revision = '8f2abc2f1342'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add expires_at column to onboarding_sessions table
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'onboarding_sessions' 
                AND column_name = 'expires_at'
            ) THEN
                ALTER TABLE onboarding_sessions 
                ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
                
                -- Set expiration time for existing sessions: 24 hours from creation
                UPDATE onboarding_sessions 
                SET expires_at = created_at + INTERVAL '24 hours'
                WHERE expires_at IS NULL;
                
                -- Create index for expires_at
                CREATE INDEX IF NOT EXISTS idx_onboarding_expires_at 
                ON onboarding_sessions(expires_at);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Remove expires_at column
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'onboarding_sessions' 
                AND column_name = 'expires_at'
            ) THEN
                DROP INDEX IF EXISTS idx_onboarding_expires_at;
                ALTER TABLE onboarding_sessions DROP COLUMN expires_at;
            END IF;
        END $$;
        """
    )
