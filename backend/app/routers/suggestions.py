from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from app.schemas import WardrobeItem, SuggestRequest, SuggestResponse, Outfit
from app.database import get_db
from app import models
import os
from sqlalchemy.exc import ProgrammingError

router = APIRouter()

# Get wardrobe items from database
def get_wardrobe_items(db: Session) -> List[dict]:
    try:
        items = db.query(models.WardrobeItem).all()
    except ProgrammingError as exc:
        # Auto-heal missing column by running migration once, then retry
        msg = str(exc)
        if "image_description" in msg and "UndefinedColumn" in msg:
            try:
                from migrate_add_image_description import migrate  # type: ignore
                migrate()
                items = db.query(models.WardrobeItem).all()
            except Exception:
                # Re-raise original if healing fails
                raise
        else:
            raise
    return [item.to_dict() for item in items]

COLOR_WORDS = {
    # Basic colors
    "black", "white", "navy", "blue", "green", "olive", "grey", "gray",
    "beige", "khaki", "burgundy", "charcoal", "dark", "light", "brown",
    "red", "pink", "yellow", "orange", "purple", "silver", "gold",
    # Denim variations
    "denim", "light", "medium", "dark",
    # Patterns and special colors
    "camo", "camouflage", "tan", "cream", "ivory",
    "maroon", "teal", "turquoise", "lavender", "mint", "peach", "coral",
    # Shades
    "pale", "bright", "deep", "pastel", "neon", "faded"
}

# Color synonyms and variations for better matching
COLOR_SYNONYMS = {
    "navy": ["navy blue", "dark blue"],
    "gray": ["grey", "charcoal"],
    "beige": ["tan", "cream", "khaki"],
    "brown": ["chocolate", "coffee", "tan"],
    "white": ["ivory", "cream", "off-white"],
    "black": ["jet black", "ebony"],
    "camo": ["camouflage", "brown camo", "green camo", "desert camo"],
    "denim": ["jean", "jeans blue", "medium light"],
}

OCCASION_KEYWORDS = {
    "formal": {"formal", "wedding", "ceremony", "black tie", "reception"},
    "business": {"business", "office", "interview", "meeting", "work"},
    "smart casual": {"smart", "smart casual", "semi-formal"},
    "party": {"party", "night out", "club", "birthday", "celebration"},
    "casual": {"casual", "hangout", "weekend", "everyday", "relaxed", "any"},
}

WEATHER_KEYWORDS = {
    "cold": {"cold", "winter", "chilly", "freezing"},
    "hot": {"hot", "summer", "warm", "heat"},
    "rain": {"rain", "rainy", "wet"},
}

# Item type keywords to help understand queries
ITEM_TYPE_KEYWORDS = {
    "ring": {"ring", "rings"},
    "watch": {"watch", "watches"},
    "belt": {"belt", "belts"},
    "bag": {"bag", "bags", "handbag", "purse"},
    "scarf": {"scarf", "scarves"},
    "sunglasses": {"sunglasses", "shades", "glasses"},
}


def _text_tokens(text: str) -> List[str]:
    """Extract meaningful tokens from text, filtering out stopwords"""
    import re
    # Common English stopwords that don't help with clothing descriptions
    stopwords = {
        'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'and', 'or',
        'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must',
        'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'its', 'our', 'their', 'this', 'that', 'these', 'those'
    }
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    # Filter out stopwords and very short tokens (less than 3 chars)
    return [t for t in tokens if t not in stopwords and len(t) >= 3]


def _detect_query_type(text: str) -> str:
    """Detect if user is asking a question or requesting outfit suggestions"""
    text_lower = text.lower()
    
    # Question patterns
    question_words = ["are there", "do i have", "what", "which", "how many", "show me", "list", "find"]
    if any(word in text_lower for word in question_words):
        return "query"
    
    # Item search patterns
    if any(word in text_lower for word in ["any", "have a", "have any"]):
        return "query"
    
    # Outfit suggestion patterns
    suggestion_words = ["suggest", "outfit", "wear", "dress", "occasion", "party", "meeting", "casual", "formal"]
    if any(word in text_lower for word in suggestion_words):
        return "suggestion"
    
    # Default to query if it's a short question-like text
    if len(text.split()) < 8 and ("?" in text or any(word in text_lower for word in ["ring", "belt", "watch", "scarf"])):
        return "query"
    
    return "suggestion"


