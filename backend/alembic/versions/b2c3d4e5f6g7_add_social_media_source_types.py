"""add_social_media_source_types

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f7
Create Date: 2025-01-27 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new social media source types to sourcetype enum
    # Note: PostgreSQL requires adding enum values one at a time
    # and they cannot be removed in downgrade (PostgreSQL limitation)
    op.execute(
        """
        DO $$
        BEGIN
            -- Add FACEBOOK if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'FACEBOOK' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sourcetype')
            ) THEN
                ALTER TYPE sourcetype ADD VALUE 'FACEBOOK';
            END IF;
            
            -- Add INSTAGRAM if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'INSTAGRAM' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sourcetype')
            ) THEN
                ALTER TYPE sourcetype ADD VALUE 'INSTAGRAM';
            END IF;
            
            -- Add LINKEDIN if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'LINKEDIN' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sourcetype')
            ) THEN
                ALTER TYPE sourcetype ADD VALUE 'LINKEDIN';
            END IF;
            
            -- Add YOUTUBE if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'YOUTUBE' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sourcetype')
            ) THEN
                ALTER TYPE sourcetype ADD VALUE 'YOUTUBE';
            END IF;
            
            -- Add TIKTOK if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'TIKTOK' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sourcetype')
            ) THEN
                ALTER TYPE sourcetype ADD VALUE 'TIKTOK';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave a comment indicating this limitation
    # In production, you would need to:
    # 1. Create a new enum without the values
    # 2. Update all columns to use the new enum
    # 3. Drop the old enum
    # This is a complex operation and should be done carefully
    pass




