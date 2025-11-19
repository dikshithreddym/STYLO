# STYLO Backend Analysis & Outfit Suggestion Tuning Guide

## 📋 Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Core Components](#core-components)
3. [Outfit Suggestion Engines](#outfit-suggestion-engines)
4. [Fine-Tuning Guide](#fine-tuning-guide)
5. [Key Parameters Reference](#key-parameters-reference)

---

## System Architecture Overview

### Technology Stack
- **Framework**: FastAPI (Python)
- **Database**: SQLite (local) / PostgreSQL (production)
- **ML Models**: 
  - Sentence Transformers (`all-MiniLM-L6-v2`) for semantic embeddings
  - Optional: Google Gemini 2.5 Flash API for advanced suggestions
- **Color Science**: CIEDE2000 color difference algorithm

### Project Structure
```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # Database connection & session management
│   ├── models.py            # SQLAlchemy models (WardrobeItem)
│   ├── schemas.py           # Pydantic schemas for API validation
│   ├── routers/
│   │   ├── suggestions_v2.py    # V2 API endpoint (PRIMARY)
│   │   ├── suggestions.py       # V1 API endpoint (LEGACY)
│   │   └── wardrobe_db.py        # Wardrobe CRUD operations
│   ├── reco/                # Recommendation engine
│   │   ├── selector.py      # Main outfit assembly logic
│   │   ├── intent.py        # Intent classification (zero-shot)
│   │   ├── embedding.py     # Sentence transformer wrapper
│   │   └── color_matcher.py # Color harmony scoring
│   └── utils/
│       ├── gemini_suggest.py    # Gemini API integration
│       └── image_analyzer.py    # Image analysis utilities
```

---

## Core Components

### 1. Database Layer (`database.py`, `models.py`)

**WardrobeItem Model**:
- `id`: Primary key
- `type`: Item name (e.g., "T-Shirt", "Jeans")
- `color`: Color string (e.g., "blue", "navy")
- `category`: One of: `top`, `bottom`, `footwear`, `layer`, `one-piece`, `accessories`
- `image_url`: Cloudinary URL
- `image_description`: AI-generated description (used for semantic matching)
- `cloudinary_id`: For image deletion

### 2. API Endpoints

#### V2 Endpoint: `/v2/suggestions` (PRIMARY) ⭐
- **File**: `routers/suggestions_v2.py`
- **Method**: POST
- **Request**: `{ "text": "business meeting", "limit": 3 }`
- **Response**: 
  ```json
  {
    "intent": "business",
    "outfits": [
      {
        "top": {...},
        "bottom": {...},
        "footwear": {...},
        "outerwear": {...},
        "accessories": {...},
        "score": 85.5,
        "rationale": "This professional outfit..."
      }
    ]
  }
  ```

**Flow**:
1. Classify intent (business, casual, formal, etc.)
2. Try Gemini API if configured (optional)
3. Fallback to semantic embedding engine
4. Score outfits (completeness + semantic + color)
5. Return top 3 outfits with scores and rationales

#### V1 Endpoint: `/suggestions` (LEGACY)
- **File**: `routers/suggestions.py`
- **Method**: POST
- **Status**: Kept for backwards compatibility
- **Technology**: Rules-based with keyword matching
- **Performance**: Slower than V2, but handles item searches well

---

## Outfit Suggestion Engines

### V2 Semantic Engine (Primary) 🎯

**Location**: `app/reco/selector.py`

**How It Works**:
1. **Intent Classification** (`intent.py`):
   - Zero-shot classification using semantic embeddings
   - Compares user query to seed descriptions for each intent
   - Returns best matching intent (business, casual, formal, etc.)

2. **Item Scoring**:
   - Each item scored by:
     - **Query similarity** (60%): How well item matches user's words
     - **Intent similarity** (40%): How well item matches the occasion
   - Intent-based bonuses/penalties applied:
     - Preferred items: +0.12 to +0.18 boost
     - Avoided items: -0.15 to -0.35 penalty

3. **Outfit Assembly**:
   - Selects top 8 items per category
   - Builds combinations (top + bottom + footwear required)
   - Optionally adds layer and accessories

4. **Outfit Scoring**:
   - **Color harmony** (40%): CIEDE2000 color science
   - **Semantic match** (60%): Average query similarity across items
   - **Intent bias**: Small boost (0.02-0.05) for occasion appropriateness

5. **Final Selection**:
   - Sorts by total score
   - Returns top 3 outfits

### Gemini API Integration (Optional) 🤖

**Location**: `app/utils/gemini_suggest.py`

**How to Enable**:
```bash
# In .env file
GEMINI_API_KEY=your-api-key-here
```

**How It Works**:
- If `GEMINI_API_KEY` is set, V2 endpoint tries Gemini first
- Gemini uses natural language understanding to select outfits
- Falls back to semantic engine if Gemini fails/unavailable

**Trade-offs**:
- ✅ Better natural language understanding
- ✅ Handles complex style preferences
- ❌ Slower (API latency)
- ❌ Costs money (Google API pricing)
- ❌ Less deterministic

---

## Fine-Tuning Guide

### 🎛️ Key Tunable Parameters

All parameters are in `backend/app/reco/selector.py` with `# TUNE THIS` comments.

### 1. Intent Bias Values (Lines 35-43)

**What it does**: Slightly favors certain occasions when outfits have similar scores.

**Current values**:
```python
BIAS = {
    "business": 0.05,    # Slight boost for business/professional
    "formal": 0.05,     # Slight boost for formal/wedding
    "party": 0.04,      # Moderate boost for party/social
    "casual": 0.03,     # Lower bias (already common)
    "workout": 0.05,    # Boost for athletic/active
    "beach": 0.04,      # Moderate boost for beach/vacation
    "hiking": 0.02,     # Lower bias (specific use case)
}
```

**How to tune**:
- **Increase** (0.06-0.08) if an intent isn't appearing enough
- **Decrease** (0.01-0.02) if an intent is over-selected
- **Example**: If "business" outfits aren't showing up, change `"business": 0.05` → `0.07`

---

### 2. Intent Rules - Prefer/Avoid Lists (Lines 62-105)

**What it does**: Items matching "prefer" keywords get score boost. Items matching "avoid" keywords get penalty.

**Current structure**:
```python
"business": {
    "top": {
        "prefer": ["shirt", "button-down", "polo"],
        "avoid": ["t-shirt", "hoodie", "tee"]
    },
    "bottom": {
        "prefer": ["chino", "dress pant", "suit pant"],
        "avoid": ["short", "shorts", "jogger"]
    },
    ...
}
```

**How to tune**:
- **Add to "prefer"**: Items you want prioritized for an occasion
- **Add to "avoid"**: Items you want excluded for an occasion
- **Example**: To prioritize "henley" shirts for casual:
  ```python
  "casual": {
      "top": {"prefer": ["t-shirt", "polo", "sweater", "henley"], ...}
  }
  ```

---

### 3. Intent Bias Bonuses/Penalties (Lines 134-138)

**What it does**: Controls how strongly prefer/avoid rules are applied.

**Current values**:
```python
# Preferred items bonus
bonus += 0.18 if label in {"business", "formal"} else 0.12

# Avoided items penalty
bonus -= 0.35 if label in {"business", "formal"} else 0.15
```

**How to tune**:
- **Increase bonus** (0.18 → 0.25): Makes preferred items rank much higher
- **Increase penalty** (0.35 → 0.50): More strictly excludes avoided items
- **Example**: To make business outfits STRICTER about avoiding t-shirts:
  ```python
  bonus -= 0.50 if label in {"business", "formal"} else 0.15
  ```

---

### 4. Query vs Intent Weight (Line 185)

**What it does**: Balances user's specific words vs occasion appropriateness.

**Current value**:
```python
raw = 0.6 * s1 + 0.4 * s2  # 60% query, 40% intent
```

**How to tune**:
- **More query-driven** (0.7/0.3): User's words matter more
  - Example: "blue shirt" → prioritizes items with "blue" in description
- **More context-appropriate** (0.5/0.5): Occasion matters more
  - Example: "business meeting" → prioritizes business-appropriate items regardless of specific words

---

### 5. Color vs Semantic Weight (Line 322)

**What it does**: Balances color harmony vs query matching in final outfit selection.

**Current value**:
```python
total = 0.6 * cscore + 0.4 * sem + _bias_for(label)
# 60% semantic, 40% color
```

**How to tune**:
- **Color-focused** (0.6 color, 0.4 semantic): Prioritizes well-coordinated colors
- **Query-focused** (0.3 color, 0.7 semantic): Prioritizes matching user's words
- **Example**: For better color coordination:
  ```python
  total = 0.6 * cscore + 0.4 * sem + _bias_for(label)
  ```

---

### 6. Performance Tuning

#### Category Pool Size (Line 189)
```python
cat_best[cat] = scored[:8]  # Top 8 per category
```
- **Increase** (8 → 12): More diversity, slower
- **Decrease** (8 → 5): Faster, less variety

#### Outfit Combinations (Line 266)
```python
for i in range(10):  # limit combinations
```
- **Increase** (10 → 15): More outfit variety, slower
- **Decrease** (10 → 5): Faster, fewer variations

---

## Key Parameters Reference

| Parameter | File | Line | Effect | Default |
|-----------|------|------|--------|---------|
| Intent bias | `selector.py` | 35-43 | Favor certain occasions | 0.02-0.05 |
| Intent rules | `selector.py` | 62-105 | Prefer/avoid specific items | Varies |
| Bias bonuses | `selector.py` | 134-138 | Strength of prefer/avoid | +0.12 to +0.18 |
| Bias penalties | `selector.py` | 134-138 | Strength of avoid rules | -0.15 to -0.35 |
| Query vs intent | `selector.py` | 185 | Balance user words vs context | 0.6/0.4 |
| Color vs semantic | `selector.py` | 322 | Balance color vs query match | 0.4/0.6 |
| Category pool | `selector.py` | 189 | Diversity vs speed | 8 items |
| Combinations | `selector.py` | 266 | Variety vs speed | 10 iterations |

---

## Common Tuning Scenarios

### Scenario 1: Business Outfits Too Casual
**Problem**: Business suggestions include t-shirts or sneakers.

**Solution**:
1. Increase business penalty (line 138): `-0.35` → `-0.50`
2. Add more items to avoid list (line 66): `"avoid": ["t-shirt", "sneaker", ...]`
3. Increase business bias (line 36): `0.05` → `0.07`

---

### Scenario 2: Not Matching User's Specific Words
**Problem**: User says "blue shirt" but gets red shirts.

**Solution**:
1. Increase query weight (line 185): `0.6` → `0.7`
2. Increase semantic weight in final scoring (line 322): `0.4` → `0.5`

---

### Scenario 3: Color Coordination Poor
**Problem**: Outfits have clashing colors.

**Solution**:
1. Increase color weight (line 322): `0.4` → `0.6`
2. Check color_matcher.py for CIEDE2000 normalization

---

### Scenario 4: Too Few Outfit Variations
**Problem**: Always getting same 3 outfits.

**Solution**:
1. Increase category pool (line 189): `8` → `12`
2. Increase combinations (line 266): `10` → `15`

---

## Testing Recommendations

1. **Test with varied queries**:
   - "business meeting"
   - "casual date night"
   - "workout at the gym"
   - "beach vacation"

2. **Monitor scoring**:
   - Add logging to see what drives outfit selection
   - Check scores in API response

3. **A/B test parameters**:
   - Compare different weight configurations
   - Track which outfits users prefer

4. **Collect user feedback**:
   - Track which outfits users actually wear
   - Adjust parameters based on real usage

---

## Quick Start: Making Your First Tune

1. **Identify the issue**: 
   - "Business outfits include t-shirts" → Need stricter business rules
   - "Not matching my color preference" → Need higher query weight
   - "Colors clash" → Need higher color weight

2. **Find the parameter**:
   - Use the reference table above
   - Open `backend/app/reco/selector.py`
   - Look for `# TUNE THIS` comments

3. **Make small changes**:
   - Start with 10-20% adjustments
   - Test and iterate

4. **Test**:
   - Use the `/v2/suggestions` endpoint
   - Try different queries
   - Check scores and rationales

---

## Additional Resources

- **Tuning Documentation**: `backend/OUTFIT_SUGGESTION_TUNING.md`
- **API Docs**: Visit `/docs` when server is running
- **Intent Seeds**: `backend/app/reco/intent.py` (lines 16-45)
- **Color Science**: `backend/app/reco/color_matcher.py`

---

## Summary

The STYLO backend uses a **semantic embedding-based recommendation engine** that:
- Understands user queries using natural language
- Matches items to occasions using intent classification
- Scores outfits by color harmony and semantic relevance
- Provides explainable suggestions with scores and rationales

**Key files for tuning**:
- `app/reco/selector.py` - Main outfit assembly and scoring
- `app/reco/intent.py` - Intent classification seeds
- `app/reco/color_matcher.py` - Color harmony scoring

**Primary endpoint**: `/v2/suggestions` (V2 semantic engine)
**Legacy endpoint**: `/suggestions` (V1 rules-based, for backwards compatibility)

