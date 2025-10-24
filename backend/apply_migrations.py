#!/usr/bin/env python3
"""
Script to apply database migrations when database is available
"""

import os
import sys
import subprocess
from pathlib import Path

def apply_migrations():
    """Apply all pending migrations to the database"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    try:
        # Try to apply migrations using alembic
        cmd = [sys.executable, '-m', 'alembic', 'upgrade', 'head']
        
        print("Applying database migrations...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("SUCCESS: Migrations applied successfully!")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print("ERROR: Failed to apply migrations:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"ERROR: Exception: {e}")
        return False

def check_database_connection():
    """Check if database is accessible"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    try:
        # Try to check current revision
        cmd = [sys.executable, '-m', 'alembic', 'current']
        
        print("Checking database connection...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("SUCCESS: Database is accessible!")
            if result.stdout:
                print(f"Current revision: {result.stdout.strip()}")
            return True
        else:
            print("ERROR: Database is not accessible:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"ERROR: Exception: {e}")
        return False

def show_migration_status():
    """Show migration status"""
    
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    try:
        # Show migration history
        cmd = [sys.executable, '-m', 'alembic', 'history']
        
        print("Migration history:")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("ERROR: Failed to show history:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"ERROR: Exception: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Database Migration Tool")
        print("")
        print("Usage:")
        print("  python apply_migrations.py check     - Check database connection")
        print("  python apply_migrations.py apply     - Apply migrations")
        print("  python apply_migrations.py status    - Show migration status")
        print("")
        print("Examples:")
        print("  python apply_migrations.py check")
        print("  python apply_migrations.py apply")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        success = check_database_connection()
    elif command == "apply":
        success = apply_migrations()
    elif command == "status":
        success = show_migration_status()
    else:
        print(f"ERROR: Unknown command: {command}")
        print("Available commands: check, apply, status")
        sys.exit(1)
    
    sys.exit(0 if success else 1)
