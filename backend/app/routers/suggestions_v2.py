import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database import get_async_db, User
from ..database import WardrobeItem
from ..utils.auth import get_current_user_async
from ..reco.intent import classify_intent_zero_shot
from ..reco.selector import assemble_outfits
from ..reco.retriever import retrieve_relevant_items_async
from ..utils.gemini_suggest import suggest_outfit_with_gemini
from ..utils.profiler import get_profiler, reset_profiler
from ..config import settings
from ..utils.cache import get_cached_suggestion, set_cached_suggestion
import hashlib
import json

# Rate limiter for suggestion endpoints (ML/Gemini calls are expensive)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/v2",
    tags=["Outfit Suggestions"],
    responses={
        401: {"description": "Not authenticated - invalid or expired token"},
        429: {"description": "Too many requests - rate limit exceeded"},
        503: {"description": "AI service temporarily unavailable"},
    }
)


class V2SuggestRequest(BaseModel):
    text: str
    limit: Optional[int] = 3  # Max 3 variations (enforced)


class V2Item(BaseModel):
    id: int
    name: str
    category: str
    color: Optional[str] = None
    image_url: Optional[str] = None


class V2Outfit(BaseModel):
    top: Optional[V2Item] = None
    bottom: Optional[V2Item] = None
    footwear: Optional[V2Item] = None
    outerwear: Optional[V2Item] = None
    accessories: Optional[V2Item] = None
    score: float = 0.0  # Outfit match score (0-100% or 0-1.0)
    rationale: Optional[str] = None  # Reason why this outfit was selected


# Helper to convert dict to V2Item
def to_v2item(item: dict) -> Optional[V2Item]:
    if not item:
        return None
    return V2Item(
        id=item.get("id"),
        name=item.get("name", ""),
        category=item.get("category", ""),
        color=item.get("color"),
        image_url=item.get("image_url"),
    )


class V2SuggestResponse(BaseModel):
    intent: str
    outfits: List[V2Outfit]


def _model_to_dict(it: WardrobeItem) -> dict:
    return {
        "id": it.id,
        "name": getattr(it, "type", None) or "",
        "category": it.category,
        "color": getattr(it, "color", None),
        "image_url": getattr(it, "image_url", None),
        "description": getattr(it, "image_description", None),
        # Embedding removed - not needed by frontend, saves ~1.5KB per item
    }


