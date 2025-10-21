#!/usr/bin/env python3
"""
Railway startup script for shot-news API
"""
import os
import sys
import uvicorn

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == "__main__":
    # Get port from environment variable, default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    print(f"Starting server on port {port}")
    
    # Start the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
