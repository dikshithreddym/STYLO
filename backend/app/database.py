
"""
Database configuration, session management, and models (PostgreSQL only)
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base # keep this if needed, but preferred is orm
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variable or use default PostgreSQL URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://stylo_user:3mVRKCccUHCTLALCPlAEWKvsOuXxzy1z@dpg-d4bkin0dl3ps739f0t4g-a.oregon-postgres.render.com/stylo_db_not6"
)

# Fix for Render PostgreSQL URL (uses postgresql:// instead of postgres://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with optimized connection pooling
# Centralized here so SessionLocal and all imports benefit from tuning
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # Number of connections to keep in the pool
    max_overflow=20,        # Number of connections allowed above pool_size
    pool_recycle=1800,      # Recycle connections after 30 minutes
    pool_pre_ping=True      # Check connection health before using
)

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
    embedding = Column(JSON, nullable=True)  # Cached embedding vector (list of floats)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True) # Making nullable first for migration safety, then we can enforce it

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

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SavedOutfit(Base):
    """Saved outfit model"""
    __tablename__ = "saved_outfits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=True) # Optional name for the outfit
    items = Column(JSON, nullable=False) # JSON object with keys like 'top', 'bottom', etc. containing item IDs or details
    is_pinned = Column(Integer, default=0, nullable=False) # 0 = not pinned, 1 = pinned
    created_at = Column(DateTime, default=datetime.utcnow)
