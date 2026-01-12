"""
User-related schemas for authentication and user management.
"""
import re
from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr = Field(..., description="User email address")


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="User password (8-128 chars, must contain letter and digit)"
    )
    full_name: Optional[str] = Field(None, description="User full name")
    
    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Ensure password has at least one letter and one digit."""
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


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
