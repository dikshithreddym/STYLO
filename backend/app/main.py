from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import wardrobe_db as wardrobe
from app.routers import suggestions_v2
from app.routers import auth
from app.database import engine, Base
from app.utils.embedding_service import start_embedding_worker
from datetime import datetime
import os
import asyncio
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

# Global flag to track startup completion
_startup_complete = False
_startup_lock = Lock()

# Thread pool for CPU-bound startup tasks
_startup_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="startup")


def _sync_startup_tasks() -> None:
    """Synchronous startup tasks that run in a thread pool to avoid blocking."""
    global _startup_complete
    
    # Pre-load sentence-transformers model to avoid cold start timeouts
    # This is CPU-intensive and MUST run in a thread to avoid blocking
    try:
        print("🔄 Pre-loading sentence-transformers model...")
        from sentence_transformers import SentenceTransformer
        _ = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Model pre-loaded successfully")
    except Exception as exc:
        print(f"⚠️  Model pre-load failed: {exc}")
    
    # Mark startup as complete
    with _startup_lock:
        _startup_complete = True
    print("✅ Startup tasks completed")


async def _run_startup_tasks() -> None:
    """Run startup tasks in background thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    
    # Run CPU-intensive tasks in thread pool (non-blocking)
    await loop.run_in_executor(_startup_executor, _sync_startup_tasks)


def _create_tables() -> None:
    """Create database tables (runs in thread to avoid blocking)."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown events."""
    # === STARTUP ===
    loop = asyncio.get_event_loop()
    
    # Create database tables in thread pool (non-blocking)
    await loop.run_in_executor(_startup_executor, _create_tables)
    
    # Run startup tasks in background (non-blocking, doesn't wait)
    asyncio.create_task(_run_startup_tasks())
    
    # Start embedding worker for async embedding updates (non-blocking)
    try:
        start_embedding_worker()
        print("✅ Embedding worker started")
    except Exception as e:
        print(f"⚠️  Could not start embedding worker: {e}. Embeddings will be computed on-demand.")
    
    print("🚀 Server starting, startup tasks running in background...")
    
    yield  # Application runs here
    
    # === SHUTDOWN ===
    _startup_executor.shutdown(wait=False)
    print("👋 Server shutting down...")


# CORS configuration
# We start with a default list of known trusted origins
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://styloapp.vercel.app",  # Production Vercel Frontend
]

# Add any additional origins from environment (CORS_ORIGINS)
cors_from_env = os.getenv("CORS_ORIGINS")
if cors_from_env:
    for origin in cors_from_env.split(","):
        o = origin.strip()
        if o and o not in allowed_origins:
            allowed_origins.append(o)

# Add widely used fallback if set
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

print(f"✅ Enabled CORS for origins: {allowed_origins}")


app = FastAPI(
    title="STYLO API",
    description="Backend API for STYLO wardrobe management",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"] with allow_credentials=True is invalid/insecure.
    # We must restrict to specific domains.
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)


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
app.include_router(auth.router)


@app.get("/health")
@app.head("/health")
async def health_check():
    """
    Health check endpoint - returns immediately to avoid timeouts.
    This endpoint should respond in < 100ms to prevent deployment platform timeouts.
    Use /ready for readiness check (waits for startup completion).
    Supports both GET and HEAD methods for monitoring services.
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


# =============================================================================
# DEBUG/TEST ENDPOINTS - Only available in development environment
# =============================================================================
_is_development = os.getenv("ENVIRONMENT", "development").lower() == "development"

if _is_development:
    @app.get("/test-cache-debug")
    async def test_cache_debug():
        """Debug cache behavior for suggestions (DEV ONLY)"""
        from app.utils.cache import get_redis_client, get_cached_suggestion, set_cached_suggestion, _generate_cache_key
        import hashlib
        import json
        
        redis_client = get_redis_client()
        
        test_query = "business meeting"
        test_hash = "10"
        
        # Generate the same key that would be used
        cache_key = _generate_cache_key("suggestion", test_query, test_hash)
        
        # Check what's in Redis
        all_suggestion_keys = []
        if redis_client:
            try:
                all_suggestion_keys = redis_client.keys("suggestion:*")
            except Exception as e:
                pass
        
        # Test set/get
        test_result = {"intent": "business", "outfits": [{"test": "outfit"}]}
        set_success = set_cached_suggestion(test_query, test_hash, test_result, ttl=60)
        get_result = get_cached_suggestion(test_query, test_hash)
        
        return {
            "cache_key_generated": cache_key,
            "cache_key_short": cache_key[:50] + "..." if len(cache_key) > 50 else cache_key,
            "set_success": set_success,
            "get_result": get_result,
            "get_matches_set": get_result == test_result,
            "redis_keys_found": len(all_suggestion_keys),
            "sample_keys": [k[:60] for k in list(all_suggestion_keys)[:10]],
            "test_query": test_query,
            "test_hash": test_hash
        }


    @app.get("/test-redis")
    async def test_redis():
        """Test Redis connection and caching (DEV ONLY)"""
        from app.utils.cache import get_redis_client, cache_set, cache_get, get_cached_suggestion, set_cached_suggestion
        import logging
        
        logger = logging.getLogger(__name__)
        
        redis_client = get_redis_client()
        
        if not redis_client:
            return {
                "status": "not_connected",
                "message": "Redis client not available - using in-memory cache",
                "redis_available": False,
                "redis_url": os.getenv("REDIS_URL", "not set")
            }
        
        try:
            # Test connection
            ping_result = redis_client.ping()
            
            # Test set/get
            test_key = "test:connection"
            test_value = {"test": "data", "timestamp": "2025-11-21", "works": True}
            
            # Set value
            cache_set(test_key, test_value, ttl=60)
            
            # Get value
            cached = cache_get(test_key)
            
            # Test direct Redis operations
            direct_set = redis_client.set("test:direct", "test_value", ex=60)
            direct_get = redis_client.get("test:direct")
            
            # Test suggestion cache functions
            test_query = "business meeting"
            test_hash = "10"
            test_suggestion = {"intent": "business", "outfits": [{"test": "outfit"}]}
            set_cached_suggestion(test_query, test_hash, test_suggestion, ttl=60)
            cached_suggestion = get_cached_suggestion(test_query, test_hash)
            
            # Check Redis keys
            all_keys = redis_client.keys("suggestion:*")
            
            return {
                "status": "connected",
                "message": "Redis is working!",
                "redis_available": True,
                "ping": "OK" if ping_result else "FAILED",
                "set_get_test": "PASSED" if cached == test_value else "FAILED",
                "cached_value": cached,
                "direct_redis_test": "PASSED" if direct_get == "test_value" else "FAILED",
                "suggestion_cache_test": "PASSED" if cached_suggestion == test_suggestion else "FAILED",
                "cached_suggestion": cached_suggestion,
                "redis_keys_count": len(all_keys),
                "sample_keys": [k[:50] for k in list(all_keys)[:5]],
                "redis_url": os.getenv("REDIS_URL", "not set")[:50] + "..." if os.getenv("REDIS_URL") else "not set"
            }
        except Exception as e:
            logger.error(f"Redis test error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Redis error: {str(e)}",
                "redis_available": True,
                "error": str(e),
                "error_type": type(e).__name__,
                "redis_url": os.getenv("REDIS_URL", "not set")[:50] + "..." if os.getenv("REDIS_URL") else "not set"
            }

    