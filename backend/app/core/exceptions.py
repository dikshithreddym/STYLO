"""
Centralized exception handling for STYLO backend.
Provides consistent error responses across all endpoints.
"""
import logging
import traceback
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exception Classes
# =============================================================================

class StyloException(Exception):
    """Base exception for STYLO application errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(message)


class NotFoundError(StyloException):
    """Resource not found."""
    
    def __init__(self, resource: str, resource_id: Any = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "id": resource_id}
        )


class ValidationError(StyloException):
    """Input validation failed."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


class AuthenticationError(StyloException):
    """Authentication failed."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(StyloException):
    """User not authorized for this action."""
    
    def __init__(self, message: str = "Not authorized to perform this action"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR"
        )


class RateLimitError(StyloException):
    """Rate limit exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR"
        )


class ExternalServiceError(StyloException):
    """External service (Gemini, Cloudinary, etc.) failed."""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service} service error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service}
        )


class DatabaseError(StyloException):
    """Database operation failed."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR"
        )


# =============================================================================
# Error Response Model
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# =============================================================================
# Exception Handlers for FastAPI
# =============================================================================

async def stylo_exception_handler(request: Request, exc: StyloException) -> JSONResponse:
    """Handle STYLO custom exceptions."""
    logger.error(f"StyloException: {exc.error_code} - {exc.message}", extra={"details": exc.details})
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details if exc.details else None
        ).model_dump(exclude_none=True)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPExceptions with consistent format."""
    error_code = "HTTP_ERROR"
    if exc.status_code == 400:
        error_code = "BAD_REQUEST"
    elif exc.status_code == 401:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        error_code = "FORBIDDEN"
    elif exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 422:
        error_code = "VALIDATION_ERROR"
    elif exc.status_code >= 500:
        error_code = "SERVER_ERROR"
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=error_code,
            message=str(exc.detail)
        ).model_dump(exclude_none=True)
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with logging."""
    # Log the full traceback for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method}
    )
    
    # In production, don't expose internal error details
    from app.config import settings
    is_dev = getattr(settings, 'ENVIRONMENT', 'production').lower() in ('development', 'dev', 'local')
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message=str(exc) if is_dev else "An unexpected error occurred",
            details={"traceback": traceback.format_exc()} if is_dev else None
        ).model_dump(exclude_none=True)
    )


# =============================================================================
# Utility Functions
# =============================================================================

def raise_not_found(resource: str, resource_id: Any = None) -> None:
    """Convenience function to raise NotFoundError."""
    raise NotFoundError(resource, resource_id)


def raise_validation_error(message: str, field: Optional[str] = None) -> None:
    """Convenience function to raise ValidationError."""
    raise ValidationError(message, field)


def safe_execute(func, *args, default=None, log_error: bool = True, **kwargs):
    """
    Safely execute a function and return default on error.
    Use for non-critical operations that shouldn't crash the app.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.warning(f"safe_execute caught error in {func.__name__}: {e}")
        return default


async def safe_execute_async(coro, default=None, log_error: bool = True):
    """
    Safely execute an async coroutine and return default on error.
    Use for non-critical async operations that shouldn't crash the app.
    """
    try:
        return await coro
    except Exception as e:
        if log_error:
            logger.warning(f"safe_execute_async caught error: {e}")
        return default
