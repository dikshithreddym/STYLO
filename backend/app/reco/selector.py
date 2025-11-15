from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from .embedding import Embedder
from .color_matcher import infer_palette, palette_score


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _bias_for(label: str) -> float:
    # Encourage more popular intents slightly to avoid ties feeling random
    BIAS = {
        "business": 0.05,
        "formal": 0.05,
        "party": 0.04,
        "casual": 0.03,
        "workout": 0.05,
        "beach": 0.04,
        "hiking": 0.04,
    }
    return BIAS.get(label, 0.02)


# Intent-aware preferences to nudge selection toward sensible items
INTENT_RULES: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "business": {
        "top": {"prefer": ["dress shirt", "button-down", "shirt", "polo"], "avoid": ["t-shirt", "hoodie"]},
        "bottom": {"prefer": ["chino", "dress pant", "suit pant", "trouser", "pant"], "avoid": ["short", "jogger", "fleece"]},
        "footwear": {"prefer": ["loafer", "boot", "dress shoe"], "avoid": ["sneaker", "slide", "sandal"]},
        "layer": {"prefer": ["blazer"], "avoid": ["hoodie"]},
    },
    "formal": {
        "top": {"prefer": ["dress shirt"], "avoid": ["t-shirt", "hoodie"]},
        "bottom": {"prefer": ["suit pant", "dress pant", "trouser"], "avoid": ["jean", "short", "jogger", "fleece"]},
        "footwear": {"prefer": ["dress shoe", "loafer"], "avoid": ["sneaker", "slide", "sandal"]},
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
        "footwear": {"prefer": ["sandal", "slide"], "avoid": ["loafer", "dress shoe", "sneaker"]},
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
        "footwear": {"prefer": ["boot", "hiking"], "avoid": ["loafer", "dress shoe", "slide", "sandal", "sneaker"]},
        "bottom": {"prefer": ["pant"], "avoid": ["short"]},
        "layer": {"prefer": ["jacket"], "avoid": ["blazer"]},
        "top": {"prefer": ["t-shirt"], "avoid": ["dress shirt"]},
    },
}


def _apply_intent_bias(label: str, category: str, name_and_desc: str, base_score: float) -> float:
    rules = INTENT_RULES.get(label, {})
    cr = rules.get(category, {})
    prefer = [t for t in cr.get("prefer", [])]
    avoid = [t for t in cr.get("avoid", [])]
    txt = name_and_desc
    bonus = 0.0
    if prefer and any(t in txt for t in prefer):
        # Stronger bonus for formal/business where correctness matters more
        bonus += 0.18 if label in {"business", "formal"} else 0.12
    if avoid and any(t in txt for t in avoid):
        # Stronger penalty for obvious mismatches in business/formal
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
    label_vec = emb.encode([label])[0]
    cat_best: Dict[str, List[Tuple[Dict, float]]] = {}
    for cat, items in pools.items():
        scored: List[Tuple[Dict, float]] = []
        names = [f"{it.get('name','')} {it.get('description','')}".strip() for it in items]
        vecs = emb.encode(names)
        for it, v in zip(items, vecs):
            s1 = _cosine(qv, v)
            s2 = _cosine(label_vec, v)
            raw = 0.6 * s1 + 0.4 * s2
            score = _apply_intent_bias(label, cat, (f"{it.get('name','')} {it.get('description','')}").lower(), raw)
            scored.append((it, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        cat_best[cat] = scored[:8]

    # Refinement pass: enforce harder constraints for specific intents when possible
    if label in {"business", "formal"}:
        for cat, pairs in list(cat_best.items()):
            rules = INTENT_RULES.get(label, {}).get(cat, {})
            if not rules:
                continue
            prefer = rules.get("prefer", [])
            avoid = rules.get("avoid", [])
            # Reorder: preferred first
            if prefer:
                preferred = [(it, s) for it, s in pairs if any(p in (f"{it.get('name','')} {it.get('description','')}").lower() for p in prefer)]
                if preferred:
                    others = [(it, s) for it, s in pairs if (it, s) not in preferred]
                    pairs = preferred + others
            # Filter out avoided tokens only if we still have at least one non-avoided candidate
            if avoid:
                non_avoided = [(it, s) for it, s in pairs if not any(a in (f"{it.get('name','')} {it.get('description','')}").lower() for a in avoid)]
                if non_avoided:
                    pairs = non_avoided
            cat_best[cat] = pairs[:5]

    # Party at night: demote shorts if alternatives exist
    ql = (query or "").lower()
    if label == "party" and ("night" in ql or "evening" in ql):
        pairs = cat_best.get("bottom", [])
        if pairs:
            non_shorts = [(it, s) for it, s in pairs if "short" not in (f"{it.get('name','')} {it.get('description','')}").lower()]
            if non_shorts:
                cat_best["bottom"] = non_shorts[:5]

    # Beach: prefer sandals/slides, demote sneakers if alternatives exist
    if label == "beach":
        pairs = cat_best.get("footwear", [])
        if pairs:
            sandals = [(it, s) for it, s in pairs if any(k in (f"{it.get('name','')} {it.get('description','')}").lower() for k in ["sandal", "slide"])]
            if sandals:
                others = [(it, s) for it, s in pairs if (it, s) not in sandals]
                pairs = sandals + others
            non_sneakers = [(it, s) for it, s in pairs if "sneaker" not in (f"{it.get('name','')} {it.get('description','')}").lower()]
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
    scored_outfits: List[Tuple[Dict[str, Dict], float]] = []
    for o in outfits:
        palette = infer_palette(o)
        cscore = palette_score(palette)
        item_texts = [f"{v.get('name','')} {v.get('description','')}".strip() for v in o.values()]
        ivecs = emb.encode(item_texts)
        sims = [max(0.0, _cosine(qv, v)) for v in ivecs]
        sem = float(np.mean(sims)) if sims else 0.5
        total = 0.6 * cscore + 0.4 * sem + _bias_for(label)
        scored_outfits.append((o, total))

    scored_outfits.sort(key=lambda x: x[1], reverse=True)
    return [o for o, _ in scored_outfits[:k]]
