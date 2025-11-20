# Beach/Swimming Outfit Tuning Changes

## Problem Identified
For "going to swim" queries, the system was:
- ✅ Correctly detecting "beach" intent
- ❌ Selecting inappropriate footwear (dress shoes like "Denver Hayes Renmark Lace Up Style Dress Shoes")
- ❌ Selecting heavy jackets (suede jackets) for beach/swimming
- ⚠️ Low match scores (58%) suggesting suboptimal selection

## Changes Made

### 1. Enhanced Beach Footwear Avoid List
**File**: `backend/app/reco/selector.py` (line 84)

**Added keywords to avoid**:
- `"dress shoe"`, `"lace up"`, `"lace-up"`, `"oxford"`, `"derby"`, `"formal"`, `"heel"`, `"boot"`

**Result**: Dress shoes and formal footwear will receive -0.35 penalty (same as business/formal)

### 2. Enhanced Beach Layer Avoid List
**File**: `backend/app/reco/selector.py` (line 85)

**Added keywords to avoid**:
- `"suede"`, `"heavy"`, `"winter"`, `"wool"`, `"fleece"`, `"racer"`

**Added keywords to prefer**:
- `"light"`, `"windbreaker"`, `"cover-up"`

**Result**: Heavy/warm jackets will be penalized for beach occasions

### 3. Hard Filter for Beach (NEW)
**File**: `backend/app/reco/selector.py` (lines 217-236)

**What it does**: Similar to business/formal hard filters, this strictly blocks:
- **Footwear**: All dress shoes, formal footwear, boots, loafers
- **Layer**: Heavy jackets, suede, wool, winter items

**Result**: Even if dress shoes score well semantically, they'll be filtered out before outfit assembly

### 4. Increased Beach Penalty Strength
**File**: `backend/app/reco/selector.py` (line 138)

**Change**: Beach now uses same strong penalty as business/formal
- **Before**: `-0.15` penalty for avoided items
- **After**: `-0.35` penalty for avoided items

**Result**: Dress shoes and heavy jackets will be much less likely to be selected

### 5. Improved Beach-Specific Filtering
**File**: `backend/app/reco/selector.py` (lines 251-272)

**Enhancements**:
- Removes formal footwear that might slip through
- Strongly prioritizes sandals/slides/flip-flops
- Demotes athletic sneakers when sandals are available

**Result**: Better footwear selection for beach/swimming

### 6. Increased Beach Intent Bias
**File**: `backend/app/reco/selector.py` (line 41)

**Change**: 
- **Before**: `"beach": 0.04`
- **After**: `"beach": 0.06`

**Result**: Beach outfits will rank slightly higher when scores are similar

### 7. Enhanced Intent Classification for Swimming
**File**: `backend/app/reco/intent.py` (lines 37-40)

**Added seed descriptions**:
- `"swimming, beach day, water activities, sandals"`
- `"going to swim, pool or ocean, lightweight clothing"`

**Result**: "going to swim" queries will better match beach intent

## Expected Improvements

### Before Tuning
- ❌ Dress shoes selected for beach/swimming
- ❌ Heavy suede jackets selected
- ⚠️ 58% match score
- ⚠️ Inappropriate items in suggestions

### After Tuning
- ✅ Only sandals/slides/flip-flops for footwear
- ✅ Light layers only (no heavy jackets)
- ✅ Higher match scores (better item selection)
- ✅ More appropriate beach/swimming outfits

## Testing Recommendations

Test with these queries:
1. "going to swim"
2. "beach day"
3. "swimming at the pool"
4. "ocean swim"
5. "beach vacation"

**Expected results**:
- Footwear: Only sandals, slides, or flip-flops
- Layer: Light windbreakers or cover-ups (or none)
- No dress shoes, boots, or formal footwear
- No heavy jackets, suede, or wool items

## Files Modified

1. `backend/app/reco/selector.py`
   - Line 84: Enhanced footwear avoid list
   - Line 85: Enhanced layer avoid/prefer lists
   - Line 41: Increased beach bias
   - Line 138: Increased beach penalty strength
   - Lines 217-236: Added hard filter for beach
   - Lines 251-272: Improved beach-specific filtering

2. `backend/app/reco/intent.py`
   - Lines 37-40: Added swimming-related seed descriptions

## Rollback Instructions

If issues occur, revert these changes:
1. Restore original beach rules (lines 81-86 in selector.py)
2. Remove hard filter block (lines 217-236)
3. Restore original beach bias (line 41: `0.04`)
4. Restore original penalty (line 138: remove "beach" from strong penalty list)
5. Restore original beach filtering (lines 251-262)
6. Restore original intent seeds (intent.py lines 37-40)