@router.post("/suggestions", response_model=V2SuggestResponse)
@limiter.limit("30/minute")  # Rate limit ML/Gemini calls to prevent abuse
async def suggest_v2(request: Request, req: V2SuggestRequest, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user_async)):
    # Reset profiler for this request
    profiler = reset_profiler()
    
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # IMPORTANT: Check cache FIRST, before any database operations
    # This ensures cached requests return in < 0.1 seconds
    import logging
    logger = logging.getLogger(__name__)
    query_normalized = text.lower().strip()
    
    # Use user-specific cache key to prevent sharing suggestions across users
    cache_key_suffix = f"fixed:{current_user.id}"
    
    logger.info(f"🔍 Checking cache FIRST for query: '{text}' (normalized: '{query_normalized}') user: {current_user.id}")
    cached_result = get_cached_suggestion(query_normalized, cache_key_suffix)
    if cached_result:
        logger.info(f"✅ CACHE HIT for query: '{text}' - returning immediately (skipped DB load)")
        profiler.log_summary("[Suggest] [CACHED] ")
        return V2SuggestResponse(**cached_result)
    else:
        logger.info(f"❌ CACHE MISS for query: '{text}' - will load wardrobe and compute")

    # 1) Load wardrobe (with RAG filtering if enabled) - only if cache miss
    with profiler.measure("db_wardrobe_load"):
        if settings.RAG_ENABLED:
            try:
                # Use adaptive thresholds (None = auto-calculate based on data volume)
                items = await retrieve_relevant_items_async(
                    query=text,
                    db=db,
                    user_id=current_user.id,
                    limit_per_category=None,  # Auto-calculate from data volume
                    min_items_per_category=None,  # Auto-calculate from data volume
                    min_total_items=None,  # Auto-calculate from data volume
                    use_intent_boost=True
                )
            except Exception as e:
                # Fallback to full wardrobe (filtered by user) on retrieval error
                logger.warning(f"RAG retrieval failed, using full wardrobe: {e}")
                result = await db.execute(
                    select(WardrobeItem).where(WardrobeItem.user_id == current_user.id)
                )
                items = result.scalars().all()
        else:
            result = await db.execute(
                select(WardrobeItem).where(WardrobeItem.user_id == current_user.id)
            )
            items = result.scalars().all()
    
    wardrobe = [_model_to_dict(it) for it in items]
    if not wardrobe:
        profiler.log_summary("[Suggest] ")
        return V2SuggestResponse(intent="none", outfits=[])
    
    wardrobe_count = len(wardrobe)
    logger.info(f"Loaded {wardrobe_count} wardrobe items, proceeding with computation")

    # 2) Try Gemini API first
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        try:
            with profiler.measure("gemini_api"):
                gemini_result = await suggest_outfit_with_gemini(text, wardrobe, limit=3)
            if gemini_result:
                intent = gemini_result.get("intent", "none")
                outfits_raw = gemini_result.get("outfits", [])
                v2_outfits = []
                for o in outfits_raw:
                    # Extract rationale from the outfit dict (set by Gemini)
                    rationale = o.get("rationale", "This outfit was selected based on your request and wardrobe items.")
                    v2_outfits.append(
                        V2Outfit(
                            top=to_v2item(o.get("top")) if o.get("top") else None,
                            bottom=to_v2item(o.get("bottom")) if o.get("bottom") else None,
                            footwear=to_v2item(o.get("footwear")) if o.get("footwear") else None,
                            outerwear=to_v2item(o.get("layer")) if o.get("layer") else None,
                            accessories=to_v2item(o.get("accessories")) if o.get("accessories") else None,
                            score=100.0,
                            rationale=rationale,  # Use the actual rationale from Gemini
                        )
                    )
                if v2_outfits:
                    result = V2SuggestResponse(intent=intent, outfits=v2_outfits)
                    # Cache the result (5 minutes TTL) - use fixed hash for consistency
                    cache_success = set_cached_suggestion(query_normalized, cache_key_suffix, result.dict(), ttl=300)
                    logger.info(f"{'✅ Cached result' if cache_success else '❌ Failed to cache result'} for query: '{text}'")
                    profiler.log_summary("[Suggest] ")
                    return result
        except Exception as e:
            logger.warning(f"Gemini suggestion failed, falling back to semantic engine: {e}")

    # 3) Fallback to semantic embedding-based engine if Gemini not available/failed
    from ..reco.intent import classify_intent_zero_shot
    try:
        with profiler.measure("embedding_intent_classification"):
            intent_obj = classify_intent_zero_shot(text)
        intent = getattr(intent_obj, "label", "none")
    except Exception:
        intent = "casual"
    try:
        with profiler.measure("embedding_outfit_assembly"):
            from ..reco.selector import assemble_outfits
            outfits_raw = assemble_outfits(text, wardrobe, label=intent, k=3)
    except Exception:
        outfits_raw = []
    v2_outfits = []
    for o in outfits_raw:
        v2_outfits.append(
            V2Outfit(
                top=to_v2item(o.get("top")) if o.get("top") else None,
                bottom=to_v2item(o.get("bottom")) if o.get("bottom") else None,
                footwear=to_v2item(o.get("footwear")) if o.get("footwear") else None,
                outerwear=to_v2item(o.get("layer")) if o.get("layer") else None,
                accessories=to_v2item(o.get("accessories")) if o.get("accessories") else None,
                score=80.0,
                rationale="Semantic engine generated outfit",
            )
        )
    
    profiler.log_summary("[Suggest] ")
    result = V2SuggestResponse(intent=intent, outfits=v2_outfits) if v2_outfits else V2SuggestResponse(intent=intent, outfits=[])
    # Cache the result (5 minutes TTL) - use fixed hash for consistency
    cache_success = set_cached_suggestion(query_normalized, cache_key_suffix, result.dict(), ttl=300)
    logger.info(f"{'✅ Cached result' if cache_success else '❌ Failed to cache result'} for query: '{text}'")
    return result
