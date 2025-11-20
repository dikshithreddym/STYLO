# Outfit Suggestion Flow Diagram

## High-Level Flow

```
User Query: "business meeting outfit"
         │
         ▼
┌─────────────────────────────────────┐
│  1. Intent Classification          │
│  (app/reco/intent.py)               │
│  - Zero-shot classification          │
│  - Compares query to seed descs      │
│  - Returns: "business"              │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  2. Load Wardrobe Items             │
│  (from database)                    │
│  - All items with categories         │
│  - Includes image descriptions       │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  3. Try Gemini API?                 │
│  (if GEMINI_API_KEY set)            │
│  - Optional enhancement              │
│  - Falls back if fails               │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  4. Semantic Engine                 │
│  (app/reco/selector.py)             │
│  ┌───────────────────────────────┐  │
│  │ 4a. Item Scoring               │  │
│  │  - Query similarity (60%)     │  │
│  │  - Intent similarity (40%)     │  │
│  │  - Intent bias (+/- bonuses)   │  │
│  │  - Top 8 per category         │  │
│  └───────────────────────────────┘  │
│         │                            │
│         ▼                            │
│  ┌───────────────────────────────┐  │
│  │ 4b. Outfit Assembly             │  │
│  │  - Build combinations           │  │
│  │  - Required: top+bottom+shoes  │  │
│  │  - Optional: layer+accessories │  │
│  │  - Up to 10 combinations       │  │
│  └───────────────────────────────┘  │
│         │                            │
│         ▼                            │
│  ┌───────────────────────────────┐  │
│  │ 4c. Outfit Scoring              │  │
│  │  - Color harmony (40%)         │  │
│  │  - Semantic match (60%)       │  │
│  │  - Intent bias (0.02-0.05)    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  5. Final Scoring & Rationale      │
│  (suggestions_v2.py)                │
│  - Completeness (40%)               │
│  - Semantic (40%)                    │
│  - Color (20%)                       │
│  - Generate explanation              │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  6. Return Top 3 Outfits            │
│  - Sorted by score                  │
│  - Each with rationale              │
└─────────────────────────────────────┘
```

## Detailed Scoring Breakdown

### Item-Level Scoring (per item in wardrobe)

```
Item: "Blue Dress Shirt"
         │
         ├─ Query Vector: [0.2, 0.5, ...] (from "business meeting")
         ├─ Intent Vector: [0.3, 0.4, ...] (from "business")
         │
         ▼
┌─────────────────────────────────────┐
│ Base Score Calculation               │
│  s1 = cosine(query_vec, item_vec)     │
│  s2 = cosine(intent_vec, item_vec)   │
│  raw = 0.6 * s1 + 0.4 * s2           │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Intent Bias Application              │
│  Check: "business" rules             │
│  - "shirt" in prefer list → +0.18   │
│  - "t-shirt" not in avoid list      │
│  Final = raw + 0.18                  │
└─────────────────────────────────────┘
         │
         ▼
Score: 0.85 (ranked in top 8 for "top" category)
```

### Outfit-Level Scoring (per complete outfit)

```
Outfit: {top: "Blue Shirt", bottom: "Chinos", footwear: "Loafers"}
         │
         ├─ Color Harmony Score
         │  └─ CIEDE2000 distance between colors
         │  └─ Normalized to 0-1 (higher = better)
         │
         ├─ Semantic Match Score
         │  └─ Average cosine similarity of all items to query
         │
         └─ Intent Bias
            └─ Small boost based on occasion type
         │
         ▼
┌─────────────────────────────────────┐
│ Final Outfit Score                   │
│  total = 0.4 * color + 0.6 * sem    │
│         + intent_bias                │
│  = 0.4 * 0.8 + 0.6 * 0.75 + 0.05    │
│  = 0.32 + 0.45 + 0.05               │
│  = 0.82 (82%)                        │
└─────────────────────────────────────┘
```

## Key Decision Points

### 1. Intent Classification
- **Input**: User query text
- **Process**: Semantic similarity to seed descriptions
- **Output**: Intent label (business, casual, formal, etc.)
- **Tunable**: Seed descriptions in `intent.py`

