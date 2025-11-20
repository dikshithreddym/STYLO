"""
Cloudinary image upload helper functions
"""
import cloudinary
import cloudinary.uploader
from cloudinary import CloudinaryImage
import re
from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.config import settings

"""Initialize Cloudinary with configuration from settings"""
def initialize_cloudinary():
    if settings.cloudinary_configured:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        return True
    return False

"""Check if string is a base64 encoded image"""
def is_base64_image(image_data: str) -> bool:
    if not image_data:
        return False
    # Check for data URL format: data:image/...;base64,...
    return image_data.startswith('data:image/')

"""Extract base64 data from data URL"""
def extract_base64_data(data_url: str) -> Optional[str]:
    if not data_url:
        return None
    
    # Pattern: data:image/png;base64,iVBORw0KGgo...
    match = re.match(r'data:image/[^;]+;base64,(.+)', data_url)
    if match:
        return match.group(1)
    return None

"""     Upload an image to Cloudinary
    Args:
        image_data: Base64 data URL or regular URL
        folder: Cloudinary folder name (default: from settings)
        public_id: Custom public ID for the image
        tags: List of tags to add to the image
    Returns:
        Dict with upload result including 'url' and 'public_id'
    Raises:
        HTTPException: If Cloudinary is not configured or upload fails
"""
async def upload_image_to_cloudinary(
    image_data: str,
    folder: Optional[str] = None,
    public_id: Optional[str] = None,
    tags: Optional[list] = None
) -> Dict[str, Any]:
    
    # Check if Cloudinary is enabled and configured
    if not settings.USE_CLOUDINARY:
        raise HTTPException(
            status_code=400,
            detail="Cloudinary upload is disabled. Set USE_CLOUDINARY=true"
        )
    
    if not settings.cloudinary_configured:
        raise HTTPException(
            status_code=500,
            detail="Cloudinary not configured. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET"
        )
    
    # Initialize Cloudinary
    initialize_cloudinary()
    
    # If it's a regular URL (not base64), return as-is or optionally fetch and re-upload
    if not is_base64_image(image_data):
        # For existing URLs (e.g., Unsplash), we can either:
        # 1. Return as-is (no upload needed)
        # 2. Fetch and re-upload to Cloudinary for consistency
        # For now, return as-is
        return {
            "url": image_data,
            "public_id": None,
            "uploaded": False
        }
    
    try:
        # Extract base64 data
        base64_data = extract_base64_data(image_data)
        if not base64_data:
            raise ValueError("Invalid base64 image data")
        
        # Prepare upload options
        upload_options: Dict[str, Any] = {
            "folder": folder or settings.CLOUDINARY_FOLDER,
            "resource_type": "image",
            "transformation": [
                {"quality": "auto:good"},
                {"fetch_format": "auto"}
            ]
        }
        
        if public_id:
            upload_options["public_id"] = public_id
        
        if tags:
            upload_options["tags"] = tags
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            f"data:image/png;base64,{base64_data}",
            **upload_options
        )
        
        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "uploaded": True,
            "width": result.get("width"),
            "height": result.get("height"),
            "format": result.get("format"),
            "bytes": result.get("bytes")
        }
        
    except cloudinary.exceptions.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cloudinary upload failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )


"""    Delete an image from Cloudinary
    Args:
        public_id: The Cloudinary public ID of the image
    Returns:
        bool: True if deletion was successful
"""
async def delete_image_from_cloudinary(public_id: str) -> bool:
    if not settings.cloudinary_configured:
        return False
    
    try:
        initialize_cloudinary()
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
    except Exception as e:
        print(f"Failed to delete image from Cloudinary: {e}")
        return False


def get_cloudinary_status() -> Dict[str, Any]:
    """Get Cloudinary configuration status"""
    return {
        "enabled": settings.USE_CLOUDINARY,
        "configured": settings.cloudinary_configured,
        "cloud_name": settings.CLOUDINARY_CLOUD_NAME if settings.cloudinary_configured else None,
        "folder": settings.CLOUDINARY_FOLDER
    }


def build_image_url(public_id: str, **options) -> str:
    """Build a Cloudinary image URL with transformations.

    Example:
        build_image_url('shoes', fetch_format='auto', quality='auto')
        build_image_url('shoes', crop='auto', gravity='auto', width=500, height=500)
    """
    if not settings.cloudinary_configured:
        raise ValueError("Cloudinary not configured")
    initialize_cloudinary()
    img = CloudinaryImage(public_id)
    # Ensure secure URLs by default
    options.setdefault('secure', True)
    url = img.build_url(**options)
    return url
