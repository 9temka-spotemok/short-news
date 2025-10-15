"""fix enum type names

Revision ID: e1f2g3h4i5j6
Revises: d5e6f7g8h9i0
Create Date: 2025-10-14 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e1f2g3h4i5j6'
down_revision = 'd5e6f7g8h9i0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix notification_frequency enum name
    # First, check if the old enum exists and rename it
    op.execute("""
        DO $$ 
        BEGIN
            -- Check if notificationfrequency exists and notification_frequency doesn't
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationfrequency') 
               AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_frequency') THEN
                -- Rename the enum type
                ALTER TYPE notificationfrequency RENAME TO notification_frequency;
            END IF;
        END $$;
    """)
    
    # Fix digest_frequency enum name if needed
    op.execute("""
        DO $$ 
        BEGIN
            -- Check if digestfrequency exists and digest_frequency doesn't
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'digestfrequency') 
               AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'digest_frequency') THEN
                -- Rename the enum type
                ALTER TYPE digestfrequency RENAME TO digest_frequency;
            END IF;
        END $$;
    """)
    
    # Fix digest_format enum name if needed
    op.execute("""
        DO $$ 
        BEGIN
            -- Check if digestformat exists and digest_format doesn't
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'digestformat') 
               AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'digest_format') THEN
                -- Rename the enum type
                ALTER TYPE digestformat RENAME TO digest_format;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Rename back to old names if needed
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_frequency') THEN
                ALTER TYPE notification_frequency RENAME TO notificationfrequency;
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'digest_frequency') THEN
                ALTER TYPE digest_frequency RENAME TO digestfrequency;
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'digest_format') THEN
                ALTER TYPE digest_format RENAME TO digestformat;
            END IF;
        END $$;
    """)
