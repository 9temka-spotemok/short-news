"""validate enum values lowercase

Revision ID: 73b129050e97
Revises: 
Create Date: 2025-11-14 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '73b129050e97'
down_revision = '2b1c3d4e5f6g'  # Last migration in the chain
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Validate that enum newscategory has lowercase values.
    This migration checks and logs the current state of enum values.
    It does not modify anything, just validates consistency.
    """
    connection = op.get_bind()
    
    # Check if newscategory enum exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'newscategory'
        )
    """))
    
    enum_exists = result.scalar()
    
    if not enum_exists:
        print("⚠️  WARNING: Enum 'newscategory' does not exist. Skipping validation.")
        return
    
    # Get all enum values
    result = connection.execute(text("""
        SELECT enumlabel 
        FROM pg_enum 
        WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'newscategory')
        ORDER BY enumsortorder
    """))
    
    enum_values = [row[0] for row in result]
    
    # Expected lowercase values
    expected_values = [
        'product_update', 'pricing_change', 'strategic_announcement',
        'technical_update', 'funding_news', 'research_paper', 'community_event',
        'partnership', 'acquisition', 'integration', 'security_update',
        'api_update', 'model_release', 'performance_improvement', 'feature_deprecation'
    ]
    
    # Check for UPPERCASE values
    uppercase_values = [v for v in enum_values if v.isupper()]
    
    if uppercase_values:
        print(f"⚠️  WARNING: Found UPPERCASE enum values in newscategory: {uppercase_values}")
        print(f"   Current enum values: {enum_values}")
        print(f"   Expected lowercase values: {expected_values}")
        print("   This may cause errors in queries. Please review the enum definition.")
    else:
        print(f"✅ Enum 'newscategory' has correct lowercase values: {enum_values}")
    
    # Check if all expected values are present
    missing_values = set(expected_values) - set(enum_values)
    if missing_values:
        print(f"⚠️  WARNING: Missing enum values: {missing_values}")
    
    extra_values = set(enum_values) - set(expected_values)
    if extra_values:
        print(f"ℹ️  INFO: Extra enum values (not in expected list): {extra_values}")


def downgrade() -> None:
    """
    No-op: This is a validation-only migration.
    """
    pass
