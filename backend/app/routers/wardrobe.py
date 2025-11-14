from fastapi import APIRouter, HTTPException, Query, Response
from typing import List, Optional
from app.schemas import WardrobeItem, WardrobeItemCreate
from app.data.wardrobe_data import DUMMY_WARDROBE_ITEMS

router = APIRouter()

# In-memory wardrobe state (mutable during session)
wardrobe_items = [dict(item) for item in DUMMY_WARDROBE_ITEMS]
next_id = max(item["id"] for item in wardrobe_items) + 1


@router.get("", response_model=List[WardrobeItem])
async def get_wardrobe_items(
    response: Response,
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
    items = wardrobe_items.copy()

    # Filtering
    if q:
        q_lower = q.lower()
        items = [
            it for it in items if q_lower in it["type"].lower() or q_lower in it["color"].lower()
        ]
    if type:
        items = [it for it in items if it["type"].lower() == type.lower()]
    if color:
        color_lower = color.lower()
        items = [it for it in items if color_lower in it["color"].lower()]
    if category:
        items = [it for it in items if it.get("category", "").lower() == category.lower()]

    # Sorting
    if sort:
        key = sort.lstrip("-")
        reverse = sort.startswith("-")
        if key not in {"id", "type", "color", "category"}:
            raise HTTPException(status_code=400, detail="Invalid sort field")
        items.sort(key=lambda x: x[key], reverse=reverse)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    sliced = items[start:end]

    # Always set total count header for pagination
    response.headers["X-Total-Count"] = str(total)

    return sliced


@router.get("/{item_id}", response_model=WardrobeItem)
async def get_wardrobe_item(item_id: int):
    """
    Get a specific wardrobe item by ID
    """
    item = next((item for item in wardrobe_items if item["id"] == item_id), None)
    if item:
        return item
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("", response_model=WardrobeItem, status_code=201)
async def create_wardrobe_item(payload: WardrobeItemCreate):
    """
    Add a new item to the wardrobe
    """
    global next_id
    new_item = {
        "id": next_id,
        "type": payload.type,
        "color": payload.color,
        "image_url": payload.image_url,
        "category": payload.category,
    }
    wardrobe_items.append(new_item)
    next_id += 1
    return new_item


@router.delete("/{item_id}", status_code=204)
async def delete_wardrobe_item(item_id: int):
    """
    Delete a wardrobe item by ID
    """
    global wardrobe_items
    item = next((it for it in wardrobe_items if it["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    wardrobe_items = [it for it in wardrobe_items if it["id"] != item_id]
    return Response(status_code=204)
