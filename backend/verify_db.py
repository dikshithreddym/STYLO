"""
Simple script to verify database connection and show wardrobe items
"""
from app.database import SessionLocal, engine
from app.models import Base, WardrobeItem

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Query items
db = SessionLocal()
try:
    items = db.query(WardrobeItem).all()
    print(f"✅ Database connection successful!")
    print(f"📦 Total items in wardrobe: {len(items)}")
    
    if items:
        print("\n📋 Current items:")
        for item in items:
            print(f"  - {item.id}: {item.type} ({item.color}) - Category: {item.category}")
    else:
        print("\n💡 Your wardrobe is empty. Add items through the frontend or API.")
    
except Exception as e:
    print(f"❌ Database error: {e}")
finally:
    db.close()
