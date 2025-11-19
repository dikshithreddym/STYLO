# Health Check Timeout Fix

## Problem
The deployment platform (Render/Heroku) was reporting health check timeouts:
- HTTP health check failed (timed out after 5 seconds)
- Connection refused errors
- Service keeps failing and recovering

## Root Cause
The startup event handler was **blocking** the server from responding to health checks:
1. Database migrations (synchronous, can take 1-2 seconds)
2. Sentence-transformers model loading (5-10 seconds) - **MAJOR BLOCKER**
3. Optional backfill operations (can take minutes)

The health check endpoint (`/health`) couldn't respond until all startup tasks completed, causing 5-second timeouts.

## Solution

### 1. Non-Blocking Startup Tasks
**File**: `backend/app/main.py` (lines 55-87)

**Before**: Startup tasks ran synchronously, blocking server startup
```python
@app.on_event("startup")
async def run_startup_migrations() -> None:
    migrate()  # Blocks
    SentenceTransformer('all-MiniLM-L6-v2')  # Blocks for 5-10 seconds
    # Health check can't respond until this completes
```

**After**: Startup tasks run in background task
```python
@app.on_event("startup")
async def run_startup_migrations() -> None:
    async def _startup_tasks():
        # All startup tasks here
        ...
        _startup_complete = True
    
    # Run in background (non-blocking)
    asyncio.create_task(_startup_tasks())
    # Server can now respond to health checks immediately
```

**Result**: Health check responds immediately (< 100ms), startup tasks run in background

### 2. Improved Health Check Endpoint
**File**: `backend/app/main.py` (lines 160-175)

**Changes**:
- Returns immediately (doesn't wait for startup)
- Includes startup status in response
- Quick database connectivity check (non-blocking)
- Never times out

**Response**:
```json
{
  "status": "ok",
  "ready": false,  // true when startup completes
  "database": "connected"  // or "checking"
}
```

### 3. New Readiness Endpoint
**File**: `backend/app/main.py` (lines 178-189)

**Purpose**: Separate endpoint for readiness checks (waits for startup)

**Response when ready**:
```json
{
  "status": "ready",
  "message": "Application is ready"
}
```

**Response when starting**:
```json
{
  "status": "starting",
  "message": "Application is still starting up"
}
```
Status: 503 Service Unavailable

## Benefits

1. **No More Timeouts**: Health check responds in < 100ms
2. **Faster Deployments**: Platform sees healthy server immediately
3. **Better Monitoring**: Can distinguish between "starting" and "ready"
4. **Graceful Degradation**: Server accepts requests even during startup (with some limitations)

## Deployment Platform Configuration

### For Render/Heroku
- **Health Check Path**: `/health` (responds immediately)
- **Readiness Check Path**: `/ready` (optional, for advanced monitoring)
- **Timeout**: 5 seconds (should never hit this now)

### Recommended Setup
1. Use `/health` for basic health checks (always returns 200)
2. Use `/ready` for readiness checks (returns 503 during startup)
3. Monitor both endpoints for better visibility

## Testing

### Local Testing
```bash
# Start server
uvicorn app.main:app --reload

# Test health check (should respond immediately)
curl http://localhost:8000/health

# Test readiness (may show "starting" initially)
curl http://localhost:8000/ready
```

### Expected Behavior
1. Server starts → `/health` returns immediately with `"ready": false`
2. Startup tasks run in background (model loading, migrations)
3. After 5-10 seconds → `/ready` returns `"ready": true`
4. Health checks never timeout

## Rollback Instructions

If issues occur, revert to blocking startup:
1. Remove `asyncio.create_task()` wrapper
2. Remove `_startup_complete` flag
3. Restore original synchronous startup handler
4. Remove `/ready` endpoint

## Additional Notes

### Model Loading
The sentence-transformers model still loads on startup (in background), but:
- First request may be slower (cold start)
- Subsequent requests are fast (model cached)
- Health check doesn't wait for model

### Database Migrations
Migrations still run on startup (in background), but:
- Health check doesn't wait
- First request may fail if migration needed
- Migration is idempotent (safe to run multiple times)

### Performance Impact
- **Before**: 5-10 second startup delay, health checks timeout
- **After**: < 100ms health check response, startup in background
- **Trade-off**: First API request may be slower (model loading)

## Files Modified

1. `backend/app/main.py`
   - Lines 11-15: Added startup tracking variables
   - Lines 55-87: Made startup tasks non-blocking
   - Lines 160-175: Improved health check endpoint
   - Lines 178-189: Added readiness endpoint

