"""
Configuration management for STYLO backend
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

"""Application settings and configuration"""
class Settings:

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # Frontend URL (for CORS)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    
    # Google Gemini Configuration (for image analysis)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Image upload settings
    CLOUDINARY_FOLDER: str = os.getenv("CLOUDINARY_FOLDER", "stylo_wardrobe")
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", "10485760"))  # 10MB default
    
    # Feature flags
    USE_CLOUDINARY: bool = os.getenv("USE_CLOUDINARY", "true").lower() == "true"
    
    # RAG (Retrieval-Augmented Generation) Configuration
    RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() == "true"
    # Lowered to improve fallback for small wardrobes
    RAG_ITEMS_PER_CATEGORY: int = int(os.getenv("RAG_ITEMS_PER_CATEGORY", "10"))
    RAG_MIN_ITEMS_FALLBACK: int = int(os.getenv("RAG_MIN_ITEMS_FALLBACK", "5"))
    RAG_MIN_ITEMS_PER_CATEGORY: int = int(os.getenv("RAG_MIN_ITEMS_PER_CATEGORY", "1"))
    
    """Check if Cloudinary is properly configured"""
    @property
    def cloudinary_configured(self) -> bool:
        return bool(
            self.CLOUDINARY_CLOUD_NAME 
            and self.CLOUDINARY_API_KEY 
            and self.CLOUDINARY_API_SECRET
        )

settings = Settings()
