from fastapi import APIRouter, HTTPException, Query, Response, Depends
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.schemas import WardrobeItem as WardrobeItemSchema, WardrobeItemCreate
from app.database import WardrobeItem as WardrobeItemModel
from app.database import get_db
from app.utils.cloudinary_helper import (
    upload_image_to_cloudinary,
    delete_image_from_cloudinary,
    get_cloudinary_status,
)
from app.config import settings
from app.utils.image_analyzer import analyze_clothing_image, generate_fallback_description
from app.utils.embedding_service import queue_embedding_refresh
from app.utils.cache import cache_clear_pattern
import requests, base64
import cloudinary
import cloudinary.api

router = APIRouter()


@router.get("", response_model=List[WardrobeItemSchema])
async def get_wardrobe_items(
    response: Response,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(100, ge=1, le=100, description="Items per page (max 100)"),
):
    """
    Get wardrobe items with pagination.
    Filtering and sorting are handled client-side for better performance.
    """
    # Simple query - no filtering or sorting (handled on frontend)
    query = db.query(WardrobeItemModel)
    
    # Get total count
    total = query.count()
    
    # Pagination
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # Set total count header
    response.headers["X-Total-Count"] = str(total)
    
    return [item.to_dict() for item in items]


# IMPORTANT: Specific routes must come BEFORE parameterized routes like /{item_id}
@router.get("/cloudinary-status")
async def cloudinary_status():
    """
    Check Cloudinary configuration status
    """
    return get_cloudinary_status()

@router.delete("/clear-all")
async def clear_all_items(db: Session = Depends(get_db)):
    """Remove all wardrobe items (dangerous)."""
    count = db.query(WardrobeItemModel).count()
    db.query(WardrobeItemModel).delete()
    db.commit()
    return {"status": "ok", "removed": count}


class RefreshEmbeddingsRequest(BaseModel):
    item_ids: Optional[List[int]] = None


