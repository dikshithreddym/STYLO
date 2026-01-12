"""
Wardrobe item model.
"""
from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey

from .base import Base


class WardrobeItem(Base):
    """Wardrobe item model"""
    __tablename__ = "wardrobe_items"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(100), nullable=False, index=True)
    color = Column(String(100), nullable=False, index=True)
    image_url = Column(Text, nullable=True)  # Cloudinary URL
    category = Column(String(50), nullable=True, index=True)
    cloudinary_id = Column(String(255), nullable=True)  # For deletion
    image_description = Column(Text, nullable=True)  # AI-generated description
    embedding = Column(JSON, nullable=True)  # Cached embedding vector (list of floats)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type,
            "color": self.color,
            "image_url": self.image_url,
            "category": self.category,
            "image_description": self.image_description,
        }
