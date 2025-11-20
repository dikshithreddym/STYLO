# Scoring Improvements for Beach/Swimming Outfits

## Problem
After initial tuning, beach outfits were still showing low match scores (58%, 56%, 55%) despite correct intent detection and appropriate item filtering.

## Root Cause
The final scoring in `suggestions_v2.py` was only considering:
- Completeness (40%)
- Semantic similarity (40%)
- Color harmony (20%)

It was **not rewarding outfits that had intent-appropriate items** (e.g., sandals for beach, athletic wear for workout).

## Changes Made

### 1. Added Intent-Appropriate Item Bonuses
**File**: `backend/app/routers/suggestions_v2.py` (lines 220-247)

**What it does**: Adds bonus points when outfits contain items that match the intent:

- **Beach outfits**:
  - +15% bonus if 2+ beach-appropriate items (sandal, slide, flip, short, swim, beach, light)
  - +8% bonus if 1 beach-appropriate item
  
- **Workout outfits**:
  - +12% bonus if 2+ athletic items (athletic, sport, gym, workout, performance, running, trainer)
  
- **Business/Formal outfits**:
  - +10% bonus if 2+ formal items (dress, shirt, blazer, suit, loafer, dress shoe, trouser)

**Result**: Outfits with appropriate items get higher scores (e.g., 58% → 73% for beach with sandals and shorts)

### 2. Adjusted Scoring Weights
**File**: `backend/app/routers/suggestions_v2.py` (line 246)

**Before**:
```python
total_score = 0.4 * completeness + 0.4 * semantic_score + 0.2 * color_score
```

**After**:
```python
base_score = 0.35 * completeness + 0.35 * semantic_score + 0.3 * color_score
total_score = min(1.0, base_score + intent_bonus)
```

**Changes**:
- Slightly reduced completeness weight (40% → 35%)
- Slightly reduced semantic weight (40% → 35%)
- Increased color weight (20% → 30%)
- Added intent bonus on top (up to 15% for beach)

**Result**: Better balance between all factors, with rewards for appropriate items

### 3. Enhanced Rationale for Beach Outfits
**File**: `backend/app/routers/suggestions_v2.py` (lines 270-279)

**What it does**: Adds specific feedback when beach-appropriate items are selected:
- "Perfect beach-appropriate items selected for swimming and water activities."

**Result**: Users get better explanations of why items were chosen

## Expected Score Improvements

### Before
- Beach outfit with sandals + shorts: **58%**
- Beach outfit with slides + shorts: **56%**
- Beach outfit with appropriate items: **55%**

### After
- Beach outfit with 2+ beach items (sandals + shorts): **58% + 15% = 73%**
- Beach outfit with 1 beach item (slides): **56% + 8% = 64%**
- Beach outfit with appropriate items: **55% + 15% = 70%**

**Note**: Actual scores depend on semantic similarity and color harmony, but intent bonuses provide significant boosts.

## Testing

Test with these queries:
1. "going to swim" - Should see 70%+ scores if sandals/slides are selected
2. "beach day" - Should see higher scores with beach-appropriate items
3. "workout at gym" - Should see 12% bonus for athletic items
4. "business meeting" - Should see 10% bonus for formal items

## Files Modified

1. `backend/app/routers/suggestions_v2.py`
   - Lines 220-247: Added intent-appropriate item bonuses
   - Lines 270-279: Enhanced beach outfit rationale

## Additional Notes

### Item Name Display Issue
If items are showing as IDs (e.g., "Iv9A2Enwrpavrlz4Dmls") instead of names, this is likely a **frontend display issue**. The backend is correctly passing item names via the `name` field in `V2Item`.

**To fix frontend**:
- Check that the frontend is displaying `item.name` or `item.type` instead of `item.id`
- Verify the API response includes proper names in the `name` field

### Score Calculation Flow

1. **Item Selection** (`selector.py`):
   - Items scored by query + intent similarity
   - Intent bonuses/penalties applied
   - Top 8 items per category selected

2. **Outfit Assembly** (`selector.py`):
   - Combinations built from top items
   - Outfits scored by color harmony + semantic match
   - Top 3 outfits selected

3. **Final Scoring** (`suggestions_v2.py`):
   - Completeness: 35%
   - Semantic: 35%
   - Color: 30%
   - **Intent Bonus: Up to 15%** (NEW)

## Rollback Instructions

If issues occur, revert these changes:
1. Restore original scoring (line 219): `0.4 * completeness + 0.4 * semantic_score + 0.2 * color_score`
2. Remove intent bonus calculation (lines 220-242)
3. Restore original rationale (remove lines 270-279)

