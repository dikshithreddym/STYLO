"""
Outfit and suggestion schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

from .wardrobe import WardrobeItem


class Outfit(BaseModel):
    """Outfit representation"""
    items: List[WardrobeItem]
    score: float = Field(..., description="Outfit score 0-1")
    rationale: Optional[str] = None


class SuggestRequest(BaseModel):
    """Input for outfit suggestion"""
    text: str
    limit: int = Field(5, ge=1, le=20, description="Number of alternative outfits to generate")
    strategy: Optional[Literal['rules', 'ml']] = Field('rules', description="Suggestion engine strategy")


class SuggestResponse(BaseModel):
    """Outfit suggestion response"""
    occasion: str
    colors: List[str]
    outfit: Outfit
    alternatives: List[Outfit] = []
    notes: Optional[str] = None
    intent: Optional[str] = Field(None, description="Resolved intent: outfit | item_search | blended_outfit_item | activity_shoes")


class SavedOutfitCreate(BaseModel):
    """Schema for creating a saved outfit"""
    name: Optional[str] = None
    items: dict = Field(..., description="JSON object containing outfit items")


class SavedOutfitResponse(SavedOutfitCreate):
    """Schema for saved outfit response"""
    id: int
    is_pinned: int = Field(0, description="Whether the outfit is pinned (0=no, 1=yes)")
    created_at: datetime
    
    class Config:
        from_attributes = True
