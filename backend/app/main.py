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

# Admin endpoint for manual backfill trigger
@app.post("/admin/backfill-descriptions")
async def trigger_backfill():
    """Admin endpoint to trigger image description backfill for existing items"""
    try:
        from backfill_image_descriptions import backfill_descriptions
        import sys
        from io import StringIO
        
        # Capture output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            await backfill_descriptions()
        finally:
            sys.stdout = old_stdout
        
        output = captured_output.getvalue()
        return {
            "status": "success", 
            "message": "Backfill completed successfully",
            "output": output
        }
    except Exception as e:
        import traceback
        return {
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc()
        }

# Admin endpoint to update category from shoes to footwear
@app.post("/admin/update-category-to-footwear")
async def update_category_to_footwear():
    """Admin endpoint to update all 'shoes' category items to 'footwear'"""
    try:
        from app.database import SessionLocal
        from app.models import WardrobeItem
        
        db = SessionLocal()
        updated_count = 0
        
        # Find all items with 'shoes' category
        items = db.query(WardrobeItem).filter(WardrobeItem.category == 'shoes').all()
        
        for item in items:
            item.category = 'footwear'
            updated_count += 1
        
        db.commit()
        db.close()
        
        return {
            "status": "success",
            "message": f"Updated {updated_count} items from 'shoes' to 'footwear'",
            "updated_count": updated_count
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }

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
