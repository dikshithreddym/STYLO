from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models
from ..reco.intent import classify_intent_zero_shot
from ..reco.selector import assemble_outfits


router = APIRouter(prefix="/v2", tags=["suggestions-v2"])


class V2SuggestRequest(BaseModel):
    text: str
    limit: Optional[int] = 3


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


class V2SuggestResponse(BaseModel):
    intent: str
    outfits: List[V2Outfit]


def _model_to_dict(it: models.WardrobeItem) -> dict:
    return {
        "id": it.id,
        "name": getattr(it, "type", None) or "",
        "category": it.category,
        "color": getattr(it, "color", None),
        "image_url": getattr(it, "image_url", None),
        "description": getattr(it, "image_description", None),
    }


@router.post("/suggestions", response_model=V2SuggestResponse)
def suggest_v2(req: V2SuggestRequest, db: Session = Depends(get_db)):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # 1) Zero-shot classify intent (robust to model errors)
    try:
        intent = classify_intent_zero_shot(text)
    except Exception:
        intent = type("_I", (), {"label": "casual"})()  # simple stub

    # 2) Load wardrobe
    items = db.query(models.WardrobeItem).all()
    wardrobe = [_model_to_dict(it) for it in items]
    if not wardrobe:
        return V2SuggestResponse(intent=intent.label, outfits=[])

    # 3) Assemble outfits (guard against embedding errors)
    try:
        outfits_raw = assemble_outfits(text, wardrobe, label=intent.label, k=req.limit or 3)
    except Exception:
        outfits_raw = []

    # Fallback: if semantic assembly couldn't form an outfit, build a simple one
    if not outfits_raw:
        by_cat: dict[str, list[dict]] = {}
        for it in wardrobe:
            cat = (it.get("category") or "").lower()
            if not cat:
                continue
            by_cat.setdefault(cat, []).append(it)

        def pick_any(candidates: list[dict], *type_hints: str) -> dict | None:
            if not candidates:
                return None
            if type_hints:
                text_hints = [h.lower() for h in type_hints]
                for it in candidates:
                    t = (it.get("name") or "") + " " + (it.get("description") or "")
                    tl = t.lower()
                    if any(h in tl for h in text_hints):
                        return it
            return candidates[0]

        top = pick_any(by_cat.get("top", []), "shirt", "t-shirt", "polo", "blouse", "sweater")
        bottom = pick_any(by_cat.get("bottom", []), "jeans", "pants", "chinos", "skirt", "shorts")
        shoes_pool = by_cat.get("footwear", []) or by_cat.get("shoes", [])
        footwear = pick_any(shoes_pool, "sneaker", "boot", "loafer", "shoe", "sandal")
        layer = pick_any(by_cat.get("layer", []), "jacket", "blazer", "hoodie", "sweater", "cardigan")
        accessories = pick_any(by_cat.get("accessories", []))

        fallback: dict[str, dict] = {}
        if top:
            fallback["top"] = top
        if bottom:
            fallback["bottom"] = bottom
        if footwear:
            fallback["footwear"] = footwear
        if layer:
            fallback["layer"] = layer
        if accessories:
            fallback["accessories"] = accessories

        required_present = len({k for k in fallback.keys()} & {"top", "bottom", "footwear"})
        if required_present >= 2:
            outfits_raw = [fallback]
        else:
            # As last resort, return best-available outfit (e.g., only a layer)
            if fallback:
                outfits_raw = [fallback]

    def to_v2item(d: dict) -> V2Item:
        return V2Item(
            id=d.get("id"),
            name=d.get("name") or "",
            category=d.get("category") or "",
            color=d.get("color"),
            image_url=d.get("image_url"),
        )

    v2_outfits: List[V2Outfit] = []
    for o in outfits_raw:
        v2_outfits.append(
            V2Outfit(
                top=to_v2item(o["top"]) if "top" in o else None,
                bottom=to_v2item(o["bottom"]) if "bottom" in o else None,
                footwear=to_v2item(o["footwear"]) if "footwear" in o else None,
                outerwear=to_v2item(o["layer"]) if "layer" in o else None,
                accessories=to_v2item(o["accessories"]) if "accessories" in o else None,
            )
        )

    return V2SuggestResponse(intent=intent.label, outfits=v2_outfits)
