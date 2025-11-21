"""
Quick script to verify image descriptions are in the database
"""
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.database import SessionLocal, WardrobeItem

def verify_descriptions():
    """Check if descriptions are actually in the database"""
    db = SessionLocal()
    
    try:
        # Get all items
        all_items = db.query(WardrobeItem).all()
        
        print(f"📊 Total items in database: {len(all_items)}")
        print()
        
        # Count items with descriptions
        items_with_desc = [item for item in all_items if item.image_description]
        items_without_desc = [item for item in all_items if not item.image_description]
        
        print(f"✅ Items WITH descriptions: {len(items_with_desc)}")
        print(f"❌ Items WITHOUT descriptions: {len(items_without_desc)}")
        print()
        
        # Show sample items with descriptions
        if items_with_desc:
            print("📝 Sample items with descriptions:")
            for item in items_with_desc[:5]:
                desc_preview = item.image_description[:60] + "..." if len(item.image_description) > 60 else item.image_description
                print(f"   ID {item.id}: {item.type} ({item.color})")
                print(f"      Description: {desc_preview}")
                print()
        
        # Show items without descriptions
        if items_without_desc:
            print("⚠️  Items without descriptions:")
            for item in items_without_desc[:10]:
                print(f"   ID {item.id}: {item.type} ({item.color}) - image_url: {item.image_url is not None}")
        
        # Check a specific item by ID
        print()
        print("🔍 Checking specific items from backfill...")
        test_ids = [5, 15, 14, 10, 12]  # IDs from the backfill output
        for test_id in test_ids:
            item = db.query(WardrobeItem).filter(WardrobeItem.id == test_id).first()
            if item:
                has_desc = "✅ HAS" if item.image_description else "❌ MISSING"
                desc_preview = item.image_description[:50] + "..." if item.image_description and len(item.image_description) > 50 else (item.image_description or "None")
                print(f"   ID {test_id}: {has_desc} description")
                print(f"      Preview: {desc_preview}")
            else:
                print(f"   ID {test_id}: ❌ NOT FOUND")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Image Description Verification")
    print("=" * 60)
    print()
    verify_descriptions()

