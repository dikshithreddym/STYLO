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
        # Format wardrobe items for Gemini
        wardrobe_text = _format_wardrobe_for_gemini(wardrobe_items)

        prompt = f"""
You are a fashion stylist assistant and intent classifier. Based on the user's request and their wardrobe, do the following:
1. Classify the user's intent as one of: outfit, item_search, blended_outfit_item, activity_shoes.
2. If relevant, specify the requested item type (e.g., shoes).
3. Suggest {limit} complete outfits as described below.

USER REQUEST: "{query}"

USER'S WARDROBE:
{wardrobe_text}

INSTRUCTIONS:
- For each outfit, select items from the wardrobe that match the occasion and work well together
- Each outfit must include: top, bottom, and footwear (required)
- Optionally include: layer/outerwear and accessories if appropriate
- Ensure colors coordinate well
- Match the occasion/style described in the user's request
- Return ONLY valid item IDs from the wardrobe - do not invent items

Return your response in this exact JSON format:
{{
    "intent": "outfit", // or "item_search", "blended_outfit_item", "activity_shoes"
    "item_type": "shoes", // or null if not applicable
    "outfits": [
        {{
            "top": {{"id": 1}},
            "bottom": {{"id": 5}},
            "footwear": {{"id": 10}},
            "layer": {{"id": 15}},
            "accessories": {{"id": 20}}
        }}
    ]
}}

Important: Only use item IDs that exist in the wardrobe above. Ensure all required categories (top, bottom, footwear) are present in each outfit.
"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"

        response = requests.post(
            url,
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2048,
                }
            },
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"Gemini API error: {response.status_code} {response.text}")
            return None

        result = response.json()
        if 'candidates' not in result or not result['candidates']:
            logger.error("No candidates in Gemini response.")
            return None

        content = result['candidates'][0]['content']
        if 'parts' not in content or not content['parts']:
            logger.error("No parts in Gemini response content.")
            return None

        text = content['parts'][0]['text'].strip()

        # Try to extract JSON from response
        # Extract JSON block from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        else:
            # Try to find JSON object
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group(0)

        try:
            parsed = json.loads(text)
        except Exception as e:
            logger.error(f"Failed to parse Gemini JSON: {e}\n{text}")
            return None

        if 'outfits' not in parsed:
            logger.error("No 'outfits' key in Gemini response JSON.")
            return None

        # Validate and map item IDs to actual items
        item_map = {it['id']: it for it in wardrobe_items}
        validated_outfits = []

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


def _format_wardrobe_for_gemini(items: List[Dict]) -> str:
    """Format wardrobe items for Gemini prompt"""
    lines = []
    for it in items:
        desc_parts = [f"ID: {it.get('id')}"]
        desc_parts.append(f"Name: {it.get('name', 'Unknown')}")
        desc_parts.append(f"Category: {it.get('category', 'unknown')}")
        if it.get('color'):
            desc_parts.append(f"Color: {it.get('color')}")
        if it.get('description'):
            desc_parts.append(f"Description: {it.get('description')}")
        lines.append(" - " + " | ".join(desc_parts))
    
    return "\n".join(lines)

