# Outfit Suggestion Tuning Guide

## Overview

The STYLO backend uses **V2 semantic engine** as the primary outfit suggestion system. This guide explains how to tune outfit suggestions and includes an optional Gemini API integration.

## System Architecture

### V2 Engine (Primary) - `/v2/suggestions`
- **Technology**: Semantic embeddings (sentence-transformers) + color harmony scoring
- **Status**: ✅ **PRIMARY** - Fast, accurate, and optimized
- **Location**: `backend/app/reco/selector.py`

### V1 Engine (Legacy) - `/suggestions`
- **Technology**: Rules-based with keyword matching
- **Status**: ⚠️ **LEGACY** - Kept for backwards compatibility and item searches only
- **Performance**: Optimized but slower than V2

### Gemini API (Optional Enhancement)
- **Technology**: Google Gemini 2.5 Flash for natural language outfit generation
- **Status**: 🔄 **OPTIONAL** - Can be enabled via environment variable
- **Location**: `backend/app/utils/gemini_suggest.py`

---

## Tuning V2 Engine Parameters

All tunable parameters are in `backend/app/reco/selector.py` with clear comments explaining their effects.

### 1. Intent Bias Values (Lines 35-43)

**What it does**: Slightly favors certain occasions when outfits have similar scores.

**How to tune**:
```python
BIAS = {
    "business": 0.05,    # Increase to 0.07 if business outfits aren't appearing enough
    "formal": 0.05,      # Increase to 0.08 for more formal suggestions
    "party": 0.04,
    "casual": 0.03,
    "workout": 0.05,
    "beach": 0.04,
    "hiking": 0.02,
}
```

**Example**: If users complain that "business" outfits aren't showing up enough, increase `"business": 0.05` → `0.07`.

---

### 2. Intent Rules - Prefer/Avoid Lists (Lines 62-105)

**What it does**: Items matching "prefer" keywords get +0.12 to +0.18 score boost. Items matching "avoid" keywords get -0.15 to -0.35 penalty.

**How to tune**:
```python
"business": {
    "top": {
        "prefer": ["shirt", "button-down", "polo"],  # Add "henley" here to prioritize henley shirts
        "avoid": ["t-shirt", "hoodie", "tee"]        # Add "tank" here to avoid tank tops
    },
    ...
}
```

**Example**: To prioritize "henley" shirts for casual occasions:
```python
"casual": {
    "top": {"prefer": ["t-shirt", "polo", "sweater", "henley"], ...}
}
```

---

### 3. Intent Bias Bonuses/Penalties (Lines 134-138)

**What it does**: Controls how strongly the prefer/avoid rules are applied.

**How to tune**:
```python
# Preferred items bonus
bonus += 0.18 if label in {"business", "formal"} else 0.12
# Increase 0.18 → 0.25 to make preferred items rank much higher

# Avoided items penalty
bonus -= 0.35 if label in {"business", "formal"} else 0.15
# Increase 0.35 → 0.50 to STRICTLY exclude avoided items
```

**Example**: To make business outfits STRICTER about avoiding t-shirts, change `-0.35` → `-0.50`.

---

### 4. Semantic Similarity Weights (Line 185)

**What it does**: Balances query matching vs intent matching.

- **Higher query weight (0.6)**: User's specific words matter more (e.g., "blue shirt")
- **Higher intent weight (0.4)**: Occasion appropriateness matters more (e.g., "business")

**How to tune**:
```python
raw = 0.6 * s1 + 0.4 * s2  # Current: 60% query, 40% intent

# More query-driven (literal matching):
raw = 0.7 * s1 + 0.3 * s2

# More context-appropriate (occasion matters more):
raw = 0.5 * s1 + 0.5 * s2
```

---

### 5. Final Outfit Scoring Weights (Line 321)

**What it does**: Balances color harmony vs semantic relevance in final outfit selection.

- **Higher color weight (0.4)**: Prioritizes outfits with well-coordinated colors
- **Higher semantic weight (0.6)**: Prioritizes outfits matching the query/intent

**How to tune**:
```python
total = 0.4 * cscore + 0.6 * sem + _bias_for(label)

# Color-focused (prioritize matching colors):
total = 0.6 * cscore + 0.4 * sem + _bias_for(label)

# Query-focused (prioritize matching user's words):
total = 0.3 * cscore + 0.7 * sem + _bias_for(label)
```

---

### 6. Performance Tuning (Lines 189, 266)

**Category pool size** (Line 189):
```python
cat_best[cat] = scored[:8]  # Top 8 per category
# Increase 8 → 12 for more diversity (slower)
# Decrease 8 → 5 for faster performance (less variety)
```

**Outfit combinations** (Line 266):
```python
for i in range(10):  # limit combinations
# Increase range(10) → range(15) for more variety (slower)
# Decrease range(10) → range(5) for faster performance
```

---

## Gemini API Integration (Optional)

The Gemini API can be used as an alternative to the semantic embedding engine for outfit suggestions.

### Enable Gemini Suggestions

Add to your `.env` file:
```bash
USE_GEMINI_FOR_SUGGESTIONS=true
GEMINI_API_KEY=your-gemini-api-key
```

**How it works**:
1. If `USE_GEMINI_FOR_SUGGESTIONS=true`, V2 endpoint tries Gemini first
2. If Gemini fails or isn't configured, falls back to semantic embedding engine
3. Gemini provides natural language understanding but is slower and costs money

### Benefits
- Natural language understanding for complex queries
- Can handle nuanced style preferences
- Good for creative/fashion-forward suggestions

### Trade-offs
- Slower response time (API call latency)
- Costs money (Google Gemini API pricing)
- Less deterministic (may vary across calls)

---

## V1 Engine Optimization

The V1 rules-based engine has been optimized for performance:

1. **Cached wardrobe queries**: Reduced database calls
2. **Limited alternatives**: Max 5 outfit variations (was unlimited)
3. **Simplified fallback chains**: Reduced complexity

**Note**: V1 is still available for backwards compatibility but V2 is recommended.

---

## Testing Recommendations

1. **Test with varied queries**: Try different occasions, colors, and styles
2. **Monitor scoring**: Add logging to see what drives outfit selection
3. **A/B test parameters**: Compare different weight configurations
4. **Collect user feedback**: Track which outfits users prefer

---

## Quick Reference

| Parameter | File | Line | Effect |
|-----------|------|------|--------|
| Intent bias | `selector.py` | 35-43 | Favor certain occasions |
| Intent rules | `selector.py` | 62-105 | Prefer/avoid specific items |
| Bias bonuses | `selector.py` | 134-138 | Strength of prefer/avoid rules |
| Query vs intent | `selector.py` | 185 | Balance user words vs context |
| Color vs semantic | `selector.py` | 321 | Balance color harmony vs query match |
| Category pool size | `selector.py` | 189 | Diversity vs speed |
| Outfit combinations | `selector.py` | 266 | Variety vs speed |

---

## Client Review Checklist

When sending `selector.py` to clients for review, they should focus on:

1. ✅ **Intent bias values** - Are certain occasions over/under-represented?
2. ✅ **Intent rules** - Should specific items be preferred/avoided for occasions?
3. ✅ **Scoring weights** - Is color coordination or query matching more important?
4. ✅ **Performance settings** - Balance speed vs diversity needs

All tunable parameters are marked with `# TUNE THIS` comments for easy identification.

