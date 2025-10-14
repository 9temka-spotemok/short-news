"""
API v1 router configuration
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, news, users, digest, companies, notifications, competitors
from app.api.v1.endpoints.admin import scraping as admin_scraping

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(digest.router, prefix="/digest", tags=["digest"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(competitors.router, prefix="/competitors", tags=["competitors"])
api_router.include_router(admin_scraping.router, prefix="/admin", tags=["admin"])
