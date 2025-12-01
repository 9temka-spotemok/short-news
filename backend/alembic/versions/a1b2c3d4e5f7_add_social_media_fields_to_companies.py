"""add_social_media_fields_to_companies

Revision ID: a1b2c3d4e5f7
Revises: 8f2abc2f1342
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f7'
down_revision = '8f2abc2f1342'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add social media URL columns to companies table
    op.execute(
        """
        DO $$
        BEGIN
            -- Add Facebook URL
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'companies' AND column_name = 'facebook_url'
            ) THEN
                ALTER TABLE companies ADD COLUMN facebook_url VARCHAR(500);
            END IF;
            
            -- Add Instagram URL
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'companies' AND column_name = 'instagram_url'
            ) THEN
                ALTER TABLE companies ADD COLUMN instagram_url VARCHAR(500);
            END IF;
            
            -- Add LinkedIn URL
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'companies' AND column_name = 'linkedin_url'
            ) THEN
                ALTER TABLE companies ADD COLUMN linkedin_url VARCHAR(500);
            END IF;
            
            -- Add YouTube URL
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'companies' AND column_name = 'youtube_url'
            ) THEN
                ALTER TABLE companies ADD COLUMN youtube_url VARCHAR(500);
            END IF;
            
            -- Add TikTok URL
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'companies' AND column_name = 'tiktok_url'
            ) THEN
                ALTER TABLE companies ADD COLUMN tiktok_url VARCHAR(500);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Remove social media URL columns
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS tiktok_url")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS youtube_url")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS linkedin_url")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS instagram_url")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS facebook_url")








