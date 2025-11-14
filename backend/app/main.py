from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import wardrobe
from app.routers import suggestions

app = FastAPI(
    title="STYLO API",
    description="Backend API for STYLO wardrobe management",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

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
