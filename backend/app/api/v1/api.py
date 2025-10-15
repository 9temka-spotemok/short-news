"""
Enhanced API v1 router configuration with improved organization
"""

from fastapi import APIRouter
from loguru import logger

from app.api.v1.endpoints import auth, news, users, digest, companies, notifications, competitors
from app.api.v1.endpoints.admin import scraping as admin_scraping

# Create main API router with enhanced configuration
api_router = APIRouter(
    prefix="/api/v1",
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)

# Include all endpoint routers with enhanced organization
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"}
    }
)

api_router.include_router(
    news.router, 
    tags=["News"],
    responses={
        404: {"description": "News item not found"},
        422: {"description": "Invalid news parameters"}
    }
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["Users"],
    responses={
        404: {"description": "User not found"},
        409: {"description": "User already exists"}
    }
)

api_router.include_router(
    digest.router, 
    prefix="/digest", 
    tags=["Digest"],
    responses={
        404: {"description": "Digest not found"}
    }
)

api_router.include_router(
    companies.router, 
    prefix="/companies", 
    tags=["Companies"],
    responses={
        404: {"description": "Company not found"}
    }
)

api_router.include_router(
    notifications.router, 
    prefix="/notifications", 
    tags=["Notifications"],
    responses={
        404: {"description": "Notification not found"}
    }
)

api_router.include_router(
    competitors.router, 
    prefix="/competitors", 
    tags=["Competitors"],
    responses={
        404: {"description": "Competitor not found"}
    }
)

api_router.include_router(
    admin_scraping.router, 
    prefix="/admin", 
    tags=["Admin"],
    responses={
        403: {"description": "Admin access required"}
    }
)

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    
    Returns the current status of the API service.
    """
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": "AI Competitor Insight Hub API",
        "version": "0.1.0",
        "endpoints": {
            "news": "/news",
            "companies": "/companies", 
            "users": "/users",
            "digest": "/digest",
            "notifications": "/notifications",
            "competitors": "/competitors",
            "admin": "/admin"
        }
    }
