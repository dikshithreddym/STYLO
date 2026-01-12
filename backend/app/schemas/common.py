"""
Common/shared schemas used across the application.
"""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
