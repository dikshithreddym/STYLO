"""
User-related schemas for authentication and user management.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: str = Field(..., description="User email address")


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., description="User password")
    full_name: Optional[str] = Field(None, description="User full name")


class UserLogin(UserBase):
    """Schema for user login"""
    password: str = Field(..., description="User password")


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    full_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token payload data"""
    email: Optional[str] = None
