#!/usr/bin/env python3
"""Fix duplicate category issues in outfit generation"""

with open('app/routers/suggestions.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Update _detect_activity to not trigger on "running errands"
old_activity = '''def _detect_activity(tokens: List[str]) -> Optional[str]:
    """Detect activity context (e.g., walk, run, hike) to tune outfit."""
    activity_map = {
        "walk": {"walk", "walking"},
        "run": {"run", "running", "jog", "jogging"},
        "hike": {"hike", "hiking", "trail"},
        "workout": {"workout", "gym", "exercise", "training"},
        "sport": {"sport", "sports", "soccer", "basketball", "tennis"},
    }
    ts = set(tokens)
    for name, keys in activity_map.items():
        if ts & keys:
            return name
    return None'''

new_activity = '''def _detect_activity(tokens: List[str]) -> Optional[str]:
    """Detect activity context (e.g., walk, run, hike) to tune outfit."""
    text_lower = " ".join(tokens)
    
    # Exclude phrases like "running errands"
    if "running" in text_lower and "errand" in text_lower:
        return None
    
    activity_map = {
        "walk": {"walk", "walking"},
        "run": {"run", "running", "jog", "jogging"},
        "hike": {"hike", "hiking", "trail"},
        "workout": {"workout", "gym", "exercise", "training"},
        "sport": {"sport", "sports", "soccer", "basketball", "tennis"},
    }
    ts = set(tokens)
    for name, keys in activity_map.items():
        if ts & keys:
            return name
    return None'''

content = content.replace(old_activity, new_activity)

# Fix 2: Add category deduplication after build_outfit
# Find the generate_alternatives function and add dedup logic
old_gen = '''def generate_alternatives(occasion: str, weather: Optional[str], colors: List[str], limit: int, db: Session, query_tokens: List[str] = []) -> List[List[dict]]:
    """Generate multiple distinct outfits by building different combinations"""
    all_items = get_wardrobe_items(db)
    variations = []
    used_globally = set()  # Track items used across all outfits
    
    # Generate multiple base outfits with different items
    for outfit_num in range(limit):
        # Build outfit avoiding items used in previous outfits
        base = build_outfit(occasion, weather, colors, db, query_tokens)
        
        # Filter out items already used in previous outfits
        base_filtered = [it for it in base if it["id"] not in used_globally]'''

new_gen = '''def generate_alternatives(occasion: str, weather: Optional[str], colors: List[str], limit: int, db: Session, query_tokens: List[str] = []) -> List[List[dict]]:
    """Generate multiple distinct outfits by building different combinations"""
    all_items = get_wardrobe_items(db)
    variations = []
    used_globally = set()  # Track items used across all outfits
    
    def deduplicate_categories(outfit: List[dict]) -> List[dict]:
        """Remove duplicate categories, keeping the first occurrence"""
        seen_categories = set()
        deduped = []
        for item in outfit:
            cat = item.get("category")
            if cat not in seen_categories:
                seen_categories.add(cat)
                deduped.append(item)
        return deduped
    
    # Generate multiple base outfits with different items
    for outfit_num in range(limit):
        # Build outfit avoiding items used in previous outfits
        base = build_outfit(occasion, weather, colors, db, query_tokens)
        
        # Deduplicate categories (only one item per category)
        base = deduplicate_categories(base)
        
        # Filter out items already used in previous outfits
        base_filtered = [it for it in base if it["id"] not in used_globally]'''

content = content.replace(old_gen, new_gen)

with open('app/routers/suggestions.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed duplicate issues!")
