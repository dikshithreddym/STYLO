"""
Test script to debug Gemini analyzer issues
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.image_analyzer import analyze_clothing_image
from app.config import settings

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_gemini_analyzer():
    """Test the Gemini analyzer with a sample image"""
    
    print("=" * 60)
    print("Testing Gemini Analyzer")
    print("=" * 60)
    
    # Check API key
    print(f"\n1. Checking GEMINI_API_KEY...")
    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not gemini_api_key:
        print("❌ GEMINI_API_KEY is not set!")
        print("   Please set it in your .env file or environment variables")
        return
    else:
        print(f"✅ GEMINI_API_KEY is set (length: {len(gemini_api_key)} characters)")
        print(f"   Key starts with: {gemini_api_key[:10]}...")
    
    # Create a minimal test image (1x1 pixel red PNG as base64)
    # This is a valid base64-encoded 1x1 red PNG
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    test_data_url = f"data:image/png;base64,{test_image_base64}"
    
    print(f"\n2. Testing with sample image...")
    print(f"   Image data URL length: {len(test_data_url)} characters")
    print(f"   Base64 data length: {len(test_image_base64)} characters")
    
    try:
        print(f"\n3. Calling analyze_clothing_image...")
        result = await analyze_clothing_image(test_data_url)
        
        if result:
            print(f"\n✅ SUCCESS!")
            print(f"   Generated description: {result}")
        else:
            print(f"\n❌ FAILED!")
            print(f"   Function returned None")
            print(f"\n   DIAGNOSIS:")
            print(f"   - If you see '429 Too Many Requests' or 'RESOURCE_EXHAUSTED':")
            print(f"     → Your Gemini API quota has been exhausted")
            print(f"     → Solution: Wait for quota reset or upgrade your API plan")
            print(f"     → The fallback description will be used automatically")
            print(f"   - If you see other errors, check the logs above for details")
            
    except Exception as e:
        print(f"\n❌ EXCEPTION occurred!")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_gemini_analyzer())