def _search_wardrobe(text: str, db: Session) -> dict:
    """Search wardrobe based on user query"""
    tokens = _text_tokens(text)
    items = get_wardrobe_items(db)
    
    # Extract item types and colors from query
    search_types = []
    search_colors = _preferred_colors(tokens)  # Use the improved color detection
    
    # Common item types
    item_keywords = {
        "ring": ["ring", "rings"],
        "watch": ["watch", "watches"],
        "belt": ["belt", "belts"],
        "bag": ["bag", "bags", "handbag", "purse"],
        "scarf": ["scarf", "scarves"],
        "sunglasses": ["sunglasses", "shades", "glasses"],
        "shirt": ["shirt", "shirts", "tshirt", "t-shirt"],
        "jeans": ["jeans", "jean"],
        "pants": ["pants", "pant", "chinos"],
        "dress": ["dress", "dresses"],
        "shoes": ["shoes", "shoe", "sneakers", "boots", "loafers"],
        "jacket": ["jacket", "jackets", "blazer"],
    }
    
    for item_type, keywords in item_keywords.items():
        if any(kw in tokens for kw in keywords):
            search_types.append(item_type)
    
    # Filter items using smart color matching
    matching_items = []
    for item in items:
        type_match = not search_types or any(st in item["type"].lower() for st in search_types)
        color_match = _color_matches(item["color"], search_colors)
        
        if type_match and color_match:
            matching_items.append(item)
    
    return {
        "found": len(matching_items) > 0,
        "count": len(matching_items),
        "items": matching_items,
        "search_types": search_types,
        "search_colors": search_colors
    }


def _preferred_colors(tokens: List[str]) -> List[str]:
    # Collect color words that appear in text
    found = []
    for t in tokens:
        if t in COLOR_WORDS and t not in found:
            found.append(t)
    
    # Also check for color synonyms in the original text
    # This helps match multi-word colors like "navy blue"
    text = " ".join(tokens)
    for base_color, variations in COLOR_SYNONYMS.items():
        for variation in variations:
            if variation in text and base_color not in found:
                found.append(base_color)
                break
    
    return found


def _color_matches(item_color: str, preferred_colors: List[str]) -> bool:
    """Check if item color matches any of the preferred colors"""
    if not preferred_colors:
        return True
    
    item_color_lower = item_color.lower()
    
    for pref_color in preferred_colors:
        # Direct substring match
        if pref_color in item_color_lower:
            return True
        
        # Check synonyms (e.g., "gray" matches "grey", "charcoal")
        if pref_color in COLOR_SYNONYMS:
            for synonym in COLOR_SYNONYMS[pref_color]:
                if synonym in item_color_lower:
                    return True
        
        # Reverse check: if item color contains synonym that maps to preferred color
        for base_color, synonyms in COLOR_SYNONYMS.items():
            if base_color == pref_color:
                for synonym in synonyms:
                    if synonym in item_color_lower:
                        return True
    
    return False


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


def _pick(preferred_type: str, colors: List[str], used_ids: set[int], category: Optional[str], db: Session, query_tokens: List[str] = []) -> Optional[dict]:
    # Try exact type match first, prefer preferred colors
    items = get_wardrobe_items(db)
    candidates = [
        it for it in items
        if it["type"].lower() == preferred_type.lower()
        and it["id"] not in used_ids
        and (category is None or it.get("category") == category)
    ]
    
    # Use smart color matching instead of simple substring
    if colors and candidates:
        color_matched = [it for it in candidates if _color_matches(it["color"], colors)]
        if color_matched:
            return color_matched[0]
    
    if candidates:
        return candidates[0]
    
    # Try contains-type match as fallback
    candidates = [
        it for it in items
        if preferred_type.lower() in it["type"].lower()
        and it["id"] not in used_ids
        and (category is None or it.get("category") == category)
    ]
    
    # Again use smart color matching
    if colors and candidates:
        color_matched = [it for it in candidates if _color_matches(it["color"], colors)]
        if color_matched:
            return color_matched[0]
            
    # NEW: Search in image description
    if query_tokens:
        desc_candidates = [
            it for it in items
            if it["id"] not in used_ids
            and (category is None or it.get("category") == category)
            and it.get("image_description")
            and any(token in it["image_description"].lower() for token in query_tokens)
        ]
        if desc_candidates:
            return desc_candidates[0]
    
    return candidates[0] if candidates else None


