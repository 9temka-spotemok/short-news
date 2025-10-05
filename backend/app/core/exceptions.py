"""
Custom exception handlers
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from loguru import logger


class ShotNewsException(Exception):
    """Base exception for shot-news application"""
    pass


class DatabaseException(ShotNewsException):
    """Database related exceptions"""
    pass


class ExternalAPIException(ShotNewsException):
    """External API related exceptions"""
    pass


class ScrapingException(ShotNewsException):
    """Web scraping related exceptions"""
    pass


class AuthenticationException(ShotNewsException):
    """Authentication related exceptions"""
    pass


class AuthorizationException(ShotNewsException):
    """Authorization related exceptions"""
    pass


class ValidationException(ShotNewsException):
    """Validation related exceptions"""
    pass


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions"""
    logger.warning(f"Validation error: {exc.errors()} - {request.url}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors(),
            "status_code": 422,
        }
    )


async def shot_news_exception_handler(request: Request, exc: ShotNewsException):
    """Handle custom application exceptions"""
    logger.error(f"Application error: {str(exc)} - {request.url}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Application Error",
            "message": str(exc),
            "status_code": 500,
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {str(exc)} - {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500,
        }
    )


def setup_exception_handlers(app: FastAPI):
    """Setup all exception handlers"""
    
    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Validation exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Custom application exceptions
    app.add_exception_handler(ShotNewsException, shot_news_exception_handler)
    
    # General exceptions
    app.add_exception_handler(Exception, general_exception_handler)
