#!/usr/bin/env python3
"""
Railway-specific startup script for shot-news API
This script handles Railway's PORT environment variable properly
"""
import os
import sys
import uvicorn

def main():
    # Get port from environment variable
    port_str = os.environ.get("PORT")
    
    if not port_str:
        print("ERROR: PORT environment variable is not set")
        sys.exit(1)
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid PORT value '{port_str}'. PORT must be a valid integer.")
        sys.exit(1)
    
    print(f"Starting server on port {port}")
    
    # Start the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
