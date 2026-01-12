"""
Pydantic schemas for STYLO API.

DEPRECATED: Import from app.schemas package instead.
This file is kept for backward compatibility only.

Example:
    # Old (still works):
    from app.schemas import UserCreate, WardrobeItem
    
    # New (preferred):
    from app.schemas.user import UserCreate
    from app.schemas.wardrobe import WardrobeItem
"""
# Re-export all schemas from the package for backward compatibility
from app.schemas import (
    # Common
    HealthResponse,
    # User
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenData,
    # Wardrobe
    WardrobeItemBase,
    WardrobeItem,
    WardrobeItemCreate,
    WardrobeItemUpdate,
    # Outfit
    Outfit,
    SuggestRequest,
    SuggestResponse,
    SavedOutfitCreate,
    SavedOutfitResponse,
)

__all__ = [
    "HealthResponse",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenData",
    "WardrobeItemBase",
    "WardrobeItem",
    "WardrobeItemCreate",
    "WardrobeItemUpdate",
    "Outfit",
    "SuggestRequest",
    "SuggestResponse",
    "SavedOutfitCreate",
    "SavedOutfitResponse",
]
