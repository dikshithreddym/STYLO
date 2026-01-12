"""
Pydantic schemas for STYLO API.

Import all schemas here for easy access and backward compatibility.
"""
from .common import HealthResponse
from .user import UserBase, UserCreate, UserLogin, UserResponse, Token, TokenData, UserUpdate
from .wardrobe import WardrobeItemBase, WardrobeItem, WardrobeItemCreate, WardrobeItemUpdate
from .outfit import Outfit, SuggestRequest, SuggestResponse, SavedOutfitCreate, SavedOutfitResponse

__all__ = [
    # Common
    "HealthResponse",
    # User
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenData",
    "UserUpdate",
    # Wardrobe
    "WardrobeItemBase",
    "WardrobeItem",
    "WardrobeItemCreate",
    "WardrobeItemUpdate",
    # Outfit
    "Outfit",
    "SuggestRequest",
    "SuggestResponse",
    "SavedOutfitCreate",
    "SavedOutfitResponse",
]
