"""
Optional Gemini API integration for outfit suggestions.
This provides an alternative to the semantic embedding-based engine.
"""
import requests
import json
import re
import logging
from typing import List, Dict, Optional
from app.config import settings
from app.utils.profiler import get_profiler

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
    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)

    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not set.")
        return None

    try:

        # Optimized: Only send up to 5 items per required category, max 15 items total
        MAX_ITEMS_PER_CATEGORY = 5
        REQUIRED_CATEGORIES = ["top", "bottom", "footwear"]
        grouped = {cat: [] for cat in REQUIRED_CATEGORIES}
        for it in wardrobe_items:
            cat = it.get("category", "").lower()
            if cat in grouped and len(grouped[cat]) < MAX_ITEMS_PER_CATEGORY:
                grouped[cat].append(it)
        limited_items = []
        for cat in REQUIRED_CATEGORIES:
            limited_items.extend(grouped[cat])
        # If less than 15, fill with other items
        MAX_TOTAL_ITEMS = 15
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

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={gemini_api_key}"

        profiler = get_profiler()
        # Use structured output for better JSON generation
        # Lower temperature for more consistent, structured responses
        with profiler.measure("gemini_api_request"):
            response = requests.post(
                url,
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
                timeout=30
            )

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
    
    return f"""You are an expert fashion stylist and intent classifier. Analyze the user's request and their wardrobe to suggest complete, well-coordinated outfits.

TASK:
1. Classify the user's intent: "outfit" (full outfit request), "item_search" (looking for specific item), "blended_outfit_item" (outfit with focus on item), or "activity_shoes" (shoes for activity).
2. If intent involves a specific item type, set "item_type" (e.g., "shoes", "jacket", null otherwise).
3. Generate {limit} complete, stylish outfits that match the user's request.

USER REQUEST: "{query}"

WARDROBE {wardrobe_note}:
{wardrobe_text}

OUTFIT REQUIREMENTS:
- Each outfit MUST include: top, bottom, and footwear (all required)
- Optionally include: layer (outerwear/jacket) and accessories if appropriate
- Ensure colors coordinate harmoniously (complementary or monochromatic schemes)
- Match the occasion, style, and formality level described in the user's request
- Select items that work well together as a cohesive outfit
- Use ONLY item IDs that exist in the wardrobe above - never invent items
- Vary the outfits to provide different style options when possible

RESPONSE FORMAT (JSON only, no markdown, no comments):
{{
    "intent": "outfit",
    "item_type": null,
    "outfits": [
        {{
            "top": {{"id": 1}},
            "bottom": {{"id": 5}},
            "footwear": {{"id": 10}},
            "layer": {{"id": 15}},
            "accessories": {{"id": 20}},
            "rationale": "A brief 1-2 sentence explanation of why this outfit was chosen, mentioning color coordination, occasion match, style compatibility, or specific features that make it suitable for the user's request."
        }}
    ]
}}

RATIONALE REQUIREMENTS:
- Each outfit MUST include a "rationale" field with a clear, concise explanation (1-2 sentences)
- Explain why this specific combination works well for the user's request
- Mention relevant aspects like: color harmony, occasion appropriateness, style coordination, comfort/functionality, or specific item features
- Be specific about how the outfit matches the user's needs (e.g., "gym", "business meeting", "casual date")
- Write in a friendly, helpful tone as if explaining to a friend

VALIDATION RULES:
- "intent" must be one of: "outfit", "item_search", "blended_outfit_item", "activity_shoes"
- "item_type" must be a string (item name) or null
- Each outfit must have "top", "bottom", and "footwear" with valid IDs from the wardrobe
- Each outfit must have a "rationale" field with explanation text
- Optional fields: "layer", "accessories" (can be omitted if not applicable)
- All item IDs must exist in the wardrobe list above
- Generate exactly {limit} outfits (or fewer if wardrobe is limited)

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



