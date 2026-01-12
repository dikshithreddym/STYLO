"""
Optional Gemini API integration for outfit suggestions.
This provides an alternative to the semantic embedding-based engine.
"""
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException
import json
import re
import logging
from typing import List, Dict, Optional
from app.config import settings
from app.utils.profiler import get_profiler

# Timeout configuration for Gemini API calls (seconds)
# - connect_timeout: time to establish connection
# - read_timeout: time to receive response (AI processing takes time)
GEMINI_TIMEOUT = (5.0, 30.0)  # (connect, read) tuple for requests library

# Gemini token limits (approximate)
# Gemini 2.5 Flash: ~1M input tokens, 8K output tokens
# Using conservative estimate for safety
MAX_INPUT_TOKENS = 100000  # Conservative limit
TOKEN_WARNING_THRESHOLD = 50000  # Warn if approaching limit

"""
Use Gemini API to suggest outfits based on query and wardrobe.
Args:
    query: User's outfit request (e.g., "business meeting", "casual date")
    wardrobe_items: List of wardrobe items with keys: id, name, category, color, image_url, description
    limit: Number of outfits to generate
Returns:
    List of outfit dicts mapping category -> item, or None if Gemini not configured/fails
"""
async def suggest_outfit_with_gemini(
    query: str,
    wardrobe_items: List[Dict],
    limit: int = 3
) -> Optional[List[Dict]]:
    logger = logging.getLogger(__name__)
    import os
    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv("GEMINI_API_KEY")

    if gemini_api_key:
        gemini_api_key = str(gemini_api_key).strip()
    
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not set - cannot use Gemini suggestions")
        return None

    # Log key info for debugging (masked for security)
    logger.debug(f"Using Gemini Key (len={len(gemini_api_key)}): {gemini_api_key[:4]}...{gemini_api_key[-4:]}")

    try:

        # Optimized: Include required categories plus accessories and layers
        MAX_ITEMS_PER_CATEGORY = 5
        REQUIRED_CATEGORIES = ["top", "bottom", "footwear"]
        OPTIONAL_CATEGORIES = ["accessories", "layer"]  # Important for complete outfits
        ALL_PRIORITY_CATEGORIES = REQUIRED_CATEGORIES + OPTIONAL_CATEGORIES
        
        grouped = {cat: [] for cat in ALL_PRIORITY_CATEGORIES}
        for it in wardrobe_items:
            cat = it.get("category", "").lower()
            if cat in grouped and len(grouped[cat]) < MAX_ITEMS_PER_CATEGORY:
                grouped[cat].append(it)
        
        limited_items = []
        # First, add required categories (top, bottom, footwear)
        for cat in REQUIRED_CATEGORIES:
            limited_items.extend(grouped[cat])
        # Then, add optional but important categories (accessories, layer)
        for cat in OPTIONAL_CATEGORIES:
            limited_items.extend(grouped[cat])
        
        # If less than 20, fill with other items (increased from 15 to accommodate accessories)
        MAX_TOTAL_ITEMS = 20
        if len(limited_items) < MAX_TOTAL_ITEMS:
            others = [it for it in wardrobe_items if it not in limited_items]
            limited_items.extend(others[:MAX_TOTAL_ITEMS - len(limited_items)])
        wardrobe_text = _format_wardrobe_for_gemini(limited_items[:MAX_TOTAL_ITEMS])
        item_count = len(limited_items[:MAX_TOTAL_ITEMS])

        # Build unified, improved prompt
        prompt = _build_gemini_prompt(query, wardrobe_text, item_count, limit)
        
        # Check token limits and log warnings
        is_safe, estimated_tokens, warning = _check_token_limits(prompt, wardrobe_items)
        
        if warning:
            logger.warning(f"Token estimation: {warning}")
        
        if not is_safe:
            logger.error(f"Prompt too large ({estimated_tokens} tokens). Truncating wardrobe items.")
            # Truncate wardrobe items if needed (keep top items per category)
            # This should rarely happen with RAG, but provides safety
            max_items = 100  # Emergency fallback limit
            original_count = len(wardrobe_items)
            if original_count > max_items:
                logger.warning(f"Truncating wardrobe from {original_count} to {max_items} items")
                wardrobe_items = wardrobe_items[:max_items]
                wardrobe_text = _format_wardrobe_for_gemini(wardrobe_items)
                prompt = _build_gemini_prompt(query, wardrobe_text, len(wardrobe_items), limit, truncated_from=original_count)
        
        logger.info(f"Sending prompt to Gemini: {len(wardrobe_items)} items, ~{estimated_tokens} tokens")

        # Remove key from URL to use header authentication instead
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        
        profiler = get_profiler()
        # Use structured output for better JSON generation
        # Lower temperature for more consistent, structured responses
        with profiler.measure("gemini_api_request"):
            try:
                response = requests.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": gemini_api_key
                    },
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.3,  # Lower for more consistent structured output
                            "maxOutputTokens": 2048,
                            "responseMimeType": "application/json",  # Enforce JSON output
                        }
                    },
                    timeout=GEMINI_TIMEOUT
                )
            except Timeout:
                logger.error("Gemini API request timed out (exceeded 30s)")
                return None
            except ConnectionError as e:
                logger.error(f"Failed to connect to Gemini API: {e}")
                return None
            except RequestException as e:
                logger.error(f"Gemini API request failed: {type(e).__name__}: {e}")
                return None

        if response.status_code != 200:
            logger.error(f"Gemini API error: {response.status_code} {response.text}")
            return None

        # Extract Gemini response text
        result = response.json()
        if 'candidates' not in result or not result['candidates']:
            logger.error(f"No candidates in Gemini response. Full response: {json.dumps(result, indent=2)}")
            return None

        content = result['candidates'][0]['content']
        if 'parts' not in content or not content['parts']:
            logger.error(f"No parts in Gemini response content. Full response: {json.dumps(result, indent=2)}")
            return None

        text = content['parts'][0]['text'].strip()

        # Extract JSON from response (handle both structured output and markdown code blocks)
        parsed = _extract_json_from_response(text, logger)
        if parsed is None:
            return None

        if 'outfits' not in parsed:
            logger.error("No 'outfits' key in Gemini response JSON.")
            return None

        # Extract intent and item_type from Gemini response
        intent = parsed.get('intent')
        item_type = parsed.get('item_type')
        outfits = parsed.get('outfits')
        if not outfits or not isinstance(outfits, list):
            logger.error("No 'outfits' key in Gemini response JSON or not a list.")
            return None

        # Validate and map item IDs to actual items
        item_map = {it['id']: it for it in wardrobe_items}
        validated_outfits = []


        for outfit_dict in outfits[:limit]:
            validated = {}
            for category in ['top', 'bottom', 'footwear', 'layer', 'accessories']:
                if category in outfit_dict and outfit_dict[category]:
                    item_id = outfit_dict[category].get('id')
                    if item_id and item_id in item_map:
                        validated[category] = item_map[item_id]

            # Extract and add rationale/reason for the outfit
            # Prioritize outfit-specific rationale, fallback to general rationale
            rationale = outfit_dict.get('rationale') or parsed.get('rationale')
            if rationale:
                validated['rationale'] = rationale
            else:
                # Fallback: generate a basic rationale if Gemini didn't provide one
                validated['rationale'] = "This outfit was selected based on your request and wardrobe items."

            # Ensure required categories are present
            if all(cat in validated for cat in ['top', 'bottom', 'footwear']):
                validated_outfits.append(validated)

        if validated_outfits:
            # Return intent, item_type, and outfits
            return {
                "intent": intent,
                "item_type": item_type,
                "outfits": validated_outfits
            }
        else:
            logger.error("No valid outfits returned by Gemini.")
            return None

    except Exception as e:
        logger.error(f"Gemini outfit suggestion error: {e}")
        return None


