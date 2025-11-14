"""
Configuration management for STYLO backend
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings"""
    
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    
    # Image upload settings
    CLOUDINARY_FOLDER: str = os.getenv("CLOUDINARY_FOLDER", "stylo_wardrobe")
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", "10485760"))  # 10MB default
    
    # Feature flags
    USE_CLOUDINARY: bool = os.getenv("USE_CLOUDINARY", "true").lower() == "true"
    
    @property
    def cloudinary_configured(self) -> bool:
        """Check if Cloudinary is properly configured"""
        return bool(
            self.CLOUDINARY_CLOUD_NAME 
            and self.CLOUDINARY_API_KEY 
            and self.CLOUDINARY_API_SECRET
        )

settings = Settings()
