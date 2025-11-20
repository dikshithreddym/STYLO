"""
Backfill script to generate image descriptions for existing wardrobe items
Run this script to analyze existing items and add AI-generated descriptions
"""
import asyncio
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import WardrobeItem
from app.utils.image_analyzer import analyze_clothing_image, generate_fallback_description
from app.config import settings
import requests


def download_image_as_base64(image_url: str) -> str:
    """Download image from URL and convert to base64 data URL"""
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Determine content type
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        # Convert to base64
        import base64
        base64_data = base64.b64encode(response.content).decode('utf-8')
        
        return f"data:{content_type};base64,{base64_data}"
    except Exception as e:
        print(f"  ⚠️  Failed to download image: {e}")
        return None


async def backfill_descriptions():
    """Backfill image descriptions for ALL wardrobe items (force re-analysis)"""
    db = SessionLocal()
    
    try:
        # Get ALL items to force re-analysis with new prompt
        all_items = db.query(WardrobeItem).all()
        
        if not all_items:
            print("✅ No items found in wardrobe!")
            return
        
        print(f"📋 Found {len(all_items)} item(s) to re-analyze")
        print(f"🔑 Gemini API configured: {'Yes' if settings.GEMINI_API_KEY else 'No'}")
        print()
        
        updated_count = 0
        failed_count = 0
        
        for item in all_items:
            print(f"🔍 Processing item #{item.id}: {item.type} ({item.color})")
            
            description = None
            
            # Try AI analysis if image URL exists and Gemini is configured
            if item.image_url and settings.GEMINI_API_KEY:
                print(f"  📥 Downloading image from Cloudinary...")
                base64_image = download_image_as_base64(item.image_url)
                
                if base64_image:
                    print(f"  🤖 Analyzing with Gemini AI...")
                    description = await analyze_clothing_image(base64_image)
            
            # Use fallback if AI analysis failed or wasn't available
            if not description:
                print(f"  💡 Using fallback description")
                description = generate_fallback_description(
                    item.type, 
                    item.color, 
                    item.category
                )
            
            # Update item
            item.image_description = description
            db.commit()
            
            print(f"  ✅ Description: {description[:80]}...")
            print()
            updated_count += 1
        
        print(f"\n🎉 Backfill complete!")
        print(f"   Updated: {updated_count}")
        print(f"   Failed: {failed_count}")
        
    except Exception as e:
        print(f"❌ Backfill error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("📸 Image Description Backfill Tool")
    print("=" * 60)
    print()
    
    asyncio.run(backfill_descriptions())
