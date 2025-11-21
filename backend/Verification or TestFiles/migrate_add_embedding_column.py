"""
Migration script to add embedding column to wardrobe_items table.
Run this once to add the embedding column for existing databases.

Usage:
    cd backend
    python "Verification or TestFiles/migrate_add_embedding_column.py"
    
Or from the backend directory:
    python -m "Verification or TestFiles.migrate_add_embedding_column"
"""
import os
import sys

# Add backend directory to path (works when run from backend/ or project root)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Also try adding parent if we're in Verification or TestFiles
parent_dir = os.path.dirname(backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from sqlalchemy import text, inspect
    from app.database import engine, SessionLocal
except ImportError as e:
    print(f"ERROR: Import error: {e}")
    print("\nMake sure you:")
    print("   1. Are in the 'backend' directory")
    print("   2. Have activated your virtual environment")
    print("   3. Have installed dependencies: pip install -r requirements.txt")
    print(f"\n   Current working directory: {os.getcwd()}")
    print(f"   Python path: {sys.path[:3]}")
    sys.exit(1)

def migrate():
    """Add embedding column to wardrobe_items table if it doesn't exist"""
    db = SessionLocal()
    try:
        # Use SQLAlchemy Inspector for database-agnostic column checking
        with engine.connect() as conn:
            insp = inspect(conn)
            cols = [c["name"] for c in insp.get_columns("wardrobe_items")]
            
            if "embedding" in cols:
                print("SUCCESS: Embedding column already exists")
                return
            
            # Add embedding column - use appropriate type for database
            # PostgreSQL uses JSON, SQLite uses TEXT (we'll store JSON string)
            db.execute(text("""
                ALTER TABLE wardrobe_items 
                ADD COLUMN embedding JSON
            """))
            db.commit()
            print("SUCCESS: Successfully added embedding column to wardrobe_items table")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Error adding embedding column: {e}")
        print(f"\nTroubleshooting:")
        print("   - Make sure DATABASE_URL is set correctly")
        print("   - Check that the database is accessible")
        print("   - Verify you have ALTER TABLE permissions")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

