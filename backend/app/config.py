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
    
    # Embedding batch processing configuration
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))  # Items per batch
    EMBEDDING_BATCH_TIMEOUT: float = float(os.getenv("EMBEDDING_BATCH_TIMEOUT", "2.0"))  # Seconds to wait for batch
    
    # RAG (Retrieval-Augmented Generation) Configuration
    RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() == "true"
    # Base thresholds (can be overridden by adaptive calculation)
    RAG_ITEMS_PER_CATEGORY_BASE: int = int(os.getenv("RAG_ITEMS_PER_CATEGORY", "10"))
    RAG_MIN_ITEMS_FALLBACK_BASE: int = int(os.getenv("RAG_MIN_ITEMS_FALLBACK", "5"))
    RAG_MIN_ITEMS_PER_CATEGORY_BASE: int = int(os.getenv("RAG_MIN_ITEMS_PER_CATEGORY", "1"))
    
    # Legacy direct access (for backward compatibility)
    @property
    def RAG_ITEMS_PER_CATEGORY(self) -> int:
        """Items per category - use get_adaptive_rag_thresholds() for data-volume-aware values"""
        return self.RAG_ITEMS_PER_CATEGORY_BASE
    
    @property
    def RAG_MIN_ITEMS_FALLBACK(self) -> int:
        """Min items fallback - use get_adaptive_rag_thresholds() for data-volume-aware values"""
        return self.RAG_MIN_ITEMS_FALLBACK_BASE
    
    @property
    def RAG_MIN_ITEMS_PER_CATEGORY(self) -> int:
        """Min items per category - use get_adaptive_rag_thresholds() for data-volume-aware values"""
        return self.RAG_MIN_ITEMS_PER_CATEGORY_BASE
    
    def get_adaptive_rag_thresholds(self, total_items: int) -> dict:
        """
        Calculate adaptive RAG thresholds based on wardrobe size.
        
        Tuning strategy:
        - Small wardrobes (< 20 items): Return all items, minimal filtering
        - Medium wardrobes (20-100 items): Moderate filtering, balanced thresholds
        - Large wardrobes (100-500 items): Aggressive filtering to reduce embedding cost
        - Very large wardrobes (> 500 items): Maximum filtering for performance
        
        Args:
            total_items: Total number of items in the wardrobe
            
        Returns:
            dict with keys: limit_per_category, min_items_per_category, min_total_items
        """
        # Small wardrobes: return all items, no filtering needed
        if total_items < 20:
            return {
                "limit_per_category": total_items,  # Effectively no limit
                "min_items_per_category": 1,
                "min_total_items": max(3, total_items // 2)  # At least half the wardrobe
            }
        
        # Medium wardrobes: balanced filtering
        elif total_items < 100:
            # Scale items per category: 10-15 items per category
            limit_per_category = min(15, max(10, total_items // 10))
            return {
                "limit_per_category": limit_per_category,
                "min_items_per_category": max(2, limit_per_category // 3),
                "min_total_items": max(8, total_items // 5)
            }
        
        # Large wardrobes: more aggressive filtering
        elif total_items < 500:
            # Scale items per category: 15-25 items per category
            limit_per_category = min(25, max(15, total_items // 20))
            return {
                "limit_per_category": limit_per_category,
                "min_items_per_category": max(3, limit_per_category // 4),
                "min_total_items": max(12, total_items // 10)
            }
        
        # Very large wardrobes: maximum filtering for performance
        else:
            # Cap at 30 items per category for very large wardrobes
            limit_per_category = min(30, max(20, total_items // 30))
            return {
                "limit_per_category": limit_per_category,
                "min_items_per_category": max(5, limit_per_category // 3),
                "min_total_items": max(15, total_items // 15)
            }
    
    """Check if Cloudinary is properly configured"""
    @property
    def cloudinary_configured(self) -> bool:
        return bool(
            self.CLOUDINARY_CLOUD_NAME 
            and self.CLOUDINARY_API_KEY 
            and self.CLOUDINARY_API_SECRET
        )

settings = Settings()
