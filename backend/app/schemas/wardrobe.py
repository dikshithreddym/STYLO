"""
Wardrobe item schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class WardrobeItemBase(BaseModel):
    """Base schema for wardrobe items"""
    type: str = Field(..., description="Type of clothing item (e.g., shirt, pants, dress)")
    color: str = Field(..., description="Primary color of the item")
    image_url: Optional[str] = Field(None, description="URL to item image")
    category: Optional[Literal['top', 'bottom', 'footwear', 'layer', 'one-piece', 'accessories']] = Field(
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


class WardrobeItemUpdate(WardrobeItemBase):
    """Schema for updating a wardrobe item"""
    type: Optional[str] = Field(None, description="Type of clothing item")
    color: Optional[str] = Field(None, description="Primary color of the item")
