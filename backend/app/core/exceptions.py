"""
Enhanced custom exception handlers with better error management
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from loguru import logger


class ShotNewsException(Exception):
    """Base exception for shot-news application with enhanced error handling"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.lower()
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(ShotNewsException):
    """Enhanced validation error with field information"""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None, 
        **kwargs
    ):
        self.field = field
        super().__init__(
            message, 
            error_code="validation_error",
            status_code=400,
            **kwargs
        )


class AuthenticationError(ShotNewsException):
    """Authentication error"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message, 
            error_code="authentication_error",
            status_code=401,
            **kwargs
        )


class AuthorizationError(ShotNewsException):
    """Authorization error"""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message, 
            error_code="authorization_error",
            status_code=403,
            **kwargs
        )


class NotFoundError(ShotNewsException):
    """Not found error"""
    
    def __init__(
        self, 
        message: str = "Resource not found", 
        resource_type: Optional[str] = None, 
        **kwargs
    ):
        self.resource_type = resource_type
        super().__init__(
            message, 
            error_code="not_found_error",
            status_code=404,
            **kwargs
        )


class ConflictError(ShotNewsException):
    """Conflict error"""
    
    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(
            message, 
            error_code="conflict_error",
            status_code=409,
            **kwargs
        )


class DatabaseError(ShotNewsException):
    """Database related exceptions"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            error_code="database_error",
            status_code=500,
            **kwargs
        )


class ExternalAPIError(ShotNewsException):
    """External API related exceptions"""
    
    def __init__(
        self, 
        message: str, 
        service_name: Optional[str] = None, 
        **kwargs
    ):
        self.service_name = service_name
        super().__init__(
            message, 
            error_code="external_api_error",
            status_code=502,
            **kwargs
        )


class ScrapingError(ShotNewsException):
    """Web scraping related exceptions"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            error_code="scraping_error",
            status_code=500,
            **kwargs
        )


class NewsServiceError(ShotNewsException):
    """News service error"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            error_code="news_service_error",
            status_code=500,
            **kwargs
        )


class RateLimitError(ShotNewsException):
    """Rate limit error"""
    
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(
            message, 
            error_code="rate_limit_error",
            status_code=429,
            **kwargs
        )


# Backward compatibility aliases
ValidationException = ValidationError
AuthenticationException = AuthenticationError
AuthorizationException = AuthorizationError
DatabaseException = DatabaseError
ExternalAPIException = ExternalAPIError
ScrapingException = ScrapingError


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create standardized error response"""
    content = {
        "error": error_code,
        "message": message,
        "status_code": status_code
    }
    
    if details:
        content["details"] = details
    
    return JSONResponse(status_code=status_code, content=content)


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return create_error_response(
        status_code=exc.status_code,
        error_code="http_error",
        message=exc.detail
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions"""
    logger.warning(f"Validation error: {exc.errors()} - {request.url}")
    return create_error_response(
        status_code=422,
        error_code="validation_error",
        message="Invalid request data",
        details={"validation_errors": exc.errors()}
    )


async def shot_news_exception_handler(request: Request, exc: ShotNewsException):
    """Handle custom application exceptions with proper status codes"""
    logger.error(f"Application error ({exc.error_code}): {exc.message} - {request.url}")
    return create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details if exc.details else None
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {str(exc)} - {request.url}", exc_info=True)
    return create_error_response(
        status_code=500,
        error_code="internal_server_error",
        message="An unexpected error occurred"
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
