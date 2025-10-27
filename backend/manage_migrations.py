#!/usr/bin/env python3
"""
Enhanced migration management script
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def get_next_revision_id():
    """Generate next revision ID based on existing migrations"""
    versions_dir = Path(__file__).parent / "alembic" / "versions"
    
    if not versions_dir.exists():
        return "0001"
    
    # Get all migration files
    migration_files = [f for f in versions_dir.glob("*.py") if not f.name.startswith("__")]
    
    if not migration_files:
        return "0001"
    
    # Extract revision IDs and find the highest
    max_id = 0
    for file in migration_files:
        # Extract first 10 characters as revision ID
        revision_id = file.name[:10]
        try:
            # Convert to int for comparison
            id_num = int(revision_id, 16)  # Assuming hex format
            max_id = max(max_id, id_num)
        except ValueError:
            continue
    
    # Generate next ID
    next_id = max_id + 1
    return f"{next_id:010x}"

def create_migration(message: str):
    """Create a new migration with the given message"""
    
    # Get the backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Generate revision ID
    revision_id = get_next_revision_id()
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.000000")
    
    # Create migration file content
    migration_content = f'''"""add telegram digest mode

Revision ID: {revision_id}
Revises: e1f2g3h4i5j6
Create Date: {timestamp}

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
    # Create telegram_digest_mode enum
    op.execute("CREATE TYPE telegram_digest_mode AS ENUM ('all', 'tracked')")
    
    # Add telegram_digest_mode column to user_preferences table
    op.add_column('user_preferences', 
                  sa.Column('telegram_digest_mode', 
                           postgresql.ENUM('all', 'tracked', name='telegram_digest_mode'), 
                           nullable=True, 
                           default='all'))


def downgrade() -> None:
    # Remove telegram_digest_mode column
    op.drop_column('user_preferences', 'telegram_digest_mode')
    
    # Drop telegram_digest_mode enum
    op.execute("DROP TYPE telegram_digest_mode")
'''
    
    # Write migration file
    migration_file = backend_dir / "alembic" / "versions" / f"{revision_id}_add_telegram_digest_mode.py"
    
    try:
        with open(migration_file, 'w', encoding='utf-8') as f:
            f.write(migration_content)
        
        print(f"SUCCESS: Migration created successfully!")
        print(f"File: {migration_file}")
        print(f"Revision ID: {revision_id}")
        print(f"Message: {message}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error creating migration file: {e}")
        return False

def apply_migrations():
    """Apply all pending migrations"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    try:
        cmd = [sys.executable, '-m', 'alembic', 'upgrade', 'head']
        
        print("Applying migrations...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("SUCCESS: Migrations applied successfully!")
            if result.stdout:
                print(result.stdout)
        else:
            print("ERROR: Error applying migrations:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"ERROR: Exception: {e}")
        return False
    
    return True

def show_migration_history():
    """Show migration history"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    try:
        cmd = [sys.executable, '-m', 'alembic', 'history']
        
        print("Migration history:")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("ERROR: Error showing history:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"ERROR: Exception: {e}")
        return False
    
    return True

def show_current_revision():
    """Show current database revision"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    try:
        cmd = [sys.executable, '-m', 'alembic', 'current']
        
        print("Current database revision:")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("ERROR: Error showing current revision:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"ERROR: Exception: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Migration Management Script")
        print("")
        print("Usage:")
        print("  python manage_migrations.py create <message>  - Create new migration")
        print("  python manage_migrations.py apply              - Apply migrations")
        print("  python manage_migrations.py history          - Show migration history")
        print("  python manage_migrations.py current          - Show current revision")
        print("")
        print("Examples:")
        print("  python manage_migrations.py create 'add user preferences'")
        print("  python manage_migrations.py apply")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("ERROR: Please provide a migration message")
            print("Example: python manage_migrations.py create 'add new field'")
            sys.exit(1)
        message = sys.argv[2]
        success = create_migration(message)
    elif command == "apply":
        success = apply_migrations()
    elif command == "history":
        success = show_migration_history()
    elif command == "current":
        success = show_current_revision()
    else:
        print(f"ERROR: Unknown command: {command}")
        print("Available commands: create, apply, history, current")
        sys.exit(1)
    
    sys.exit(0 if success else 1)
