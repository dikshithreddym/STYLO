"""
Wardrobe item model.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import Float, TypeDecorator
import json


class VectorType(TypeDecorator):
    """
    Custom type for embedding vectors.
    Uses ARRAY(Float) on PostgreSQL for better performance.
    Falls back to JSON on SQLite/other databases for compatibility.
    """
    impl = JSON  # Default implementation
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(Float))
        return dialect.type_descriptor(JSON())
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # For PostgreSQL ARRAY, pass list directly
        # For JSON, it will be serialized automatically
        if isinstance(value, list):
            return value
        return list(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Both ARRAY and JSON return list-like objects
        return list(value) if value else None


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
    # Embedding vector - uses ARRAY(Float) on PostgreSQL, JSON on SQLite
    # 384 dimensions for all-MiniLM-L6-v2 model
    embedding = Column(VectorType, nullable=True)
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