def _estimate_tokens(text: str) -> int:
    """
    Rough token estimation (1 token ≈ 4 characters for English text).
    This is an approximation; actual tokenization may vary.
    """
    return len(text) // 4


def _format_wardrobe_for_gemini(items: List[Dict]) -> str:
    """
    Format wardrobe items for Gemini prompt.
    Optimized for conciseness while maintaining essential information.
    """
    lines = []
    for it in items:
        # Compact format: ID, Name, Category, Color, Description (if available)
        parts = [f"ID:{it.get('id')}"]
        
        name = it.get('name', 'Unknown')
        if name:
            parts.append(f"Name:{name}")
        
        category = it.get('category', 'unknown')
        if category:
            parts.append(f"Cat:{category}")
        
        color = it.get('color')
        if color:
            parts.append(f"Color:{color}")
        
        # Truncate description if too long (keep first 100 chars)
        description = it.get('description', '')
        if description:
            desc_truncated = description[:100] + "..." if len(description) > 100 else description
            parts.append(f"Desc:{desc_truncated}")
        
        lines.append(" | ".join(parts))
    
    return "\n".join(lines)


def _build_gemini_prompt(
    query: str, 
    wardrobe_text: str, 
    item_count: int, 
    limit: int,
    truncated_from: Optional[int] = None
) -> str:
    """
    Build optimized Gemini prompt for outfit suggestions.
    
    Args:
        query: User's outfit request
        wardrobe_text: Formatted wardrobe items
        item_count: Number of items in wardrobe
        limit: Number of outfits to generate
        truncated_from: Original item count if truncated (for logging)
    
    Returns:
        Formatted prompt string
    """
    wardrobe_note = f"({item_count} items"
    if truncated_from:
        wardrobe_note += f", truncated from {truncated_from}"
    wardrobe_note += ")"
    
    return f"""You are an expert fashion stylist and intelligent wardrobe assistant. Your role is to understand user queries contextually and provide appropriate responses.

## CONTEXT ANALYSIS

USER REQUEST: "{query}"

Analyze this query carefully to determine:
1. **Intent Classification**: What is the user really asking for?
   - "outfit": User wants complete outfit suggestions (e.g., "business meeting outfit", "casual date", "traditional wear")
   - "item_search": User is looking for a specific item type (e.g., "are there any rings", "do I have watches", "show me my jackets")
   - "blended_outfit_item": User wants an outfit but with focus on a specific item (e.g., "outfit with my blue shirt", "what to wear with these shoes")
   - "activity_shoes": User specifically needs shoes for an activity (e.g., "running shoes", "hiking boots")

2. **Item Type Extraction**: If the query mentions a specific item type, extract it:
   - Examples: "rings" → "rings", "watch" → "watch", "blue shirt" → "shirt", "jacket" → "jacket"
   - Set to null if no specific item type is mentioned

3. **Context Understanding**: Consider:
   - Occasion/activity mentioned (business, casual, formal, gym, etc.)
   - Weather conditions implied (cold, warm, rainy, etc.)
   - Formality level (formal, semi-formal, casual)
   - Specific requirements (color, style, comfort, etc.)

## WARDROBE DATA {wardrobe_note}:
{wardrobe_text}

## RESPONSE STRATEGY BY INTENT

### For "item_search" Intent:
- User is asking about specific items in their wardrobe
- **CRITICAL**: If user asks "are there any rings" or "do I have watches", return outfits that HIGHLIGHT those specific items
- Create {limit} outfits where the requested item type is prominently featured
- Example: Query "rings" → Return outfits where rings (accessories) are included and emphasized in rationale
- Still include top, bottom, footwear to show how the item works in a complete outfit
- Set "item_type" to the specific item category (e.g., "rings", "watch", "jacket")
- **If the requested item type is NOT in the wardrobe**: Still return {limit} outfits, but note in the rationale that the specific item type is not available in the wardrobe

### For "outfit" Intent:
- User wants complete outfit suggestions for an occasion/activity
- Generate {limit} diverse, well-coordinated outfits
- **PRIORITY**: Include accessories in at least 2 out of {limit} outfits when available
- Match the occasion, formality, and style requirements
- Consider weather and context (layers only when needed)

### For "blended_outfit_item" Intent:
- User wants outfits built around a specific item
- Feature the mentioned item prominently in all outfits
- Show different ways to style that item
- Set "item_type" to the specific item mentioned

### For "activity_shoes" Intent:
- Focus on footwear appropriate for the activity
- Build complete outfits around suitable shoes
- Consider functionality and comfort requirements

## OUTFIT COMPOSITION RULES

**REQUIRED Components** (every outfit must have):
- "top": Upper body garment (shirt, t-shirt, blouse, kurta, etc.)
- "bottom": Lower body garment (pants, jeans, skirt, chinos, etc.)
- "footwear": Shoes, sandals, boots, etc.

**STRONGLY RECOMMENDED** (when available in wardrobe):
- "accessories": Watch, ring, cap, umbrella, bag, jewelry, belt, etc.
  - Include in at least 2 out of {limit} outfits for "outfit" intent
  - Always include when user searches for accessories (item_search intent)
  - Accessories complete and elevate outfits

**CONTEXT-DEPENDENT** (only when truly needed):
- "layer": Outerwear, jacket, blazer, cardigan, etc.
  - Include for: cold weather, rain, formal requirements, outdoor events
  - Omit for: warm weather, indoor events, casual occasions, summer outfits
  - Better to omit than include unnecessarily

## COLOR & STYLE COORDINATION

- Ensure harmonious color schemes (complementary, monochromatic, or analogous)
- Match formality level to the occasion
- Consider style consistency (e.g., don't mix formal and casual items)
- Vary outfits to provide different style options when possible

## RESPONSE FORMAT

Return valid JSON only (no markdown, no comments):

{{
    "intent": "outfit" | "item_search" | "blended_outfit_item" | "activity_shoes",
    "item_type": "specific item name" | null,
    "outfits": [
        {{
            "top": {{"id": <wardrobe_id>}},
            "bottom": {{"id": <wardrobe_id>}},
            "footwear": {{"id": <wardrobe_id>}},
            "layer": {{"id": <wardrobe_id>}} | null,
            "accessories": {{"id": <wardrobe_id>}} | null,
            "rationale": "1-2 sentence explanation: why this outfit works, how it matches the request, color/style coordination, and how the specific item (if item_search) is featured"
        }}
    ]
}}

## CRITICAL VALIDATION

- All item IDs MUST exist in the wardrobe list above - never invent items
- For "item_search": If the requested item type exists in wardrobe, it MUST appear in at least one outfit. If it doesn't exist, note this in the rationale
- For "outfit": Accessories should appear in at least 2 out of {limit} outfits when available
- Layers only when contextually appropriate (weather, formality, occasion)
- Generate exactly {limit} outfits (or fewer if wardrobe is limited)
- Each outfit MUST have a "rationale" explaining the selection

## RATIONALE GUIDELINES

Write clear, contextual rationales:
- For "item_search": Emphasize how the requested item is featured and styled
- For "outfit": Explain occasion match, color harmony, style coordination
- Be specific: mention colors, occasion type, style elements
- Friendly, helpful tone as if explaining to a friend
- 1-2 sentences maximum per outfit

Return valid JSON only."""


