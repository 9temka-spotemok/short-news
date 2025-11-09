"""
Version 2 API router configuration.
"""

from fastapi import APIRouter

from app.api.v2.endpoints import analytics

api_v2_router = APIRouter(
    prefix="/api/v2",
    tags=["API v2"],
)

api_v2_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)