### 2. Item Selection
- **Input**: All wardrobe items
- **Process**: 
  - Score each item by query + intent similarity
  - Apply intent-based bonuses/penalties
  - Filter by hard rules (e.g., no t-shirts for business)
- **Output**: Top 8 items per category
- **Tunable**: 
  - Query vs intent weight (line 185)
  - Intent rules (lines 62-105)
  - Bias bonuses/penalties (lines 134-138)

### 3. Outfit Assembly
- **Input**: Top items per category
- **Process**: 
  - Build combinations (greedy selection)
  - Ensure required categories present
  - Add optional categories if available
- **Output**: Up to 10 outfit candidates
- **Tunable**: 
  - Category pool size (line 189)
  - Combination limit (line 266)

### 4. Outfit Scoring
- **Input**: Complete outfit candidates
- **Process**: 
  - Calculate color harmony (CIEDE2000)
  - Calculate semantic match (average similarity)
  - Apply intent bias
- **Output**: Scored outfits
- **Tunable**: 
  - Color vs semantic weight (line 322)
  - Intent bias values (lines 35-43)

### 5. Final Selection
- **Input**: Scored outfits
- **Process**: 
  - Sort by score (descending)
  - Take top 3
  - Generate rationales
- **Output**: Top 3 outfits with scores and explanations

## Scoring Weights Summary

| Stage | Component | Weight | Location |
|-------|-----------|--------|----------|
| Item Scoring | Query similarity | 60% | selector.py:185 |
| Item Scoring | Intent similarity | 40% | selector.py:185 |
| Item Scoring | Intent bonus (prefer) | +0.12 to +0.18 | selector.py:134 |
| Item Scoring | Intent penalty (avoid) | -0.15 to -0.35 | selector.py:138 |
| Outfit Scoring | Color harmony | 40% | selector.py:322 |
| Outfit Scoring | Semantic match | 60% | selector.py:322 |
| Outfit Scoring | Intent bias | 0.02-0.05 | selector.py:35-43 |
| Final Scoring | Completeness | 40% | suggestions_v2.py:219 |
| Final Scoring | Semantic | 40% | suggestions_v2.py:219 |
| Final Scoring | Color | 20% | suggestions_v2.py:219 |

## Example: "Business Meeting" Query

```
Query: "business meeting outfit"
         │
         ▼
Intent: "business" (score: 0.92)
         │
         ▼
Item Scoring:
  - "Blue Dress Shirt" → 0.85 (prefer bonus: +0.18)
  - "Navy Chinos" → 0.78 (prefer bonus: +0.18)
  - "Black Loafers" → 0.82 (prefer bonus: +0.18)
  - "T-Shirt" → 0.45 (avoid penalty: -0.35)
         │
         ▼
Outfit Assembly:
  Outfit 1: Shirt + Chinos + Loafers
  Outfit 2: Shirt + Chinos + Boots
  Outfit 3: Shirt + Dress Pants + Loafers
         │
         ▼
Outfit Scoring:
  Outfit 1: 0.82 (color: 0.8, semantic: 0.75, bias: 0.05)
  Outfit 2: 0.79 (color: 0.75, semantic: 0.73, bias: 0.05)
  Outfit 3: 0.81 (color: 0.78, semantic: 0.74, bias: 0.05)
         │
         ▼
Final Response:
  Top 3 outfits sorted by score
  Each with rationale explaining selection
```

## Tuning Impact Examples

### Increase Business Strictness
**Change**: Intent penalty from -0.35 to -0.50
**Effect**: T-shirts will score even lower for business queries
**Result**: More formal items selected

### Increase Query Weight
**Change**: Query weight from 0.6 to 0.7
**Effect**: User's specific words matter more
**Result**: "blue shirt" query → more blue items selected

### Increase Color Weight
**Change**: Color weight from 0.4 to 0.6
**Effect**: Color coordination prioritized
**Result**: Better color-matched outfits

### Increase Category Pool
**Change**: Pool size from 8 to 12
**Effect**: More items considered per category
**Result**: More diverse outfit variations