def _extract_json_from_response(text: str, logger) -> Optional[Dict]:
    """
    Extract and parse JSON from Gemini response.
    Handles various response formats: pure JSON, markdown code blocks, or mixed text.
    
    Args:
        text: Raw response text from Gemini
        logger: Logger instance for error reporting
    
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    # Try direct JSON parse first (for structured output)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code blocks (handle nested JSON)
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            # Use brace matching for nested structures
            json_text = json_match.group(1)
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from code block: {e}")
    
    # Try finding JSON object in text using brace matching
    start_idx = text.find('{')
    if start_idx != -1:
        # Find matching closing brace for nested structures
        brace_count = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    try:
                        return json.loads(text[start_idx:i+1])
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON from brace-matched text: {e}")
                        break
    
    
    logger.error(f"Failed to extract valid JSON from Gemini response. Response text: {text[:500]}")
    return None


def _check_token_limits(prompt: str, wardrobe_items: List[Dict]) -> tuple[bool, int, Optional[str]]:
    """
    Check if prompt is within token limits.
    
    Returns:
        (is_safe, estimated_tokens, warning_message)
    """
    estimated_tokens = _estimate_tokens(prompt)
    
    if estimated_tokens > MAX_INPUT_TOKENS:
        return False, estimated_tokens, f"Prompt exceeds token limit ({estimated_tokens} > {MAX_INPUT_TOKENS})"
    elif estimated_tokens > TOKEN_WARNING_THRESHOLD:
        return True, estimated_tokens, f"Prompt is large ({estimated_tokens} tokens, {len(wardrobe_items)} items)"
    else:
        return True, estimated_tokens, None



