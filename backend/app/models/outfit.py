"""
Saved outfit model.
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from datetime import datetime

from .base import Base


class SavedOutfit(Base):
    """Saved outfit model"""
    __tablename__ = "saved_outfits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # Optional name for the outfit
    items = Column(JSON, nullable=False)  # JSON object with keys like 'top', 'bottom', etc.
    is_pinned = Column(Integer, default=0, nullable=False)  # 0 = not pinned, 1 = pinned
    created_at = Column(DateTime, default=datetime.utcnow)
