from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import wardrobe_db as wardrobe
from app.routers import suggestions
from app.database import engine, Base
import os

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="STYLO API",
    description="Backend API for STYLO wardrobe management",
    version="1.0.0"
)

# CORS configuration
# Prefer comma-separated CORS_ORIGINS if provided, otherwise fallback to FRONTEND_URL
cors_from_env = os.getenv("CORS_ORIGINS")
if cors_from_env:
    allowed_origins = [o.strip() for o in cors_from_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        os.getenv("FRONTEND_URL", "*"),
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if os.getenv("ENVIRONMENT") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# Run lightweight, idempotent DB migrations on startup
@app.on_event("startup")
async def run_startup_migrations() -> None:
    # Only run on server start; safe to run repeatedly
    try:
        # The migration checks for the column and only adds if missing
        from migrate_add_image_description import migrate  # type: ignore
        migrate()
        print("✅ Startup migration completed (image_description column ensured)")
    except Exception as exc:
        # Do not crash app on migration failure; log for visibility
        print(f"⚠️  Migration on startup skipped/failed: {exc}")
    
    # Optional: Backfill image descriptions for existing items
    # Set BACKFILL_ON_STARTUP=true in environment to enable
    if os.getenv("BACKFILL_ON_STARTUP", "false").lower() == "true":
        try:
            print("🔄 Running image description backfill...")
            from backfill_image_descriptions import backfill_descriptions  # type: ignore
            await backfill_descriptions()
            print("✅ Backfill completed on startup")
        except Exception as exc:
            print(f"⚠️  Backfill on startup failed: {exc}")

# Include routers
app.include_router(wardrobe.router, prefix="/wardrobe", tags=["wardrobe"])
app.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to STYLO API",
        "version": "1.0.0",
        "docs": "/docs"
    }
