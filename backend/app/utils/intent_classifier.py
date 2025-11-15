from typing import Literal, Optional, Tuple, List, Dict

Intent = Literal[
    "outfit",            # Build a full outfit
    "item_search",       # Return matching items (e.g., shoes)
    "blended_outfit_item", # Outfit + show requested items (e.g., outfit with shoes)
    "activity_shoes"     # Show shoes suitable for an activity (e.g., walk)
]


ITEM_KEYWORDS: Dict[str, List[str]] = {
    "shoes": ["shoe", "shoes", "sneaker", "sneakers", "trainers", "boots", "loafers", "slides"],
}

ACTIVITY_KEYWORDS: Dict[str, List[str]] = {
    "walk": ["walk", "walking"],
    "run": ["run", "running", "jog", "jogging"],
    "hike": ["hike", "hiking", "trail"],
    "sport": ["basketball", "soccer", "tennis", "sport", "sports"],
}

OUTFIT_HINTS = [
    "outfit", "wear", "dress", "what should i wear", "suggest", "occasion",
    "party", "wedding", "date", "dinner", "restaurant", "business", "interview", "office",
]


def _contains_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


def classify_intent(text: str) -> Tuple[Intent, Optional[str]]:
    """Classify prompt intent and optionally return the requested item type.

    Returns (intent, item_type)
    - item_type: normalized like "shoes" when applicable
    """
    t = text.lower().strip()

    # Normalize trailing punctuation
    import re
    t = re.sub(r"[?!\.]$", "", t).strip()

    # Extract activity first
    for act, keys in ACTIVITY_KEYWORDS.items():
        if _contains_any(t, keys):
            # If the user mentions only activity without outfit hints, return activity_shoes
            if not _contains_any(t, OUTFIT_HINTS):
                return "activity_shoes", "shoes"
            # If both outfit + activity, let outfit engine run
            return "outfit", None

    # Detect explicit item requests (e.g., shoes)
    requested_item: Optional[str] = None
    for item_type, keys in ITEM_KEYWORDS.items():
        if _contains_any(t, keys):
            requested_item = item_type
            break

    has_outfit_hint = _contains_any(t, OUTFIT_HINTS)

    if requested_item and has_outfit_hint:
        return "blended_outfit_item", requested_item
    if requested_item and not has_outfit_hint:
        return "item_search", requested_item

    # Default to outfit suggestion
    return "outfit", None
