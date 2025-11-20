
"""
Database configuration, session management, and models (PostgreSQL only)
"""
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get database URL from environment variable or use default PostgreSQL URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://stylo_user:3mVRKCccUHCTLALCPlAEWKvsOuXxzy1z@dpg-d4bkin0dl3ps739f0t4g-a.oregon-postgres.render.com/stylo_db_not6"
)

# Fix for Render PostgreSQL URL (uses postgresql:// instead of postgres://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine (PostgreSQL only)
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database models
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
