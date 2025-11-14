from fastapi import APIRouter, HTTPException, Query, Response, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from app.schemas import WardrobeItem, WardrobeItemCreate
from app.database import get_db
from app import models
from app.utils.cloudinary_helper import (
    upload_image_to_cloudinary,
    delete_image_from_cloudinary,
    get_cloudinary_status,
    build_image_url,
    initialize_cloudinary,
)
from app.utils.image_analyzer import analyze_clothing_image, generate_fallback_description
from app.config import settings
import cloudinary
import cloudinary.uploader

router = APIRouter()


@router.get("", response_model=List[WardrobeItem])
async def get_wardrobe_items(
    response: Response,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search query across type and color"),
    type: Optional[str] = Query(None, description="Filter by item type (exact match)"),
    color: Optional[str] = Query(None, description="Filter by color (partial match)"),
    category: Optional[str] = Query(None, description="Filter by category (top/bottom/footwear/layer/one-piece/accessories)"),
    sort: Optional[str] = Query(
        None,
        description="Sort by field. Use prefix '-' for descending. Allowed: id, type, color",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(12, ge=1, le=100, description="Items per page"),
):
    """
    Get wardrobe items with optional filtering and sorting.
    """
    query = db.query(models.WardrobeItem)

    # Filtering
    if q:
        q_lower = f"%{q.lower()}%"
        query = query.filter(
            (models.WardrobeItem.type.ilike(q_lower)) |
            (models.WardrobeItem.color.ilike(q_lower))
        )
    if type:
        query = query.filter(models.WardrobeItem.type.ilike(type))
    if color:
        query = query.filter(models.WardrobeItem.color.ilike(f"%{color}%"))
    if category:
        query = query.filter(models.WardrobeItem.category.ilike(category))

    # Get total count before pagination
    total = query.count()

    # Sorting
    if sort:
        key = sort.lstrip("-")
        reverse = sort.startswith("-")
        if key not in {"id", "type", "color", "category"}:
            raise HTTPException(status_code=400, detail="Invalid sort field")
        
        sort_column = getattr(models.WardrobeItem, key)
        if reverse:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    # Pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    # Set total count header for pagination
    response.headers["X-Total-Count"] = str(total)

    return [item.to_dict() for item in items]


# IMPORTANT: Specific routes must come BEFORE parameterized routes like /{item_id}
@router.get("/cloudinary-status")
async def cloudinary_status():
    """
    Check Cloudinary configuration status
    """
    return get_cloudinary_status()


@router.post("/cloudinary-test")
async def cloudinary_test():
    """Server-side emulation of the provided JS snippet.

    - Uploads a demo image by URL with a fixed public_id
    - Returns upload result and two transformed URLs (optimize + auto-crop)
    """
    status = get_cloudinary_status()
    if not status["enabled"] or not status["configured"]:
        raise HTTPException(status_code=400, detail="Cloudinary not enabled/configured")

    # Initialize Cloudinary
    initialize_cloudinary()

    # Upload the demo image (idempotent: reusing public_id overwrites/updates)
    demo_url = "https://res.cloudinary.com/demo/image/upload/getting-started/shoes.jpg"
    public_id = f"{status['folder']}/demo_shoes"

    try:
        upload_result = cloudinary.uploader.upload(
            demo_url,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    # Build optimized and auto-crop URLs (like the JS example)
    optimize_url = build_image_url(public_id, fetch_format="auto", quality="auto")
    auto_crop_url = build_image_url(
        public_id,
        crop="auto",
        gravity="auto",
        width=500,
        height=500,
    )

    return {
        "upload": {
            "public_id": upload_result.get("public_id"),
            "url": upload_result.get("secure_url"),
            "width": upload_result.get("width"),
            "height": upload_result.get("height"),
            "format": upload_result.get("format"),
            "bytes": upload_result.get("bytes"),
        },
        "optimize_url": optimize_url,
        "auto_crop_url": auto_crop_url,
    }


@router.get("/{item_id}", response_model=WardrobeItem)
async def get_wardrobe_item(item_id: int, db: Session = Depends(get_db)):
    """
    Get a specific wardrobe item by ID
    """
    item = db.query(models.WardrobeItem).filter(models.WardrobeItem.id == item_id).first()
    if item:
        return item.to_dict()
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("", response_model=WardrobeItem, status_code=201)
async def create_wardrobe_item(payload: WardrobeItemCreate, db: Session = Depends(get_db)):
    """
    Add a new item to the wardrobe
    """
    # Handle image upload to Cloudinary if enabled
    image_url = payload.image_url
    cloudinary_public_id = None
    image_description = None
    
    if image_url and settings.USE_CLOUDINARY and settings.cloudinary_configured:
        try:
            # Upload to Cloudinary
            upload_result = await upload_image_to_cloudinary(
                image_data=image_url,
                tags=["wardrobe", payload.type.lower(), payload.category]
            )
            if upload_result.get("uploaded"):
                image_url = upload_result["url"]
                cloudinary_public_id = upload_result.get("public_id")
        except HTTPException:
            # If Cloudinary upload fails, fall back to base64 storage
            pass
    
    # Generate AI description if image is provided
    if image_url:
        # Try to generate AI description
        image_description = await analyze_clothing_image(image_url)
        
        # If AI analysis fails, use fallback description
        if not image_description:
            image_description = generate_fallback_description(
                payload.type, 
                payload.color, 
                payload.category
            )
    
    new_item = models.WardrobeItem(
        type=payload.type,
        color=payload.color,
        image_url=image_url,
        category=payload.category,
        cloudinary_id=cloudinary_public_id,
        image_description=image_description,
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return new_item.to_dict()


@router.delete("/{item_id}", status_code=204)
async def delete_wardrobe_item(item_id: int, db: Session = Depends(get_db)):
    """
    Delete a wardrobe item by ID
    """
    item = db.query(models.WardrobeItem).filter(models.WardrobeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Delete from Cloudinary if it was uploaded there
    if item.cloudinary_id:
        await delete_image_from_cloudinary(item.cloudinary_id)
    
    db.delete(item)
    db.commit()
    
    return Response(status_code=204)
