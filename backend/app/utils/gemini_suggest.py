"""
Optional Gemini API integration for outfit suggestions.
This provides an alternative to the semantic embedding-based engine.
"""
import os
import requests
from typing import List, Dict, Optional
from app.config import settings


async def suggest_outfit_with_gemini(
    query: str,
    wardrobe_items: List[Dict],
    limit: int = 3
) -> Optional[List[Dict]]:
    """
    Use Gemini API to suggest outfits based on query and wardrobe.
    
    Args:
        query: User's outfit request (e.g., "business meeting", "casual date")
        wardrobe_items: List of wardrobe items with keys: id, name, category, color, image_url, description
        limit: Number of outfits to generate
        
    Returns:
        List of outfit dicts mapping category -> item, or None if Gemini not configured/fails
    """
    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
    
    if not gemini_api_key:
        return None
    
    try:
        # Format wardrobe items for Gemini
        wardrobe_text = _format_wardrobe_for_gemini(wardrobe_items)
        
        prompt = f"""You are a fashion stylist assistant. Based on the user's request and their wardrobe, suggest {limit} complete outfits.

USER REQUEST: "{query}"

USER'S WARDROBE:
{wardrobe_text}

INSTRUCTIONS:
1. For each outfit, select items from the wardrobe that match the occasion and work well together
2. Each outfit must include: top, bottom, and footwear (required)
3. Optionally include: outerwear/layer and accessories if appropriate
4. Ensure colors coordinate well
5. Match the occasion/style described in the user's request
6. Return ONLY valid item IDs from the wardrobe - do not invent items

Return your response in this exact JSON format:
{{
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

Important: Only use item IDs that exist in the wardrobe above. Ensure all required categories (top, bottom, footwear) are present in each outfit."""

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
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']
                if 'parts' in content and len(content['parts']) > 0:
                    text = content['parts'][0]['text'].strip()
                    
                    # Try to extract JSON from response
                    import json
                    import re
                    
                    # Extract JSON block from markdown code blocks if present
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
                    if json_match:
                        text = json_match.group(1)
                    else:
                        # Try to find JSON object
                        json_match = re.search(r'\{.*\}', text, re.DOTALL)
                        if json_match:
                            text = json_match.group(0)
                    
                    parsed = json.loads(text)
                    
                    if 'outfits' in parsed:
                        # Validate and map item IDs to actual items
                        item_map = {it['id']: it for it in wardrobe_items}
                        validated_outfits = []
                        
                        for outfit_dict in parsed['outfits'][:limit]:
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
                            return validated_outfits
        
        return None
        
    except Exception as e:
        print(f"Gemini outfit suggestion error: {e}")
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
            desc_parts.append(f"Description: {it.get('description')[:100]}")
        lines.append(" - " + " | ".join(desc_parts))
    
    return "\n".join(lines)