@router.post("/refresh-embeddings")
async def refresh_embeddings(
    request: Optional[RefreshEmbeddingsRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Batch refresh embeddings for wardrobe items.
    If item_ids is provided in request body, refresh only those items.
    Otherwise, refresh all items that don't have embeddings yet.
    """
    from app.utils.embedding_service import batch_refresh_embeddings
    
    item_ids = request.item_ids if request else None
    refreshed = batch_refresh_embeddings(db, item_ids)
    return {
        "status": "ok",
        "refreshed": refreshed,
        "message": f"Refreshed embeddings for {refreshed} items"
    }


@router.post("/sync-cloudinary")
async def sync_from_cloudinary(
    db: Session = Depends(get_db),
    folder: Optional[str] = Query(None, description="Cloudinary folder prefix; defaults to settings.CLOUDINARY_FOLDER"),
    max_results: int = Query(100, ge=1, le=500, description="Max resources to pull per page"),
):
    """Create wardrobe items from existing Cloudinary images in the configured folder.

    - Skips images already present (matched by cloudinary_id)
    - Infers type/category from public_id/tags heuristically
    - Uses secure URL and stores cloudinary_id for deletion
    """
    from app.utils.cloudinary_helper import initialize_cloudinary
    if not settings.cloudinary_configured:
        raise HTTPException(status_code=400, detail="Cloudinary not configured")

    initialize_cloudinary()
    prefix = folder or settings.CLOUDINARY_FOLDER
    created = 0

    next_cursor = None
    while True:
        params = {
            "type": "upload",
            "prefix": prefix if prefix else None,
            "max_results": max_results,
            "next_cursor": next_cursor,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        res = cloudinary.api.resources(**params)
        resources = res.get("resources", [])
        for r in resources:
            public_id = r.get("public_id")
            secure_url = r.get("secure_url") or r.get("url")
            tags = r.get("tags") or []

            # Skip if already imported
            existing = db.query(WardrobeItemModel).filter(WardrobeItemModel.cloudinary_id == public_id).first()
            if existing:
                continue

            inferred_type, category = _infer_category_and_type(public_id or "", tags)
            # Simple color inference from tags or public_id tokens
            color = None
            for c in ["black", "white", "navy", "blue", "green", "olive", "grey", "gray", "beige", "khaki", "burgundy", "charcoal", "brown"]:
                if c in (" ".join(tags) + " " + (public_id or "")).lower():
                    color = c.title() if c != "navy" else "Navy Blue"
                    break
            if color is None:
                color = "Unknown"

            desc = generate_fallback_description(inferred_type, color, category)
            item = WardrobeItemModel(
                type=inferred_type,
                color=color,
                image_url=secure_url,
                category=category,
                cloudinary_id=public_id,
                image_description=desc,
            )
            db.add(item)
            created += 1

        db.commit()

        next_cursor = res.get("next_cursor")
        if not next_cursor:
            break

    return {"status": "ok", "created": created, "folder": prefix}


@router.post("/recategorize")
async def recategorize_from_descriptions(db: Session = Depends(get_db)):
    """Re-categorize items based on their Gemini-generated descriptions"""
    items = db.query(WardrobeItemModel).all()
    updated = 0
    
    for item in items:
        desc = (item.image_description or "").lower()
        old_cat = item.category
        
        # Infer category from description
        if any(kw in desc for kw in ["t-shirt", "shirt", "polo", "blouse", "tank", "sweater", "pullover"]):
            item.category = "top"
        elif any(kw in desc for kw in ["trouser", "pant", "jean", "chino", "short"]):
            item.category = "bottom"
        elif any(kw in desc for kw in ["jacket", "blazer", "hoodie", "coat", "cardigan", "wetsuit"]):
            item.category = "layer"
        elif any(kw in desc for kw in ["shoe", "sneaker", "boot", "loafer", "sandal", "slide"]):
            item.category = "footwear"
        elif any(kw in desc for kw in ["watch", "belt", "scarf", "jewelry", "sunglass", "bracelet"]):
            item.category = "accessories"
        
        if item.category != old_cat:
            updated += 1
    
    db.commit()
    return {"status": "ok", "updated": updated}


@router.get("/{item_id}", response_model=WardrobeItemSchema)
async def get_wardrobe_item(item_id: int, db: Session = Depends(get_db)):
    """
    Get a specific wardrobe item by ID
    """
    item = db.query(WardrobeItemModel).filter(WardrobeItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.to_dict()


@router.post("", response_model=WardrobeItemSchema, status_code=201)
async def create_wardrobe_item(payload: WardrobeItemCreate, db: Session = Depends(get_db)):
    """
    Add a new item to the wardrobe
    """
    # Preserve original image data (may be base64 data URL)
    original_image_data = payload.image_url

    # Handle image upload to Cloudinary if enabled
    image_url = original_image_data
    cloudinary_public_id = None
    
    if image_url and settings.USE_CLOUDINARY and settings.cloudinary_configured:
        try:
            # Upload to Cloudinary
            upload_result = await upload_image_to_cloudinary(
                image_data=image_url,
                tags=["wardrobe", payload.type.lower(), payload.category] if payload.category else ["wardrobe", payload.type.lower()]
            )
            if upload_result.get("uploaded"):
                image_url = upload_result["url"]
                cloudinary_public_id = upload_result.get("public_id")
        except HTTPException:
            # If Cloudinary upload fails, fall back to original URL
            pass
    
    # Create new item in database
    # Attempt AI / fallback description generation
    description: str | None = None
    try:
        if image_url:
            base64_data: str | None = None
            # If original was a data URL, keep that for analysis
            if original_image_data and isinstance(original_image_data, str) and original_image_data.startswith("data:image/"):
                base64_data = original_image_data
            # Otherwise download the final image_url and convert to base64 data URL
            elif image_url.startswith("http"):
                resp = requests.get(image_url, timeout=10)
                if resp.status_code == 200:
                    mime = resp.headers.get("content-type", "image/jpeg")
                    encoded = base64.b64encode(resp.content).decode("utf-8")
                    base64_data = f"data:{mime};base64,{encoded}"
            # Run AI analyzer if we constructed a base64 payload
            if base64_data:
                ai_result = None
                try:
                    ai_result = await analyze_clothing_image(base64_data)
                except Exception:
                    ai_result = None
                if ai_result:
                    description = ai_result
        # Fallback description if AI missing or failed
        if description is None:
            description = generate_fallback_description(payload.type, payload.color, payload.category)
    except Exception:
        # Final safeguard: still provide fallback
        description = generate_fallback_description(payload.type, payload.color, payload.category)

    new_item = WardrobeItemModel(
        type=payload.type,
        color=payload.color,
        image_url=image_url,
        category=payload.category,
        cloudinary_id=cloudinary_public_id,
        image_description=description,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    # Queue async embedding refresh (non-blocking)
    queue_embedding_refresh(new_item.id)
    
    return new_item.to_dict()


@router.patch("/{item_id}", response_model=WardrobeItemSchema)
async def update_wardrobe_item(item_id: int, payload: WardrobeItemCreate, db: Session = Depends(get_db)):
    """
    Update a wardrobe item by ID
    """
    item = db.query(WardrobeItemModel).filter(WardrobeItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update fields
    item.type = payload.type
    item.color = payload.color
    item.category = payload.category
    
    # Update image if provided
    if payload.image_url and payload.image_url != item.image_url:
        # Handle new image upload to Cloudinary if enabled
        image_url = payload.image_url
        cloudinary_public_id = item.cloudinary_id
        
        if image_url and settings.USE_CLOUDINARY and settings.cloudinary_configured:
            try:
                # Delete old image if exists
                if item.cloudinary_id:
                    await delete_image_from_cloudinary(item.cloudinary_id)
                
                # Upload new image
                upload_result = await upload_image_to_cloudinary(
                    image_data=image_url,
                    tags=["wardrobe", payload.type.lower(), payload.category] if payload.category else ["wardrobe", payload.type.lower()]
                )
                if upload_result.get("uploaded"):
                    image_url = upload_result["url"]
                    cloudinary_public_id = upload_result.get("public_id")
            except HTTPException:
                pass
        
        item.image_url = image_url
        item.cloudinary_id = cloudinary_public_id
    
    # Check if any fields that affect embedding have changed
    embedding_fields_changed = (
        payload.type != item.type or
        payload.color != item.color or
        payload.category != item.category or
        (payload.image_url and payload.image_url != item.image_url)
    )
    
    db.commit()
    db.refresh(item)
    
    # Invalidate suggestion cache (wardrobe changes affect suggestions)
    cache_clear_pattern("suggestion:*")
    
    # Queue async embedding refresh if relevant fields changed (non-blocking)
    if embedding_fields_changed:
        queue_embedding_refresh(item.id)
    
    return item.to_dict()


@router.delete("/{item_id}", status_code=204)
async def delete_wardrobe_item(item_id: int, db: Session = Depends(get_db)):
    """
    Delete a wardrobe item by ID
    """
    item = db.query(WardrobeItemModel).filter(WardrobeItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Delete from Cloudinary if it was uploaded there
    if item.cloudinary_id:
        await delete_image_from_cloudinary(item.cloudinary_id)
    
    db.delete(item)
    db.commit()
    
    # Invalidate suggestion cache (wardrobe changes affect suggestions)
    cache_clear_pattern("suggestion:*")
    
    return Response(status_code=204)

