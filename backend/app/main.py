from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import wardrobe_db as wardrobe
from app.routers import suggestions_v2
from app.database import engine, Base
from sqlalchemy import create_engine
from datetime import datetime
import os
import asyncio
from threading import Lock

# Global flag to track startup completion
_startup_complete = False
_startup_lock = Lock()


# Optimize SQLAlchemy connection pooling
# You can adjust pool_size and pool_recycle as needed
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,           # Number of connections to keep in the pool
        max_overflow=20,        # Number of connections allowed above pool_size
        pool_recycle=1800,      # Recycle connections after 30 minutes
        pool_pre_ping=True      # Check connection health before using
    )
    Base.metadata.create_all(bind=engine)
else:
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
        "https://stylo-chi.vercel.app",
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

# Run lightweight, idempotent DB migrations on startup (non-blocking)
@app.on_event("startup")
async def run_startup_migrations() -> None:
    """Run startup tasks in background to avoid blocking health checks"""
    global _startup_complete
    
    async def _startup_tasks():
        global _startup_complete
        try:
            # The migration checks for the column and only adds if missing
            from migrate_add_image_description import migrate  # type: ignore
            migrate()
            print("✅ Startup migration completed (image_description column ensured)")
        except Exception as exc:
            # Do not crash app on migration failure; log for visibility
            print(f"⚠️  Migration on startup skipped/failed: {exc}")
        
        # Pre-load sentence-transformers model to avoid cold start timeouts
        try:
            print("🔄 Pre-loading sentence-transformers model...")
            from sentence_transformers import SentenceTransformer
            _ = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Model pre-loaded successfully")
        except Exception as exc:
            print(f"⚠️  Model pre-load failed: {exc}")
        
        # Backfill will only run if BACKFILL_ON_STARTUP=true is set in environment
        # This avoids running backfill on every startup unless explicitly required
        if os.getenv("BACKFILL_ON_STARTUP", "false").lower() == "true":
            try:
                print("🔄 Running image description backfill...")
                from backfill_image_descriptions import backfill_descriptions  # type: ignore
                await backfill_descriptions()
                print("✅ Backfill completed on startup")
            except Exception as exc:
                print(f"⚠️  Backfill on startup failed: {exc}")
        
        # Mark startup as complete
        with _startup_lock:
            _startup_complete = True
        print("✅ Startup tasks completed")
    
    # Run startup tasks in background (non-blocking)
    asyncio.create_task(_startup_tasks())
    print("🚀 Server starting, startup tasks running in background...")

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

# Include routers
app.include_router(wardrobe.router, prefix="/wardrobe", tags=["wardrobe"])
app.include_router(suggestions_v2.router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint - returns immediately to avoid timeouts.
    This endpoint should respond in < 100ms to prevent deployment platform timeouts.
    Use /ready for readiness check (waits for startup completion).
    """
    # Quick database connectivity check (non-blocking, with timeout)
    db_ok = False
    try:
        # Quick connection test with timeout
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        # Database check failed, but don't fail health check during startup
        db_ok = False
    
    return {
        "status": "ok",
        "ready": _startup_complete,
        "database": "connected" if db_ok else "checking"
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint - verifies app is fully ready.
    Returns 200 when startup tasks complete, 503 if still starting.
    """
    from fastapi import status
    from fastapi.responses import JSONResponse
    
    if _startup_complete:
        return {"status": "ready", "message": "Application is ready"}
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "starting", "message": "Application is still starting up"}
        )


@app.get("/admin/version")
async def version_info():
    """Admin: return deployment/version metadata to verify live build.

    Includes commit SHA from common platforms, optional SERVICE_VERSION env,
    the app version configured in FastAPI, and current UTC time.
    """
    commit = (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("GIT_COMMIT")
        or os.getenv("VERCEL_GIT_COMMIT_SHA")
        or os.getenv("RENDER_GIT_BRANCH")  # fallback if SHA not present
    )
    return {
        "commit": commit,
        "service_version": os.getenv("SERVICE_VERSION"),
        "app_version": app.version,
        "time": datetime.utcnow().isoformat() + "Z",
        "env": os.getenv("ENVIRONMENT") or os.getenv("NODE_ENV") or "",
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to STYLO API",
        "version": "1.0.0",
        "docs": "/docs"
    }
