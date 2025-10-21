#!/usr/bin/env python3
"""
Universal startup script for shot-news API
Works with Railway, Heroku, and other platforms
"""
import os
import sys
import uvicorn

def get_port():
    """Get port from environment variable with fallbacks"""
    # Try different environment variable names
    port_str = os.environ.get("PORT") or os.environ.get("PORT_NUMBER") or "8000"
    
    try:
        port = int(port_str)
        return port
    except ValueError:
        print(f"Warning: Invalid port value '{port_str}', using default 8000")
        return 8000

def main():
    port = get_port()
    print(f"Starting server on port {port}")
    print(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
    
    # Start the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