def build_outfit(occasion: str, weather: Optional[str], colors: List[str], db: Session, query_tokens: List[str] = []) -> List[dict]:
    used: set[int] = set()
    result: List[dict] = []

    def add_if_found(t: str, cat: Optional[str] = None):
        it = _pick(t, colors, used, cat, db, query_tokens)
        if it:
            used.add(it["id"])
            result.append(it)
            return True
        return False

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
        # casual default - try T-Shirt first, then any top
        if not add_if_found("T-Shirt"):
            # Try any top if no T-Shirt found
            items = get_wardrobe_items(db)
            top_items = [it for it in items if it.get("category") == "top" and it["id"] not in used]
            if top_items:
                if colors:
                    color_matched = [it for it in top_items if _color_matches(it["color"], colors)]
                    if color_matched:
                        result.append(color_matched[0])
                        used.add(color_matched[0]["id"])
                    else:
                        result.append(top_items[0])
                        used.add(top_items[0]["id"])
                else:
                    result.append(top_items[0])
                    used.add(top_items[0]["id"])
        
        # Add bottoms
        if not add_if_found("Jeans"):
            # Try any bottom if no Jeans found
            items = get_wardrobe_items(db)
            bottom_items = [it for it in items if it.get("category") == "bottom" and it["id"] not in used]
            if bottom_items:
                if colors:
                    color_matched = [it for it in bottom_items if _color_matches(it["color"], colors)]
                    if color_matched:
                        result.append(color_matched[0])
                        used.add(color_matched[0]["id"])
                    else:
                        result.append(bottom_items[0])
                        used.add(bottom_items[0]["id"])
                else:
                    result.append(bottom_items[0])
                    used.add(bottom_items[0]["id"])
        
        # ALWAYS try to add shoes for casual outfits
        if not add_if_found("Sneakers"):
            add_if_found("Boots") or add_if_found("Loafers")

    # Weather layers - CRITICAL: Prioritize for cold/rain weather
    if weather == "cold":
        # Try multiple layer types for cold weather
        layer_added = (
            add_if_found("Hoodie", "layer") or 
            add_if_found("Jacket", "layer") or 
            add_if_found("Sweater", "layer") or 
            add_if_found("Cardigan", "layer")
        )
        # If still no layer, try without category filter
        if not layer_added:
            items = get_wardrobe_items(db)
            layer_items = [
                it for it in items 
                if it["id"] not in used and (
                    it.get("category") == "layer" or 
                    any(word in it["type"].lower() for word in ["hoodie", "jacket", "sweater", "cardigan"])
                )
            ]
            if layer_items:
                if colors:
                    color_matched = [it for it in layer_items if _color_matches(it["color"], colors)]
                    if color_matched:
                        result.append(color_matched[0])
                        used.add(color_matched[0]["id"])
                    else:
                        result.append(layer_items[0])
                        used.add(layer_items[0]["id"])
                else:
                    result.append(layer_items[0])
                    used.add(layer_items[0]["id"])
    elif weather == "rain":
        add_if_found("Jacket") or add_if_found("Hoodie")

    # Shoes fallback preferring loafers/boots for formal/business, sneakers otherwise
    if occasion in ("formal", "business"):
        add_if_found("Loafers") or add_if_found("Boots") or add_if_found("Sneakers")
    else:
        add_if_found("Sneakers") or add_if_found("Boots")

    # Add accessories if available (watches, belts, bags, etc.)
    # Try to add one accessory item for any outfit
    items = get_wardrobe_items(db)
    accessory_candidates = [
        it for it in items
        if it.get("category") == "accessories" and it["id"] not in used
    ]
    if accessory_candidates:
        # Use smart color-matching for accessories
        if colors:
            color_matched = [acc for acc in accessory_candidates if _color_matches(acc["color"], colors)]
            if color_matched:
                result.append(color_matched[0])
                return result
        
        # If no color match, add first available accessory
        if not any(it.get("category") == "accessories" for it in result):
            result.append(accessory_candidates[0])

    return result


