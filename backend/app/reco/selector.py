from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from .embedding import Embedder
from .color_matcher import infer_palette, palette_score


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors (0 = no similarity, 1 = identical)"""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _bias_for(label: str) -> float:
    """
    Intent-specific bias values that slightly favor certain occasions in scoring.
    
    HOW IT AFFECTS OUTFIT SUGGESTIONS:
    - Higher bias values (e.g., 0.05) will make that intent's outfits rank slightly higher
    - Lower bias values (e.g., 0.02-0.03) reduce priority for that intent
    - This helps break ties when multiple outfits have similar scores
    
    TUNING RECOMMENDATIONS:
    - Increase bias (0.06-0.08) if you want an intent to be selected more often
    - Decrease bias (0.01-0.02) if an intent is over-selected
    - Keep values between 0.01-0.10 to avoid overwhelming other scoring factors
    
    Example: If "business" outfits aren't appearing enough, increase "business": 0.05 → 0.07
    """
    BIAS = {
        "business": 0.05,    # Slight boost for business/professional outfits
        "formal": 0.05,      # Slight boost for formal/wedding outfits
        "party": 0.04,       # Moderate boost for party/social outfits
        "casual": 0.03,      # Lower bias (already common, less need to boost)
        "workout": 0.05,     # Boost for athletic/active wear
        "beach": 0.04,       # Moderate boost for beach/vacation outfits
        "hiking": 0.02,      # Lower bias (specific use case)
    }
    return BIAS.get(label, 0.02)


# Intent-aware preferences to nudge selection toward sensible items
#
# HOW IT AFFECTS OUTFIT SUGGESTIONS:
# - "prefer" list: Items matching these keywords get +0.12 to +0.18 score bonus
# - "avoid" list: Items matching these keywords get -0.15 to -0.35 score penalty
# - This ensures business/formal outfits don't include t-shirts/shorts, etc.
#
# TUNING RECOMMENDATIONS:
# - Add new item types to "prefer" if certain items should be prioritized for an intent
# - Add keywords to "avoid" to exclude inappropriate items (e.g., "short" for formal)
# - Use lowercase keywords that match item names/descriptions (substring matching)
#
# Example: To prioritize "henley" shirts for casual occasions:
#   "casual": {"top": {"prefer": ["t-shirt", "polo", "sweater", "henley"], ...}}
#
INTENT_RULES: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "business": {
        "top": {"prefer": ["shirt", "button-down", "shirt", "polo"], "avoid": ["t-shirt", "hoodie", "tee"]},
        "bottom": {"prefer": ["chino", "dress pant", "suit pant", "trouser", "pant"], "avoid": ["short", "shorts", "jogger", "fleece", "sweatpant"]},
        "footwear": {"prefer": ["loafer", "boot", "dress"], "avoid": ["sneaker", "sneakers", "slide", "sandal", "nike", "adidas", "athletic", "running", "trainer"]},
        "layer": {"prefer": ["blazer"], "avoid": ["hoodie"]},
    },
    "formal": {
        "top": {"prefer": ["dress shirt"], "avoid": ["t-shirt", "hoodie", "tee"]},
        "bottom": {"prefer": ["suit pant", "dress pant", "trouser"], "avoid": ["jean", "short", "shorts", "jogger", "fleece", "sweatpant"]},
        "footwear": {"prefer": ["dress", "loafer"], "avoid": ["sneaker", "sneakers", "slide", "sandal", "nike", "adidas", "athletic", "running", "trainer"]},
        "layer": {"prefer": ["blazer"], "avoid": ["hoodie"]},
    },
    "workout": {
        "top": {"prefer": ["t-shirt", "tank"], "avoid": ["dress shirt"]},
        "bottom": {"prefer": ["short"], "avoid": ["jean", "chino", "dress pant"]},
        "footwear": {"prefer": ["sneaker"], "avoid": ["loafer", "boot", "dress shoe"]},
        "layer": {"prefer": ["hoodie"], "avoid": ["blazer"]},
    },
    "beach": {
        "top": {"prefer": ["t-shirt"], "avoid": ["dress shirt"]},
        "bottom": {"prefer": ["short"], "avoid": ["jean", "chino"]},
        "footwear": {"prefer": ["sandal", "slide", "flip"], "avoid": ["loafer", "dress", "sneaker", "nike", "adidas"]},
        "layer": {"avoid": ["blazer", "sweater"]},
    },
    "party": {
        "top": {"prefer": ["dress shirt", "button-down"], "avoid": []},
        "bottom": {"prefer": ["chino", "suit pant", "dark jean"], "avoid": []},
        "footwear": {"prefer": ["loafer", "boot", "sneaker"], "avoid": ["slide", "sandal"]},
        "layer": {"prefer": ["blazer"], "avoid": []},
    },
    "casual": {
        "top": {"prefer": ["t-shirt", "polo", "sweater"], "avoid": []},
        "bottom": {"prefer": ["jean", "chino"], "avoid": []},
        "footwear": {"prefer": ["sneaker", "boot"], "avoid": []},
        "layer": {"prefer": ["hoodie", "jacket", "cardigan"], "avoid": []},
    },
    "hiking": {
        "footwear": {"prefer": ["boot", "hiking"], "avoid": ["loafer", "dress", "slide", "sandal", "sneaker", "nike", "adidas"]},
        "bottom": {"prefer": ["pant"], "avoid": ["short"]},
        "layer": {"prefer": ["jacket"], "avoid": ["blazer"]},
        "top": {"prefer": ["t-shirt"], "avoid": ["dress shirt"]},
    },
}


def _apply_intent_bias(label: str, category: str, name_and_desc: str, base_score: float) -> float:
    """
    Apply intent-based scoring adjustments to individual items.
    
    HOW IT AFFECTS OUTFIT SUGGESTIONS:
    - Preferred items get +0.12 (casual/party) or +0.18 (business/formal) score boost
    - Avoided items get -0.15 (casual) or -0.35 (business/formal) score penalty
    - Stronger penalties for business/formal ensure strict adherence to dress codes
    
    TUNING RECOMMENDATIONS:
    - Increase bonus (0.18 → 0.25) to make preferred items more likely to be selected
    - Increase penalty (0.35 → 0.50) to more strictly exclude avoided items
    - Decrease values if rules are too strict and limiting outfit options
    
    Example: To make business outfits STRICTER about avoiding t-shirts:
    - Change penalty from -0.35 to -0.50 in the "if avoid" block below
    """
    rules = INTENT_RULES.get(label, {})
    cr = rules.get(category, {})
    prefer = [t for t in cr.get("prefer", [])]
    avoid = [t for t in cr.get("avoid", [])]
    txt = name_and_desc
    bonus = 0.0
    if prefer and any(t in txt for t in prefer):
        # Stronger bonus for formal/business where correctness matters more
        # TUNE THIS: Increase 0.18/0.12 to make preferred items rank higher
        bonus += 0.18 if label in {"business", "formal"} else 0.12
    if avoid and any(t in txt for t in avoid):
        # Stronger penalty for obvious mismatches in business/formal
        # TUNE THIS: Increase 0.35/0.15 to more strictly exclude avoided items
        bonus -= 0.35 if label in {"business", "formal"} else 0.15
    return base_score + bonus


def assemble_outfits(query: str, wardrobe: List[Dict], label: str, k: int = 3) -> List[Dict[str, Dict]]:
    """Select up to k outfits using semantic + color harmony scoring.

    wardrobe: list of dicts with at least keys: id, category, name, color (optional)
    returns: list of dicts mapping category -> item
    """
    emb = Embedder.instance()
    qv = emb.encode([query])[0]

    # One-per-category pools
    pools: Dict[str, List[Dict]] = {}
    for it in wardrobe:
        cat = (it.get("category") or "").lower()
        if not cat:
            continue
        pools.setdefault(cat, []).append(it)

    # Score within-category by semantic relevance to query and intent label name
    #
    # HOW IT AFFECTS OUTFIT SUGGESTIONS:
    # - s1 (query similarity): How well item matches user's query (60% weight)
    # - s2 (intent similarity): How well item matches the occasion type (40% weight)
    # - Higher s1 weight = more query-driven results (user's specific words matter more)
    # - Higher s2 weight = more context-appropriate results (occasion matters more)
    #
    # TUNING RECOMMENDATIONS:
    # - Increase 0.6 (query) → 0.7 if users want more literal query matching
    # - Increase 0.4 (intent) → 0.5 if outfits should be more occasion-appropriate
    # - Balance: 0.6/0.4 is good for most cases (balances specificity + context)
    #
    # Example: For "blue shirt for business meeting":
    #   - Higher query weight: Prefers items with "blue" in description
    #   - Higher intent weight: Prefers items matching "business" style regardless of color
    #
    label_vec = emb.encode([label])[0]
    cat_best: Dict[str, List[Tuple[Dict, float]]] = {}
    for cat, items in pools.items():
        scored: List[Tuple[Dict, float]] = []
        names = [f"{it.get('name','')} {it.get('description','')}".strip() for it in items]
        vecs = emb.encode(names)
        for it, v in zip(items, vecs):
            s1 = _cosine(qv, v)  # Query similarity (TUNE: adjust weight below)
            s2 = _cosine(label_vec, v)  # Intent similarity (TUNE: adjust weight below)
            raw = 0.6 * s1 + 0.4 * s2  # TUNE THIS LINE: Change 0.6/0.4 to adjust query vs intent importance
            score = _apply_intent_bias(label, cat, (f"{it.get('name','')} {it.get('description','')}").lower(), raw)
            scored.append((it, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        cat_best[cat] = scored[:8]  # TUNE: Increase 8 → 12 for more diversity, decrease → 5 for faster performance

    # Hard filter for business/formal: block tees, shorts, hoodies, sneakers, joggers, fleece, sweatpants, athletic
    if label in {"business", "formal"}:
        HARD_AVOID = ["t-shirt", "tee", "short", "shorts", "hoodie", "sneaker", "sneakers", "athletic", "jogger", "fleece", "sweatpant", "nike", "adidas", "trainer", "running"]
        HARD_PREFER = ["dress shirt", "button-down", "shirt", "polo", "chino", "dress pant", "suit pant", "trouser", "pant", "blazer", "loafer", "boot", "dress shoe"]
        for cat, pairs in list(cat_best.items()):
            # Remove all avoided items
            filtered = [(it, s) for it, s in pairs if not any(a in (f"{it.get('name','')} {it.get('description','')}").lower() for a in HARD_AVOID)]
            # Prefer preferred items
            preferred = [(it, s) for it, s in filtered if any(p in (f"{it.get('name','')} {it.get('description','')}").lower() for p in HARD_PREFER)]
            if preferred:
                pairs = preferred + [x for x in filtered if x not in preferred]
            elif filtered:
                pairs = filtered
            else:
                # If nothing left, fallback to original pool
                pairs = pairs
            # For outerwear, force blazer first if present
            if cat == "layer":
                blazers = [(it, s) for it, s in pairs if "blazer" in (f"{it.get('name','')} {it.get('description','')}").lower()]
                if blazers:
                    others = [(it, s) for it, s in pairs if (it, s) not in blazers]
                    pairs = blazers + others
            cat_best[cat] = pairs[:5]

    # Party at night: demote shorts and hoodies if alternatives exist
    ql = (query or "").lower()
    if label == "party" and ("night" in ql or "evening" in ql):
        pairs = cat_best.get("bottom", [])
        if pairs:
            non_shorts = [(it, s) for it, s in pairs if "short" not in (f"{it.get('name','')} {it.get('description','')}").lower()]
            if non_shorts:
                cat_best["bottom"] = non_shorts[:5]
        lpairs = cat_best.get("layer", [])
        if lpairs:
            non_hoodie = [(it, s) for it, s in lpairs if "hoodie" not in (f"{it.get('name','')} {it.get('description','')}").lower()]
            if non_hoodie:
                cat_best["layer"] = non_hoodie[:5]

    # Beach: prefer sandals/slides, demote brand sneakers if alternatives exist
    if label == "beach":
        pairs = cat_best.get("footwear", [])
        if pairs:
            sandals = [(it, s) for it, s in pairs if any(k in (f"{it.get('name','')} {it.get('description','')}").lower() for k in ["sandal", "slide"])]
            if sandals:
                others = [(it, s) for it, s in pairs if (it, s) not in sandals]
                pairs = sandals + others
            non_sneakers = [(it, s) for it, s in pairs if all(k not in (f"{it.get('name','')} {it.get('description','')}").lower() for k in ["sneaker", "nike", "adidas"])]
            if non_sneakers:
                pairs = non_sneakers
            cat_best["footwear"] = pairs[:5]

    # Hiking: if cool/cold mentioned, avoid shorts; always prefer boots
    if label == "hiking":
        if any(k in ql for k in ["cool", "cold", "chilly"]):
            pairs = cat_best.get("bottom", [])
            if pairs:
                non_shorts = [(it, s) for it, s in pairs if "short" not in (f"{it.get('name','')} {it.get('description','')}").lower()]
                if non_shorts:
                    cat_best["bottom"] = non_shorts[:5]
        pairs = cat_best.get("footwear", [])
        if pairs:
            boots = [(it, s) for it, s in pairs if any(k in (f"{it.get('name','')} {it.get('description','')}").lower() for k in ["boot", "hiking"])]
            if boots:
                others = [(it, s) for it, s in pairs if (it, s) not in boots]
                cat_best["footwear"] = (boots + others)[:5]

    # Required categories
    required = ["top", "bottom", "footwear"]
    for r in required:
        if r not in cat_best:
            return []

    outfits: List[Dict[str, Dict]] = []
    # Build up to k outfits using greedy selection
    # TUNE THIS: Increase range(10) → range(15) for more outfit variety, decrease → range(5) for faster performance
    for i in range(10):  # limit combinations
        candidate: Dict[str, Dict] = {}
        for cat in ["top", "bottom", "footwear"]:
            pool = cat_best.get(cat, [])
            if not pool:
                break
            pick = pool[min(i, len(pool) - 1)][0]
            candidate[cat] = pick

        # Optional layer/accessories if available (DB uses 'layer')
        for opt in ["layer", "accessories"]:
            pool = cat_best.get(opt, [])
            if pool:
                # For layer, pick first preferred by intent if available
                if opt == "layer" and label in INTENT_RULES and INTENT_RULES[label].get("layer", {}).get("prefer"):
                    pref = INTENT_RULES[label]["layer"]["prefer"]
                    chosen = None
                    for it, _ in pool:
                        t = (f"{it.get('name','')} {it.get('description','')}").lower()
                        if any(p in t for p in pref):
                            chosen = it
                            break
                    candidate[opt] = chosen or pool[0][0]
                else:
                    candidate[opt] = pool[0][0]

        if len(candidate) >= 3:
            outfits.append(candidate)
        if len(outfits) >= k:
            break

    # Score outfits by harmony + per-item semantic avg + intent bias
    #
    # HOW IT AFFECTS OUTFIT SUGGESTIONS:
    # - cscore (color harmony): 0.4 weight = how well colors work together (CIEDE2000 color science)
    # - sem (semantic match): 0.6 weight = how well all items match the query/intent
    # - bias: Small intent-specific boost (0.02-0.05)
    #
    # TUNING RECOMMENDATIONS:
    # - Increase color weight (0.4 → 0.5) if color coordination is more important
    # - Increase semantic weight (0.6 → 0.7) if query matching is more important
    # - Current 40/60 split prioritizes semantic relevance over color harmony
    #
    # Example scenarios:
    #   - Color-focused: Change to 0.6 * cscore + 0.4 * sem (prioritize matching colors)
    #   - Query-focused: Keep 0.4 * cscore + 0.6 * sem (prioritize matching user's words)
    #
    scored_outfits: List[Tuple[Dict[str, Dict], float]] = []
    for o in outfits:
        palette = infer_palette(o)
        cscore = palette_score(palette)  # Color harmony score (0-1, higher = better color match)
        item_texts = [f"{v.get('name','')} {v.get('description','')}".strip() for v in o.values()]
        ivecs = emb.encode(item_texts)
        sims = [max(0.0, _cosine(qv, v)) for v in ivecs]
        sem = float(np.mean(sims)) if sims else 0.5  # Average semantic similarity (0-1)
        # TUNE THIS LINE: Adjust color vs semantic weights to change outfit selection priority
        total = 0.4 * cscore + 0.6 * sem + _bias_for(label)
        scored_outfits.append((o, total))

    scored_outfits.sort(key=lambda x: x[1], reverse=True)
    # Limit to max 3 variations for performance
    max_outfits = min(k, 3)
    return [o for o, _ in scored_outfits[:max_outfits]]
