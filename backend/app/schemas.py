"""Schemas for wardrobe items and outfit suggestions."""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

"""Base schema for wardrobe items"""
class WardrobeItemBase(BaseModel):
    type: str = Field(..., description="Type of clothing item (e.g., shirt, pants, dress)")
    color: str = Field(..., description="Primary color of the item")
    image_url: Optional[str] = Field(None, description="URL to item image")
    category: Optional[Literal['top','bottom','footwear','layer','one-piece','accessories']] = Field(
        None, description="Categorization for outfit building"
    )
    image_description: Optional[str] = Field(None, description="AI-generated description of the item")

"""Wardrobe item with ID"""
class WardrobeItem(WardrobeItemBase):
    id: int = Field(..., description="Unique identifier for the item")

    """Configuration for WardrobeItem schema"""
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "shirt",
                "color": "blue",
                "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c"
            }
        }

"""Schema for creating a new wardrobe item"""
class WardrobeItemCreate(WardrobeItemBase):
    pass

"""Health check response"""
class HealthResponse(BaseModel):
    status: str

"""Input for outfit suggestion"""
class SuggestRequest(BaseModel):
    text: str
    limit: int = Field(5, ge=1, le=20, description="Number of alternative outfits to generate")
    strategy: Optional[Literal['rules','ml']] = Field('rules', description="Suggestion engine strategy")

"""Outfit representation"""
class Outfit(BaseModel):
    items: List[WardrobeItem]
    score: float = Field(..., description="Outfit score 0-1")
    rationale: Optional[str] = None

"""Outfit suggestion response"""
class SuggestResponse(BaseModel):
    occasion: str
    colors: List[str]
    outfit: Outfit
    alternatives: List[Outfit] = []
    notes: Optional[str] = None
    intent: Optional[str] = Field(None, description="Resolved intent: outfit | item_search | blended_outfit_item | activity_shoes")

from datetime import datetime

"""User Schemas"""
class UserBase(BaseModel):
    email: str = Field(..., description="User email address")

class UserCreate(UserBase):
    password: str = Field(..., description="User password")
    full_name: Optional[str] = Field(None, description="User full name")

class UserLogin(UserBase):
    password: str = Field(..., description="User password")

class UserResponse(UserBase):
    id: int
    full_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
