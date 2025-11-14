from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.schemas import WardrobeItem, SuggestRequest, SuggestResponse, Outfit
import os

router = APIRouter()

# Import shared wardrobe items accessor
def get_wardrobe_items():
    from app.routers.wardrobe import wardrobe_items
    return wardrobe_items

COLOR_WORDS = {
    "black", "white", "navy", "blue", "green", "olive", "grey", "gray",
    "beige", "khaki", "burgundy", "charcoal", "dark", "light"
}

OCCASION_KEYWORDS = {
    "formal": {"formal", "wedding", "ceremony", "black tie", "reception"},
    "business": {"business", "office", "interview", "meeting", "work"},
    "smart casual": {"smart", "smart casual", "semi-formal"},
    "party": {"party", "night out", "club", "birthday"},
    "casual": {"casual", "hangout", "weekend", "everyday", "relaxed"},
}

WEATHER_KEYWORDS = {
    "cold": {"cold", "winter", "chilly", "freezing"},
    "hot": {"hot", "summer", "warm", "heat"},
    "rain": {"rain", "rainy", "wet"},
}


def _text_tokens(text: str) -> List[str]:
    import re
    return re.findall(r"[a-zA-Z]+", text.lower())


def _preferred_colors(tokens: List[str]) -> List[str]:
    # Collect color words that appear in text
    found = []
    for t in tokens:
        if t in COLOR_WORDS and t not in found:
            found.append(t)
    return found


def _detect_occasion(tokens: List[str]) -> str:
    token_set = set(tokens)
    for name, keys in OCCASION_KEYWORDS.items():
        if token_set & keys:
            return name
    # default
    return "casual"


def _detect_weather(tokens: List[str]) -> Optional[str]:
    token_set = set(tokens)
    for w, keys in WEATHER_KEYWORDS.items():
        if token_set & keys:
            return w
    return None


def _pick(preferred_type: str, colors: List[str], used_ids: set[int], category: Optional[str] = None) -> Optional[dict]:
    # Try exact type match first, prefer preferred colors
    items = get_wardrobe_items()
    candidates = [
        it for it in items
        if it["type"].lower() == preferred_type.lower()
        and it["id"] not in used_ids
        and (category is None or it.get("category") == category)
    ]
    if colors:
        for c in colors:
            for it in candidates:
                if c in it["color"].lower():
                    return it
    if candidates:
        return candidates[0]
    # Try contains-type match as fallback
    items = get_wardrobe_items()
    candidates = [
        it for it in items
        if preferred_type.lower() in it["type"].lower()
        and it["id"] not in used_ids
        and (category is None or it.get("category") == category)
    ]
    if colors:
        for c in colors:
            for it in candidates:
                if c in it["color"].lower():
                    return it
    return candidates[0] if candidates else None


def build_outfit(occasion: str, weather: Optional[str], colors: List[str]) -> List[dict]:
    used: set[int] = set()
    result: List[dict] = []

    def add_if_found(t: str, cat: Optional[str] = None):
        it = _pick(t, colors, used, category=cat)
        if it:
            used.add(it["id"])
            result.append(it)

    if occasion in ("formal", "business", "smart casual"):
        add_if_found("Dress Shirt")
        add_if_found("Blazer") if occasion != "business" or weather != "hot" else None
        add_if_found("Chinos")
        # Fallback to Jeans if no chinos
        if not any(x for x in result if x["type"].lower() == "chinos"):
            add_if_found("Jeans")
    elif occasion == "party":
        # Prefer Dress if available, otherwise smart casual
        add_if_found("Dress")
        if not result:
            add_if_found("Dress Shirt")
            add_if_found("Chinos")
    else:
        # casual default
        add_if_found("T-Shirt")
        add_if_found("Jeans")

    # Weather layers
    if weather == "cold":
        add_if_found("Sweater") or add_if_found("Cardigan") or add_if_found("Jacket")
    elif weather == "rain":
        add_if_found("Jacket")

    # Shoes fallback preferring loafers/boots for formal/business, sneakers otherwise
    if occasion in ("formal", "business"):
        add_if_found("Loafers") or add_if_found("Boots") or add_if_found("Sneakers")
    else:
        add_if_found("Sneakers") or add_if_found("Boots")

    # Add accessories if available (watches, belts, bags, etc.)
    # Try to add one accessory item for any outfit
    items = get_wardrobe_items()
    accessory_candidates = [
        it for it in items
        if it.get("category") == "accessories" and it["id"] not in used
    ]
    if accessory_candidates:
        # Prefer color-matching accessories
        if colors:
            for c in colors:
                for acc in accessory_candidates:
                    if c in acc["color"].lower():
                        result.append(acc)
                        break
                if any(it.get("category") == "accessories" for it in result):
                    break
        # If no color match, add first available accessory
        if not any(it.get("category") == "accessories" for it in result):
            result.append(accessory_candidates[0])

    return result


