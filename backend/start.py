#!/usr/bin/env python3
"""
Railway startup script for shot-news API
"""
import os
import uvicorn

if __name__ == "__main__":
    # Get port from environment variable, default to 8000
    port_str = os.environ.get("PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        print(f"Warning: Invalid PORT value '{port_str}', using default port 8000")
        port = 8000
    
    print(f"Starting server on port {port}")
    
    # Start the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
