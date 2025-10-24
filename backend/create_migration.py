#!/usr/bin/env python3
"""
Script to create Alembic migrations automatically
"""

import os
import sys
import subprocess
from pathlib import Path

def create_migration(message: str):
    """Create a new migration with the given message"""
    
    # Get the backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Set environment variables for offline mode
    env = os.environ.copy()
    env['ALEMBIC_CONFIG'] = str(backend_dir / 'alembic.ini')
    
    try:
        # Create migration using alembic
        cmd = [
            sys.executable, '-m', 'alembic', 
            'revision', '--autogenerate', 
            '-m', message
        ]
        
        print(f"Creating migration: {message}")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            print("✅ Migration created successfully!")
            print(result.stdout)
        else:
            print("❌ Error creating migration:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False
    
    return True

def apply_migrations():
    """Apply all pending migrations"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    env = os.environ.copy()
    env['ALEMBIC_CONFIG'] = str(backend_dir / 'alembic.ini')
    
    try:
        cmd = [sys.executable, '-m', 'alembic', 'upgrade', 'head']
        
        print("Applying migrations...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            print("✅ Migrations applied successfully!")
            print(result.stdout)
        else:
            print("❌ Error applying migrations:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False
    
    return True

def show_migration_history():
    """Show migration history"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    env = os.environ.copy()
    env['ALEMBIC_CONFIG'] = str(backend_dir / 'alembic.ini')
    
    try:
        cmd = [sys.executable, '-m', 'alembic', 'history']
        
        print("Migration history:")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ Error showing history:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python create_migration.py create <message>  - Create new migration")
        print("  python create_migration.py apply            - Apply migrations")
        print("  python create_migration.py history          - Show migration history")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Please provide a migration message")
            sys.exit(1)
        message = sys.argv[2]
        success = create_migration(message)
    elif command == "apply":
        success = apply_migrations()
    elif command == "history":
        success = show_migration_history()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)
