from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from .embedding import Embedder


LABELS = [
    "business", "formal", "party", "casual", "workout", "beach", "hiking",
]

# Short seed descriptions per label for zero-shot matching
SEEDS = {
    "business": [
        "office meeting outfit, smart shirt and trousers",
        "professional attire, blazer and chinos, leather shoes",
    ],
    "formal": [
        "black tie event, tuxedo, dress shirt, polished shoes",
        "wedding attire, suit and tie, dress shoes",
    ],
    "party": [
        "night out outfit, stylish blazer or shirt, chinos or dark jeans",
        "date night look, elegant top and tailored pants",
    ],
    "casual": [
        "everyday wear, t-shirt and jeans or chinos",
        "relaxed outfit for brunch or errands",
    ],
    "workout": [
        "gym clothing, shorts, breathable top, athletic shoes",
        "running or training gear, performance fabrics",
    ],
    "beach": [
        "hot weather, shorts, light shirt, sandals or slides",
        "seaside day, airy outfit, sun protection",
    ],
    "hiking": [
        "outdoor trail, sturdy shoes, breathable layers",
        "active wear for walking long distances",
    ],
}


@dataclass
class Intent:
    label: str
    scores: List[Tuple[str, float]]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def classify_intent_zero_shot(text: str) -> Intent:
    """Zero-shot classify text into one of LABELS using seed descriptions.

    Returns best label and per-label scores for transparency.
    """
    emb = Embedder.instance()
    # Build seed bank
    seed_texts: List[str] = []
    seed_index: List[Tuple[str, int]] = []
    for label in LABELS:
        for s in SEEDS[label]:
            seed_index.append((label, len(seed_texts)))
            seed_texts.append(s)

    seed_vecs = emb.encode(seed_texts)
    query_vec = emb.encode([text])[0]

    # Aggregate similarity by label
    label_scores: dict[str, List[float]] = {l: [] for l in LABELS}
    for (label, idx) in seed_index:
        sim = _cosine(query_vec, seed_vecs[idx])
        label_scores[label].append(sim)

    averaged = {l: float(np.mean(vals)) if vals else 0.0 for l, vals in label_scores.items()}
    ranked = sorted(averaged.items(), key=lambda x: x[1], reverse=True)
    best = ranked[0][0] if ranked else "casual"
    return Intent(label=best, scores=ranked)