def generate_outfit_rationale(items: List[dict], occasion: str, weather: Optional[str], colors: List[str], score: float, query_tokens: List[str] = []) -> str:
    """Generate a detailed explanation for why this outfit was suggested"""
    parts = []
    
    # Occasion reasoning
    if occasion == "casual":
        parts.append("This is a relaxed, comfortable outfit perfect for casual settings.")
    elif occasion == "formal":
        parts.append("This sophisticated ensemble is ideal for formal occasions.")
    elif occasion == "business":
        parts.append("This professional outfit works great for business settings.")
    elif occasion == "party":
        parts.append("This stylish combination is perfect for social gatherings.")
    elif occasion == "smart casual":
        parts.append("This polished yet comfortable outfit strikes the right balance.")
    
    # Weather considerations
    if weather == "cold":
        layers = [it for it in items if it.get("category") == "layer" or 
                 any(word in it["type"].lower() for word in ["hoodie", "jacket", "sweater", "cardigan"])]
        if layers:
            layer_names = ", ".join(it["type"] for it in layers)
            parts.append(f"For the cold weather, I've included {layer_names} to keep you warm.")
        else:
            parts.append("Note: Consider adding a jacket or sweater for cold weather.")
    elif weather == "hot":
        parts.append("The lightweight pieces will keep you cool in warm weather.")
    elif weather == "rain":
        if any("jacket" in it["type"].lower() or "hoodie" in it["type"].lower() for it in items):
            parts.append("The outerwear will provide protection from the rain.")
    
    # Color matching
    if colors:
        color_matched_items = [it for it in items if _color_matches(it["color"], colors)]
        if color_matched_items:
            matched_pieces = ", ".join(it["type"] for it in color_matched_items)
            color_list = " and ".join(colors)
            parts.append(f"I matched your {color_list} preference with the {matched_pieces}.")
            
    # NEW: Description-based reasoning
    if query_tokens:
        for item in items:
            if item.get("image_description"):
                desc_lower = item["image_description"].lower()
                matched_tokens = [token for token in query_tokens if token in desc_lower]
                if matched_tokens:
                    parts.append(f"The {item['type']} was chosen as its description mentions '{', '.join(matched_tokens)}'.")

    # Outfit composition
    categories = {it.get("category") for it in items}
    has_accessories = "accessories" in categories
    has_layer = "layer" in categories
    
    if has_accessories:
        accessories = [it["type"] for it in items if it.get("category") == "accessories"]
        parts.append(f"Added {', '.join(accessories)} to complete the look.")
    
    # Confidence note
    if score >= 0.8:
        parts.append("This is a highly compatible outfit based on your wardrobe!")
    elif score >= 0.6:
        parts.append("This outfit works well with what you have available.")
    else:
        parts.append("This is the best match from your current wardrobe items.")
    
    return " ".join(parts)


def outfit_score(items: List[dict], occasion: str, weather: Optional[str], colors: List[str], query_tokens: List[str] = []) -> float:
    # Simple heuristic scoring 0..1
    score = 0.0
    types = {it["type"].lower() for it in items}
    cats = {it.get("category") for it in items}

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

    # Weather - Enhanced scoring for layers
    if weather == "cold" and any(t in types for t in ["jacket", "sweater", "cardigan", "hoodie"]):
        score += 0.15  # Increased from 0.1
    if weather == "hot" and not any(t in types for t in ["jacket", "sweater", "cardigan", "hoodie"]):
        score += 0.05

    # Color preference - use smart color matching
    if colors and any(_color_matches(it["color"], colors) for it in items):
        score += 0.05
        
    # NEW: Description match bonus
    if query_tokens:
        for item in items:
            if item.get("image_description"):
                desc_lower = item["image_description"].lower()
                if any(token in desc_lower for token in query_tokens):
                    score += 0.02 # Small bonus for each item that matches description
    
    return min(score, 1.0)


def generate_alternatives(occasion: str, weather: Optional[str], colors: List[str], limit: int, db: Session, query_tokens: List[str] = []) -> List[List[dict]]:
    # Produce simple variations by toggling bottoms, shoes, and layers
    base = build_outfit(occasion, weather, colors, db, query_tokens)
    variations = [base]
    
    base_ids = {it["id"] for it in base}

    # Try alternative bottom if available
    current_bottom = next((x for x in base if x.get("category") == "bottom"), None)
    if current_bottom:
        alt_bottom_type = "Chinos" if "Jeans" in current_bottom["type"] else "Jeans"
        alt_bottom = _pick(alt_bottom_type, colors, base_ids, "bottom", db, query_tokens)
        if alt_bottom and alt_bottom["id"] not in base_ids:
            v = [it for it in base if it.get("category") != "bottom"] + [alt_bottom]
            variations.append(v)

    # Try alternative shoes
    current_shoes = next((x for x in base if x.get("category") == "shoes"), None)
    if current_shoes:
        alt_shoes_type = "Boots" if "Sneakers" in current_shoes["type"] else "Sneakers"
        alt_shoes = _pick(alt_shoes_type, colors, base_ids, "shoes", db, query_tokens)
        if alt_shoes and alt_shoes["id"] not in base_ids:
            v = [it for it in base if it.get("category") != "shoes"] + [alt_shoes]
            variations.append(v)
    
    # Try with/without layer for more variety
    current_layer = next((x for x in base if x.get("category") == "layer"), None)
    if current_layer:
        # Variant without layer
        v = [it for it in base if it.get("category") != "layer"]
        if len(v) > 0:
            variations.append(v)
    else:
        # Try to add a layer
        alt_layer = _pick("Hoodie", colors, base_ids, "layer", db, query_tokens)
        if alt_layer and alt_layer["id"] not in base_ids:
            variations.append(base + [alt_layer])

    # De-duplicate by item id sets
    seen = set()
    unique: List[List[dict]] = []
    for v in variations:
        key = tuple(sorted(it["id"] for it in v))
        if key not in seen and len(v) > 0:
            seen.add(key)
            unique.append(v)

    return unique[: max(1, limit)]


