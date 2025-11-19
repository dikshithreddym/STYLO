from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models
from ..reco.intent import classify_intent_zero_shot
from ..reco.selector import assemble_outfits
from ..utils.gemini_suggest import suggest_outfit_with_gemini


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
async def suggest_v2(req: V2SuggestRequest, db: Session = Depends(get_db)):
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

    # 3) PRIORITY: Try Gemini API first if GEMINI_API_KEY is configured
    outfits_raw = None
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    used_gemini = False
    
    if gemini_api_key:
        try:
            outfits_raw = await suggest_outfit_with_gemini(text, wardrobe, limit=3)
            if outfits_raw:
                used_gemini = True
        except Exception as e:
            print(f"Gemini suggestion failed, falling back to semantic engine: {e}")
            outfits_raw = None
    
    # 4) Fallback to semantic embedding-based engine if Gemini not available/failed
    if not outfits_raw:
        try:
            # Limit to 3 variations
            outfits_raw = assemble_outfits(text, wardrobe, label=intent.label, k=3)
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

    # Score and generate rationale for each outfit
    def score_outfit(outfit_dict: dict, query: str, intent_label: str) -> tuple[float, str]:
        """
        Score outfit match (0-100%) and generate rationale.
        
        Returns:
            (score: float 0-1.0, rationale: str)
        """
        # Calculate completeness score
        required_cats = {"top", "bottom", "footwear"}
        present_cats = {cat for cat in required_cats if cat in outfit_dict and outfit_dict[cat]}
        completeness = len(present_cats) / len(required_cats)  # 0-1.0
        
        # Calculate semantic match score (if using semantic engine)
        if not used_gemini:
            # For semantic engine, use embedding similarity
            from ..reco.embedding import Embedder
            from ..reco.color_matcher import infer_palette, palette_score
            
            emb = Embedder.instance()
            qv = emb.encode([query])[0]
            
            item_texts = [
                f"{outfit_dict.get(cat, {}).get('name', '')} {outfit_dict.get(cat, {}).get('description', '')}".strip()
                for cat in ["top", "bottom", "footwear", "layer", "accessories"]
                if cat in outfit_dict and outfit_dict[cat]
            ]
            
            if item_texts:
                ivecs = emb.encode(item_texts)
                # Calculate cosine similarity
                from ..reco.selector import _cosine as cosine_sim
                sims = [max(0.0, cosine_sim(qv, v)) for v in ivecs]
                semantic_score = float(sum(sims) / len(sims)) if sims else 0.5
            else:
                semantic_score = 0.5
            
            # Color harmony score
            palette = infer_palette(outfit_dict)
            color_score = palette_score(palette)
            
            # Combined score: completeness (40%), semantic (40%), color (20%)
            total_score = 0.4 * completeness + 0.4 * semantic_score + 0.2 * color_score
        else:
            # For Gemini, assume high match (Gemini handles matching internally)
            # Could enhance with post-scoring if needed
            total_score = 0.95 * completeness + 0.05  # High confidence if Gemini selected it
        
        # Generate rationale
        rationale_parts = []
        
        # Occasion/intent reasoning
        if intent_label == "business":
            rationale_parts.append(f"This professional outfit is perfect for business settings.")
        elif intent_label == "formal":
            rationale_parts.append(f"This sophisticated ensemble is ideal for formal occasions.")
        elif intent_label == "party":
            rationale_parts.append(f"This stylish combination works great for social gatherings.")
        elif intent_label == "casual":
            rationale_parts.append(f"This relaxed outfit is perfect for casual occasions.")
        elif intent_label == "workout":
            rationale_parts.append(f"This athletic outfit is designed for active wear.")
        elif intent_label == "beach":
            rationale_parts.append(f"This lightweight outfit is perfect for beach activities.")
        elif intent_label == "hiking":
            rationale_parts.append(f"This practical outfit is ideal for outdoor activities.")
        
        # Item selection reasoning
        items_mentioned = []
        if "top" in outfit_dict and outfit_dict["top"]:
            top_name = outfit_dict["top"].get("name", "top")
            items_mentioned.append(top_name)
        if "bottom" in outfit_dict and outfit_dict["bottom"]:
            bottom_name = outfit_dict["bottom"].get("name", "bottom")
            items_mentioned.append(bottom_name)
        if "footwear" in outfit_dict and outfit_dict["footwear"]:
            shoe_name = outfit_dict["footwear"].get("name", "footwear")
            items_mentioned.append(shoe_name)
        
        if items_mentioned:
            rationale_parts.append(f"Selected {', '.join(items_mentioned[:3])} based on your query.")
        
        # Completeness note
        if completeness < 1.0:
            missing = required_cats - present_cats
            if missing:
                rationale_parts.append(f"Note: Missing {', '.join(missing)} from your wardrobe.")
        
        # Match confidence
        if total_score >= 0.9:
            rationale_parts.append("This is an excellent match for your request!")
        elif total_score >= 0.7:
            rationale_parts.append("This outfit works well for your needs.")
        else:
            rationale_parts.append("This is the best available match from your wardrobe.")
        
        rationale = " ".join(rationale_parts) if rationale_parts else "Selected outfit based on your request."
        
        # Convert to percentage (0-100)
        score_percentage = total_score * 100
        
        return score_percentage, rationale
    
    v2_outfits: List[V2Outfit] = []
    for o in outfits_raw:
        score, rationale = score_outfit(o, text, intent.label)
        v2_outfits.append(
            V2Outfit(
                top=to_v2item(o["top"]) if "top" in o else None,
                bottom=to_v2item(o["bottom"]) if "bottom" in o else None,
                footwear=to_v2item(o["footwear"]) if "footwear" in o else None,
                outerwear=to_v2item(o["layer"]) if "layer" in o else None,
                accessories=to_v2item(o["accessories"]) if "accessories" in o else None,
                score=score,
                rationale=rationale,
            )
        )
    
    # Sort by score (highest first) and limit to 3
    v2_outfits.sort(key=lambda x: x.score, reverse=True)
    v2_outfits = v2_outfits[:3]

    return V2SuggestResponse(intent=intent.label, outfits=v2_outfits)
