
"""
Database configuration and session management (PostgreSQL only).
Models are defined in app/models/ - imported here for backward compatibility.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Import models from their proper location (re-export for backward compatibility)
from app.models import Base, User, WardrobeItem, SavedOutfit

load_dotenv()

# Get database URL from environment variable (REQUIRED - no default for security)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Set it in your .env file or environment."
    )

# Fix for Render PostgreSQL URL (uses postgres:// instead of postgresql://)
if DATABASE_URL.startswith("postgres://"):
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


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Re-export for backward compatibility
__all__ = ["engine", "SessionLocal", "Base", "get_db", "User", "WardrobeItem", "SavedOutfit"]

