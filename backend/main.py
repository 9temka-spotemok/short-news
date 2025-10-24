"""
AI Competitor Insight Hub (shot-news) - Main FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import uvicorn

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router
from app.core.exceptions import setup_exception_handlers

# Create FastAPI app
app = FastAPI(
    title="AI Competitor Insight Hub API",
    description="API для мониторинга новостей из мира ИИ-индустрии",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup trusted hosts (expects hostnames, not full URLs)
if settings.ENVIRONMENT == "production":
    try:
        allowed_hosts = [h.replace("http://", "").replace("https://", "").split("/")[0] for h in settings.ALLOWED_HOSTS]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    except Exception:
        # Fallback to original list if parsing fails
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Setup exception handlers
setup_exception_handlers(app)

# Include API router
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting AI Competitor Insight Hub API...")
    
    # Initialize database
    await init_db()
    
    logger.info("Application startup complete!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down AI Competitor Insight Hub API...")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "shot-news-api",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "message": "Welcome to AI Competitor Insight Hub API",
            "version": "0.1.0",
            "docs": "/docs" if settings.ENVIRONMENT != "production" else "Not available in production",
            "health": "/health"
        }
    )


if __name__ == "__main__":
    import os
    import sys
    
    # Check for required environment variables
    required_vars = ["SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in Railway dashboard or .env file")
        sys.exit(1)
    
    # Get port from environment variable with multiple fallbacks
    port_str = os.environ.get("PORT") or os.environ.get("PORT_NUMBER") or "8000"
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid PORT value '{port_str}'. Using default port 8000.")
        port = 8000
    
    print(f"Starting server on port {port}")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'unknown')}")
    print(f"Debug mode: {os.environ.get('DEBUG', 'false')}")
    # Log database URL (masked for security)
    db_url = os.environ.get('DATABASE_URL', 'not set')
    if db_url != 'not set':
        # Mask password in URL for logging
        import re
        masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', db_url)
        print(f"Database URL: {masked_url}")
    else:
        print(f"Database URL: {db_url}")
    
    redis_url = os.environ.get('REDIS_URL', 'not set')
    if redis_url != 'not set':
        import re
        masked_redis = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', redis_url)
        print(f"Redis URL: {masked_redis}")
    else:
        print(f"Redis URL: {redis_url}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
