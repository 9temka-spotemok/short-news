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
app.include_router(api_router, prefix="/api/v1")


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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
