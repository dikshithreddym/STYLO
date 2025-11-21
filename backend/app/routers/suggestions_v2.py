from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..database import WardrobeItem
from ..reco.intent import classify_intent_zero_shot
from ..reco.selector import assemble_outfits
from ..reco.retriever import retrieve_relevant_items
from ..utils.gemini_suggest import suggest_outfit_with_gemini
from ..utils.profiler import get_profiler, reset_profiler
from ..config import settings
from ..utils.cache import get_cached_suggestion, set_cached_suggestion
import hashlib
import json


router = APIRouter(prefix="/v2", tags=["suggestions-v2"])


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
        "embedding": it.embedding,  # Include stored embedding if available
    }


@router.post("/suggestions", response_model=V2SuggestResponse)
async def suggest_v2(req: V2SuggestRequest, db: Session = Depends(get_db)):
    # Reset profiler for this request
    profiler = reset_profiler()
    
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # 1) Load wardrobe (with RAG filtering if enabled)
    with profiler.measure("db_wardrobe_load"):
        if settings.RAG_ENABLED:
            try:
                # Use adaptive thresholds (None = auto-calculate based on data volume)
                items = retrieve_relevant_items(
                    query=text,
                    db=db,
                    limit_per_category=None,  # Auto-calculate from data volume
                    min_items_per_category=None,  # Auto-calculate from data volume
                    min_total_items=None,  # Auto-calculate from data volume
                    use_intent_boost=True
                )
            except Exception as e:
                # Fallback to full wardrobe on retrieval error
                print(f"RAG retrieval failed, using full wardrobe: {e}")
                items = db.query(WardrobeItem).all()
        else:
            items = db.query(WardrobeItem).all()
    
    wardrobe = [_model_to_dict(it) for it in items]
    if not wardrobe:
        profiler.log_summary("[Suggest] ")
        return V2SuggestResponse(intent="none", outfits=[])
    
    # Generate cache key based on query and wardrobe items
    wardrobe_hash = hashlib.md5(
        json.dumps([(it.get("id"), it.get("category")) for it in wardrobe[:20]], sort_keys=True).encode()
    ).hexdigest()
    
    # Check cache first
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Checking cache for query: '{text}', wardrobe_hash: {wardrobe_hash[:8]}...")
    cached_result = get_cached_suggestion(text, wardrobe_hash)
    if cached_result:
        logger.info(f"✅ CACHE HIT for query: '{text}'")
        profiler.log_summary("[Suggest] [CACHED] ")
        return V2SuggestResponse(**cached_result)
    else:
        logger.info(f"❌ CACHE MISS for query: '{text}' - will compute and cache result")

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
                    # Cache the result (5 minutes TTL)
                    cache_success = set_cached_suggestion(text, wardrobe_hash, result.dict(), ttl=300)
                    logger.info(f"{'✅ Cached result' if cache_success else '❌ Failed to cache result'} for query: '{text}'")
                    profiler.log_summary("[Suggest] ")
                    return result
        except Exception as e:
            print(f"Gemini suggestion failed, falling back to semantic engine: {e}")

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
    # Cache the result (5 minutes TTL)
    cache_success = set_cached_suggestion(text, wardrobe_hash, result.dict(), ttl=300)
    logger.info(f"{'✅ Cached result' if cache_success else '❌ Failed to cache result'} for query: '{text}'")
    return result
