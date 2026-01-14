
"""
Database configuration and session management (PostgreSQL only).
Models are defined in app/models/ - imported here for backward compatibility.

Supports both sync and async operations:
- Sync: Use `get_db()` dependency and `SessionLocal`
- Async: Use `get_async_db()` dependency and `AsyncSessionLocal`
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
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

# Create async URL for asyncpg driver
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


# =============================================================================
# SYNC ENGINE (for backward compatibility and migrations)
# =============================================================================
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Sync dependency to get database session (for backward compatibility)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# ASYNC ENGINE (preferred for new code)
# =============================================================================
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_timeout=5,
    echo=False,
    connect_args={"timeout": 3},
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency to get database session (preferred)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Re-export for backward compatibility
__all__ = [
    # Sync (backward compat)
    "engine", 
    "SessionLocal", 
    "get_db",
    # Async (preferred)
    "async_engine",
    "AsyncSessionLocal",
    "get_async_db",
    # Models
    "Base", 
    "User", 
    "WardrobeItem", 
    "SavedOutfit",
]