def outfit_score(items: List[dict], occasion: str, weather: Optional[str], colors: List[str]) -> float:
    # Simple heuristic scoring 0..1
    score = 0.0
    types = {it["type"].lower() for it in items}
    cats = {it.get("category") for it in items}
    colors_l = [c.lower() for c in colors]

    # Completeness
    has_top = "top" in cats or any(t in types for t in ["dress shirt", "t-shirt"])
    has_bottom = "bottom" in cats or "dress" in types
    has_shoes = "shoes" in cats
    has_accessories = "accessories" in cats
    if (has_top and has_bottom) or "dress" in types:
        score += 0.4
    if has_shoes:
        score += 0.2
    if has_accessories:
        score += 0.05  # Small bonus for including accessories

    # Occasion match
    if occasion in ("formal", "business") and ("blazer" in types or "dress shirt" in types):
        score += 0.2
    if occasion == "casual" and ("t-shirt" in types or "jeans" in types):
        score += 0.15
    if occasion == "party" and ("dress" in types or "blazer" in types):
        score += 0.15

    # Weather
    if weather == "cold" and any(t in types for t in ["jacket", "sweater", "cardigan"]):
        score += 0.1
    if weather == "hot" and not any(t in types for t in ["jacket", "sweater", "cardigan"]):
        score += 0.05

    # Color preference
    if colors_l and any(any(c in it["color"].lower() for c in colors_l) for it in items):
        score += 0.05

    return min(score, 1.0)


def generate_alternatives(occasion: str, weather: Optional[str], colors: List[str], limit: int) -> List[List[dict]]:
    # Produce simple variations by toggling bottoms and shoes when possible
    base = build_outfit(occasion, weather, colors)
    variations = [base]

    # Try alternative bottom if available
    alt_bottom = _pick("Chinos" if any(x["type"] == "Jeans" for x in base) else "Jeans", colors, set(), category="bottom")
    if alt_bottom:
        v = [it for it in base if it.get("category") != "bottom"] + [alt_bottom]
        variations.append(v)

    # Try alternative shoes
    alt_shoes = _pick("Boots" if any(x["type"] == "Sneakers" for x in base) else "Sneakers", colors, set(), category="shoes")
    if alt_shoes:
        v = [it for it in base if it.get("category") != "shoes"] + [alt_shoes]
        variations.append(v)

    # De-duplicate by item id sets
    seen = set()
    unique: List[List[dict]] = []
    for v in variations:
        key = tuple(sorted(it["id"] for it in v))
        if key not in seen:
            seen.add(key)
            unique.append(v)

    # If fewer than limit, just repeat base variants (could be extended)
    return unique[: max(1, limit)]


@router.post("", response_model=SuggestResponse)
async def suggest_outfit(payload: SuggestRequest) -> SuggestResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    tokens = _text_tokens(text)
    colors = _preferred_colors(tokens)
    occasion = _detect_occasion(tokens)
    weather = _detect_weather(tokens)

    # ML stub
    if payload.strategy == 'ml':
        url = os.environ.get('ML_SUGGEST_URL')
        if not url:
            raise HTTPException(status_code=501, detail="ML strategy not configured; set ML_SUGGEST_URL")
        # In future: call ML service here
        raise HTTPException(status_code=501, detail="ML service integration not yet implemented")

    # Rules engine
    variants = generate_alternatives(occasion, weather, colors, payload.limit)
    scored = [
        (v, outfit_score(v, occasion, weather, colors))
        for v in variants
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    best_items, best_score = scored[0]
    alt_outfits = [Outfit(items=v, score=s, rationale=None) for v, s in scored[1:]]

    notes_parts = [f"Occasion: {occasion}"]
    if weather:
        notes_parts.append(f"Weather: {weather}")
    if colors:
        notes_parts.append("Preferred colors: " + ", ".join(colors))

    return SuggestResponse(
        occasion=occasion,
        colors=colors,
        outfit=Outfit(items=best_items, score=best_score, rationale=None),
        alternatives=alt_outfits,
        notes=" | ".join(notes_parts) if notes_parts else None,
    )
