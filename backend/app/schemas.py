from pydantic import BaseModel, Field
from typing import Optional, List
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


class WardrobeItemBase(BaseModel):
    """Base schema for wardrobe items"""
    type: str = Field(..., description="Type of clothing item (e.g., shirt, pants, dress)")
    color: str = Field(..., description="Primary color of the item")
    image_url: Optional[str] = Field(None, description="URL to item image")
    category: Optional[Literal['top','bottom','footwear','layer','one-piece','accessories']] = Field(
        None, description="Categorization for outfit building"
    )
    image_description: Optional[str] = Field(None, description="AI-generated description of the item")


class WardrobeItem(WardrobeItemBase):
    """Wardrobe item with ID"""
    id: int = Field(..., description="Unique identifier for the item")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "shirt",
                "color": "blue",
                "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c"
            }
        }


class WardrobeItemCreate(WardrobeItemBase):
    """Schema for creating a new wardrobe item"""
    pass


class HealthResponse(BaseModel):
    """Health check response"""
    status: str


class SuggestRequest(BaseModel):
    """Input for outfit suggestion"""
    text: str
    limit: int = Field(5, ge=1, le=20, description="Number of alternative outfits to generate")
    strategy: Optional[Literal['rules','ml']] = Field('rules', description="Suggestion engine strategy")


class Outfit(BaseModel):
    items: List[WardrobeItem]
    score: float = Field(..., description="Outfit score 0-1")
    rationale: Optional[str] = None


class SuggestResponse(BaseModel):
    """Outfit suggestion response"""
    occasion: str
    colors: List[str]
    outfit: Outfit
    alternatives: List[Outfit] = []
    notes: Optional[str] = None
    intent: Optional[str] = Field(None, description="Resolved intent: outfit | item_search | blended_outfit_item | activity_shoes")
