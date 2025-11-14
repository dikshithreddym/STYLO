"""
Migration script to add image_description column to wardrobe_items table
Run this script once to update your database schema
"""
from sqlalchemy import create_engine, text
from app.config import settings

def migrate():
    """Add image_description column to wardrobe_items table"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        # Check if column already exists
        result = connection.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='wardrobe_items' 
            AND column_name='image_description'
        """))
        
        if result.fetchone() is None:
            print("Adding image_description column...")
            connection.execute(text("""
                ALTER TABLE wardrobe_items 
                ADD COLUMN image_description TEXT
            """))
            connection.commit()
            print("✅ Successfully added image_description column")
        else:
            print("ℹ️  Column image_description already exists, skipping migration")

if __name__ == "__main__":
    migrate()
