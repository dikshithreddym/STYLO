from fastapi import APIRouter, HTTPException, Query, Response, Depends
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.schemas import WardrobeItem as WardrobeItemSchema, WardrobeItemCreate
from app.database import WardrobeItem as WardrobeItemModel
from app.database import get_db
from app.utils.cloudinary_helper import (
    upload_image_to_cloudinary,
    delete_image_from_cloudinary,
    get_cloudinary_status,
    build_image_url,
    initialize_cloudinary,
)
from app.config import settings
from app.utils.image_analyzer import analyze_clothing_image, generate_fallback_description
import requests, base64, re
import cloudinary
import cloudinary.uploader
import cloudinary.api

router = APIRouter()


@router.get("", response_model=List[WardrobeItemSchema])
async def get_wardrobe_items(
    response: Response,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search query across type and color"),
    type: Optional[str] = Query(None, description="Filter by item type (exact match)"),
    color: Optional[str] = Query(None, description="Filter by color (partial match)"),
    category: Optional[str] = Query(None, description="Filter by category (top/bottom/shoes/layer/one-piece)"),
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
    query = db.query(WardrobeItemModel)

    # Filtering
    if q:
        q_lower = q.lower()
        query = query.filter(
            (WardrobeItemModel.type.ilike(f"%{q_lower}%")) |
            (WardrobeItemModel.color.ilike(f"%{q_lower}%"))
        )
    if type:
        query = query.filter(WardrobeItemModel.type.ilike(f"%{type}%"))
    if color:
        query = query.filter(WardrobeItemModel.color.ilike(f"%{color}%"))
    if category:
        query = query.filter(WardrobeItemModel.category.ilike(f"%{category}%"))

    # Sorting
    if sort:
        key = sort.lstrip("-")
        reverse = sort.startswith("-")
        if key not in {"id", "type", "color", "category"}:
            raise HTTPException(status_code=400, detail="Invalid sort field")
        
        order_column = getattr(WardrobeItemModel, key)
        query = query.order_by(order_column.desc() if reverse else order_column.asc())

    # Get total count
    total = query.count()
    
    # Pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    items = query.all()

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


@router.delete("/clear-demo")
async def clear_demo_items(db: Session = Depends(get_db)):
    """Remove demo/seeded items (those without Cloudinary public_id or Unsplash URLs)."""
    removed = 0
    items = db.query(WardrobeItemModel).all()
    for it in items:
        if (not it.cloudinary_id) or (it.image_url and "images.unsplash.com" in it.image_url):
            db.delete(it)
            removed += 1
    db.commit()
    return {"status": "ok", "removed": removed}


@router.delete("/clear-all")
async def clear_all_items(db: Session = Depends(get_db)):
    """Remove all wardrobe items (dangerous)."""
    count = db.query(WardrobeItemModel).count()
    db.query(WardrobeItemModel).delete()
    db.commit()
    return {"status": "ok", "removed": count}


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
    
    db.commit()
    db.refresh(item)
    
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
    
    return Response(status_code=204)


 


@router.post("/seed-demo")
async def seed_demo_data(
    db: Session = Depends(get_db),
    force: bool = Query(False, description="Insert demo items even if DB not empty"),
    mode: str = Query("append", description="append | replace existing items when force=true"),
):
    """Seed the database with a small demo wardrobe if empty.

    - Idempotent: only inserts when there are zero items
    - Normalizes 'shoes' category to 'footwear'
    - Generates fallback image descriptions
    """
    total = db.query(WardrobeItemModel).count()
    if total > 0 and not force:
        return {"status": "skipped", "message": f"Database already has {total} items"}

    if force and mode.lower() == "replace":
        # Danger: wipe table contents then seed
        db.query(WardrobeItemModel).delete()
        db.commit()

    created = 0
    for d in DUMMY_WARDROBE_ITEMS:
        cat = d.get("category") or None
        if cat == "shoes":
            cat = "footwear"
        desc = generate_fallback_description(d["type"], d["color"], cat)
        item = WardrobeItemModel(
            type=d["type"],
            color=d["color"],
            image_url=d.get("image_url"),
            category=cat,
            image_description=desc,
        )
        db.add(item)
        created += 1
    db.commit()
    return {"status": "ok", "created": created, "previous_count": total}


def _infer_category_and_type(name: str, tags: Optional[List[str]] = None) -> Tuple[str, str]:
    """Infer (type, category) from public_id or tags.

    - Uses simple keyword heuristics. Defaults to (name, 'accessories') if unknown.
    """
    tokens = (name or "").lower().replace("-", " ").replace("_", " ").split("/")
    base = tokens[-1] if tokens else name.lower()
    all_text = " ".join(tokens + (tags or []))

    def has(*words: str) -> bool:
        return any(w in all_text for w in words)

    # One-piece
    if has("dress"):
        return ("Dress", "one-piece")
    # Tops
    if has("t shirt", "t-shirt", "tshirt", "shirt", "polo", "blouse", "sweater"):
        if "dress shirt" in all_text:
            return ("Dress Shirt", "top")
        if "t shirt" in all_text or "t-shirt" in all_text or "tshirt" in all_text:
            return ("T-Shirt", "top")
        if "polo" in all_text:
            return ("Polo", "top")
        if "sweater" in all_text:
            return ("Sweater", "top")
        return ("Shirt", "top")
    # Bottoms
    if has("jean", "jeans"):
        return ("Jeans", "bottom")
    if has("chino", "trouser", "pant"):
        if "short" in all_text:
            return ("Shorts", "bottom")
        return ("Chinos", "bottom")
    if has("skirt"):
        return ("Skirt", "bottom")
    if has("short"):
        return ("Shorts", "bottom")
    # Layer
    if has("blazer"):
        return ("Blazer", "layer")
    if has("jacket"):
        return ("Jacket", "layer")
    if has("hoodie"):
        return ("Hoodie", "layer")
    if has("cardigan"):
        return ("Cardigan", "layer")
    # Footwear
    if has("sneaker", "shoe", "boots", "boot", "loafer", "sandal", "slide"):
        if "sneaker" in all_text:
            return ("Sneakers", "footwear")
        if "loafer" in all_text:
            return ("Loafers", "footwear")
        if "boot" in all_text:
            return ("Boots", "footwear")
        if "sandal" in all_text:
            return ("Sandals", "footwear")
        return ("Shoes", "footwear")
    # Accessories
    if has("watch", "belt", "sunglass", "scarf", "handbag", "bag"):
        if "watch" in all_text:
            return ("Watch", "accessories")
        if "belt" in all_text:
            return ("Belt", "accessories")
        if "sunglass" in all_text:
            return ("Sunglasses", "accessories")
        if "scarf" in all_text:
            return ("Scarf", "accessories")
        if "handbag" in all_text or "bag" in all_text:
            return ("Handbag", "accessories")

    # Fallback
    pretty = base.replace("_", " ").title()
    return (pretty, "accessories")
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
