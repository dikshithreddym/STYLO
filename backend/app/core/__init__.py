"""
Core module for STYLO backend.
Contains exception handling and shared utilities.
"""
from .exceptions import (
    StyloException,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ExternalServiceError,
    DatabaseError,
    ErrorResponse,
    stylo_exception_handler,
    http_exception_handler,
    generic_exception_handler,
    raise_not_found,
    raise_validation_error,
    safe_execute,
    safe_execute_async,
)

__all__ = [
    "StyloException",
    "NotFoundError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "ExternalServiceError",
    "DatabaseError",
    "ErrorResponse",
    "stylo_exception_handler",
    "http_exception_handler",
    "generic_exception_handler",
    "raise_not_found",
    "raise_validation_error",
    "safe_execute",
    "safe_execute_async",
]
