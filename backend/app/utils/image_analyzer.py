"""
Image analysis utility using AI to generate clothing descriptions
"""
import httpx
import re
import logging
import asyncio
from typing import Optional
from app.config import settings


def extract_base64_from_data_url(data_url: str) -> Optional[str]:
    """Extract base64 data from data URL"""
    if data_url.startswith('data:image/'):
        match = re.match(r'data:image/[^;]+;base64,(.+)', data_url)
        if match:
            return match.group(1)
    return data_url if not data_url.startswith('data:') else None


async def analyze_clothing_image(image_data: str) -> Optional[str]:
    """
    Analyze a clothing image and generate a description using Google Gemini
    Args:
        image_data: Base64 data URL of the image
    Returns:
        str: Description of the clothing item, or None if analysis fails
    """
    logger = logging.getLogger(__name__)
    import os
    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv("GEMINI_API_KEY")

    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not set.")
        return None

    try:
        # Extract base64 data
        base64_data = extract_base64_from_data_url(image_data)
        if not base64_data:
            logger.error("Failed to extract base64 data from image")
            return None

        logger.info(f"Extracted base64 data, length: {len(base64_data)} characters")

        # Using gemini-2.5-flash model
        model_name = "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": gemini_api_key
        }

        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": "Analyze this clothing image and provide a detailed description in 2-3 sentences. First, identify what's written or branded on the item. Then describe the visual characteristics: sleeve length (long/short/sleeveless), fit style (fitted/relaxed/oversized), closure type (zipper/button/pullover), material texture (if visible), and any distinctive design features like pockets, collars, or patterns. Include the color and brand/text visible on the item."
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_data
                        }
                    }
                ]
            }]
        }

        logger.info(f"Calling Gemini API with model: {model_name}")
        
        # Retry logic for rate limits (429 errors)
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                response = await client.post(url, headers=headers, json=payload, timeout=30)
                
                logger.info(f"Gemini API response status: {response.status_code} (attempt {attempt + 1}/{max_retries})")

                if response.status_code == 200:
                    break  # Success, exit retry loop
                
                # Handle rate limiting (429) with retry
                if response.status_code == 429:
                    error_json = {}
                    try:
                        error_json = response.json()
                    except (ValueError, KeyError):
                        pass
                    
                    error_message = error_json.get('error', {}).get('message', 'Rate limit exceeded')
                    
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Gemini API rate limit hit (429). "
                            f"Retrying in {retry_delay} seconds... "
                            f"Error: {error_message}"
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"Gemini API rate limit exceeded after {max_retries} attempts. "
                            f"Quota may be exhausted. Using fallback description. "
                            f"Error: {error_message}"
                        )
                        return None
                else:
                    # Other errors - log and return None
                    error_text = response.text
                    logger.error(f"Gemini API error: {response.status_code} - {error_text}")
                    try:
                        error_json = response.json()
                        logger.error(f"Gemini API error details: {error_json}")
                    except (ValueError, KeyError):
                        pass
                    return None

        if response.status_code != 200:
            return None

        result = response.json()
        logger.debug(f"Gemini API response structure: {list(result.keys())}")
        
        if 'candidates' not in result or not result['candidates']:
            logger.error(f"No candidates in Gemini response. Response keys: {list(result.keys())}")
            logger.error(f"Full response: {result}")
            return None

        content = result['candidates'][0]['content']
        if 'parts' not in content or not content['parts']:
            logger.error(f"No parts in Gemini response content. Content keys: {list(content.keys())}")
            logger.error(f"Full content: {content}")
            return None

        description = content['parts'][0]['text'].strip()
        logger.info(f"Successfully generated description: {description[:100]}...")
        return description

    except httpx.HTTPError as e:
        logger.error(f"HTTP error analyzing image: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error analyzing image: {type(e).__name__}: {e}", exc_info=True)
        return None


def generate_fallback_description(item_type: str, color: str, category: Optional[str] = None) -> str:
    """
    Generate a basic description when AI analysis is not available
    
    Args:
        item_type: Type of clothing item
        color: Color of the item
        category: Category (top, bottom, etc.)
        
    Returns:
        str: Basic description
    """
    descriptions = {
        'top': f"A {color} {item_type} that pairs well with various bottoms.",
        'bottom': f"Versatile {color} {item_type} suitable for different occasions.",
        'footwear': f"Comfortable {color} {item_type} to complete your outfit.",
        'layer': f"A {color} {item_type} perfect for layering in cooler weather.",
        'one-piece': f"An elegant {color} {item_type} for a complete look.",
        'accessories': f"A stylish {color} {item_type} to complement your ensemble."
    }
    
    if category and category in descriptions:
        return descriptions[category]
    
    return f"A {color} {item_type} from your wardrobe collection."