@router.post("", response_model=SuggestResponse)
async def suggest_outfit(payload: SuggestRequest, db: Session = Depends(get_db)) -> SuggestResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    # Detect if this is a query or outfit suggestion request
    query_type = _detect_query_type(text)
    
    # Check if wardrobe has items
    available_items = get_wardrobe_items(db)
    if len(available_items) == 0:
        raise HTTPException(
            status_code=400, 
            detail="Your wardrobe is empty. Please add some clothing items first."
        )
    
    # Handle wardrobe queries (searching for items)
    if query_type == "query":
        search_result = _search_wardrobe(text, db)
        
        if search_result["found"]:
            # Return the found items as an "outfit"
            items = search_result["items"]
            search_desc = []
            if search_result["search_types"]:
                search_desc.append(f"type: {', '.join(search_result['search_types'])}")
            if search_result["search_colors"]:
                search_desc.append(f"color: {', '.join(search_result['search_colors'])}")
            
            notes = f"Found {search_result['count']} item(s) matching your query"
            if search_desc:
                notes += f" ({'; '.join(search_desc)})"
            
            return SuggestResponse(
                occasion="query",
                colors=search_result["search_colors"],
                outfit=Outfit(
                    items=items,
                    score=1.0,
                    rationale=f"Search results: {search_result['count']} matching item(s)"
                ),
                alternatives=[],
                notes=notes
            )
        else:
            # No items found
            search_terms = []
            if search_result["search_types"]:
                search_terms.extend(search_result["search_types"])
            if search_result["search_colors"]:
                search_terms.extend(search_result["search_colors"])
            
            search_desc = " ".join(search_terms) if search_terms else "your query"
            available_types = ', '.join(set(item['type'] for item in available_items))
            
            raise HTTPException(
                status_code=404,
                detail=f"No items found matching '{search_desc}'. Your wardrobe contains: {available_types}."
            )
    
    # Handle outfit suggestion requests
    # Check if wardrobe has basic items needed for an outfit
    has_top_or_dress = any(
        item.get("category") in ["top", "one-piece"] or 
        any(word in item["type"].lower() for word in ["shirt", "dress", "top", "sweater", "jacket"])
        for item in available_items
    )
    has_bottom = any(
        item.get("category") == "bottom" or 
        any(word in item["type"].lower() for word in ["jeans", "pants", "chinos", "skirt"])
        for item in available_items
    )
    
    if not has_top_or_dress and not has_bottom:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough clothing items to create an outfit. You have {len(available_items)} item(s): {', '.join(item['type'] for item in available_items)}. Please add tops, bottoms, or complete outfits."
        )

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
    variants = generate_alternatives(occasion, weather, colors, payload.limit, db, tokens)
    
    # If no valid outfits generated, provide helpful message
    if not variants or all(len(v) == 0 for v in variants):
        available_types = ', '.join(set(item['type'] for item in available_items))
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create an outfit with available items. Your wardrobe contains: {available_types}. Try adding more clothing pieces like tops, bottoms, or shoes."
        )
    
    scored = [
        (v, outfit_score(v, occasion, weather, colors, tokens))
        for v in variants if len(v) > 0
    ]
    
    if not scored:
        raise HTTPException(
            status_code=400,
            detail="Unable to generate outfit suggestions. Please add more clothing items to your wardrobe."
        )
    
    scored.sort(key=lambda x: x[1], reverse=True)
    best_items, best_score = scored[0]
    
    # Generate intelligent rationale for the best outfit
    best_rationale = generate_outfit_rationale(best_items, occasion, weather, colors, best_score, tokens)
    
    # Generate rationales for alternatives too
    alt_outfits = [
        Outfit(
            items=v, 
            score=s, 
            rationale=generate_outfit_rationale(v, occasion, weather, colors, s, tokens)
        ) 
        for v, s in scored[1:]
    ]

    notes_parts = [f"Occasion: {occasion}"]
    if weather:
        notes_parts.append(f"Weather: {weather}")
    if colors:
        notes_parts.append("Preferred colors: " + ", ".join(colors))

    return SuggestResponse(
        occasion=occasion,
        colors=colors,
        outfit=Outfit(items=best_items, score=best_score, rationale=best_rationale),
        alternatives=alt_outfits,
        notes=" | ".join(notes_parts) if notes_parts else None,
    )
