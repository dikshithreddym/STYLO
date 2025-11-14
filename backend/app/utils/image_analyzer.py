"""
Image analysis utility using AI to generate clothing descriptions
"""
import base64
import requests
import re
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
    # Check if Gemini API key is configured
    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
    
    if not gemini_api_key:
        # Return None if no AI service is configured (will use fallback)
        return None
    
    try:
        # Extract base64 data
        base64_data = extract_base64_from_data_url(image_data)
        if not base64_data:
            print("Failed to extract base64 data from image")
            return None
        
        # Call Google Gemini Vision API (use gemini-1.5-flash-latest)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_api_key}"
        
        headers = {
            "Content-Type": "application/json"
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
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']
                if 'parts' in content and len(content['parts']) > 0:
                    description = content['parts'][0]['text'].strip()
                    return description
            print(f"Unexpected Gemini API response format: {result}")
            return None
        else:
            print(f"Gemini API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error analyzing image: {e}")
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
        'shoes': f"Comfortable {color} {item_type} to complete your outfit.",
        'layer': f"A {color} {item_type} perfect for layering in cooler weather.",
        'one-piece': f"An elegant {color} {item_type} for a complete look.",
        'accessories': f"A stylish {color} {item_type} to complement your ensemble."
    }
    
    if category and category in descriptions:
        return descriptions[category]
    
    return f"A {color} {item_type} from your wardrobe collection."
