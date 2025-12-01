"""create_competitor_monitoring_matrices

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-01-27 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create competitor_monitoring_matrices table
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'competitor_monitoring_matrices'
            ) THEN
                CREATE TABLE competitor_monitoring_matrices (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    company_id UUID NOT NULL UNIQUE,
                    monitoring_config JSONB NOT NULL DEFAULT '{}',
                    social_media_sources JSONB NOT NULL DEFAULT '{}',
                    website_sources JSONB NOT NULL DEFAULT '{}',
                    news_sources JSONB NOT NULL DEFAULT '{}',
                    marketing_sources JSONB NOT NULL DEFAULT '{}',
                    seo_signals JSONB NOT NULL DEFAULT '{}',
                    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    CONSTRAINT fk_competitor_monitoring_matrix_company_id 
                        FOREIGN KEY (company_id) 
                        REFERENCES companies(id) ON DELETE CASCADE
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS ix_competitor_monitoring_matrices_company_id 
                    ON competitor_monitoring_matrices(company_id);
                CREATE INDEX IF NOT EXISTS ix_competitor_monitoring_matrices_last_updated 
                    ON competitor_monitoring_matrices(last_updated);
                CREATE INDEX IF NOT EXISTS ix_competitor_monitoring_matrix_company_updated 
                    ON competitor_monitoring_matrices(company_id, last_updated);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_competitor_monitoring_matrix_company_updated")
    op.execute("DROP INDEX IF EXISTS ix_competitor_monitoring_matrices_last_updated")
    op.execute("DROP INDEX IF EXISTS ix_competitor_monitoring_matrices_company_id")
    
    # Drop table
    op.execute("DROP TABLE IF EXISTS competitor_monitoring_matrices")








