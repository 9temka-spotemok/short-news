#!/usr/bin/env python3
"""
Quick migration creation script
Usage: python quick_migration.py "migration message"
"""

import sys
import os
from pathlib import Path
from datetime import datetime

def create_quick_migration(message: str):
    """Create a migration quickly without complex logic"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Generate simple revision ID based on timestamp
    timestamp = datetime.now()
    revision_id = f"{timestamp.strftime('%Y%m%d%H%M')}"
    
    # Get current timestamp
    create_date = timestamp.strftime("%Y-%m-%d %H:%M:%S.000000")
    
    # Create migration file content
    migration_content = f'''"""add telegram digest mode

Revision ID: {revision_id}
Revises: e1f2g3h4i5j6
Create Date: {create_date}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # TODO: Add your migration code here
    # Example:
    # op.add_column('table_name', sa.Column('new_field', sa.String(255), nullable=True))
    pass


def downgrade() -> None:
    # TODO: Add your rollback code here
    # Example:
    # op.drop_column('table_name', 'new_field')
    pass
'''
    
    # Write migration file
    migration_file = backend_dir / "alembic" / "versions" / f"{revision_id}_{message.replace(' ', '_')}.py"
    
    try:
        with open(migration_file, 'w', encoding='utf-8') as f:
            f.write(migration_content)
        
        print(f"SUCCESS: Migration created!")
        print(f"File: {migration_file}")
        print(f"Revision ID: {revision_id}")
        print(f"Message: {message}")
        print("")
        print("Next steps:")
        print("1. Edit the migration file to add your changes")
        print("2. Run: python manage_migrations.py apply")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Quick Migration Creator")
        print("Usage: python quick_migration.py \"migration message\"")
        print("Example: python quick_migration.py \"add user preferences\"")
        sys.exit(1)
    
    message = sys.argv[1]
    success = create_quick_migration(message)
    sys.exit(0 if success else 1)
