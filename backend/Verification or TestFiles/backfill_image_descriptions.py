"""
Backfill script to generate image descriptions for existing wardrobe items
Run this script to analyze existing items and add AI-generated descriptions
"""
import asyncio
import sys
import os

# Add backend directory to path to import app modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.database import SessionLocal, WardrobeItem
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


async def backfill_descriptions(limit: int = 10):
    """
    Backfill image descriptions for the latest uploaded wardrobe items
    Args:
        limit: Number of latest items to process (default: 10)
    """
    db = SessionLocal()
    
    try:
        # Get latest items ordered by ID (descending) - newest first
        all_items = db.query(WardrobeItem).order_by(WardrobeItem.id.desc()).limit(limit).all()
        
        if not all_items:
            print("✅ No items found in wardrobe!")
            return
        
        print(f"📋 Processing latest {len(all_items)} item(s) (ordered by most recent)")
        print(f"🔑 Gemini API configured: {'Yes' if settings.GEMINI_API_KEY else 'No'}")
        print()
        
        updated_count = 0
        failed_count = 0
        
        for item in all_items:
            try:
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
                
                # Update item in database
                item.image_description = description
                db.flush()  # Ensure changes are sent to database
                
                # Verify before committing
                db.refresh(item)
                if item.image_description == description:
                    db.commit()  # Commit the transaction
                    print(f"  ✅ Description saved: {description[:80]}...")
                    updated_count += 1
                else:
                    print(f"  ⚠️  Warning: Description mismatch, rolling back")
                    db.rollback()
                    failed_count += 1
                print()
                
            except Exception as e:
                print(f"  ❌ Error processing item #{item.id}: {e}")
                db.rollback()
                failed_count += 1
                print()
        
        # Final commit to ensure all changes are persisted
        db.commit()
        
        # Verify updates by querying a few items
        print(f"\n🔍 Verifying updates...")
        sample_items = db.query(WardrobeItem).limit(5).all()
        verified_count = sum(1 for item in sample_items if item.image_description)
        print(f"   Sample check: {verified_count}/{len(sample_items)} items have descriptions")
        
        print(f"\n🎉 Backfill complete!")
        print(f"   Updated: {updated_count}")
        print(f"   Failed: {failed_count}")
        
    except Exception as e:
        print(f"❌ Backfill error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    # Allow limit to be passed as command line argument
    limit = 10
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"⚠️  Invalid limit '{sys.argv[1]}', using default: 10")
            limit = 10
    
    print("=" * 60)
    print("📸 Image Description Backfill Tool")
    print(f"   Processing latest {limit} items")
    print("=" * 60)
    print()
    
    asyncio.run(backfill_descriptions(limit=limit))
